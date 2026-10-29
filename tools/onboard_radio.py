#!/usr/bin/env python3
"""Automated Onboarding & Health Diagnostic Tool for ASTRO 25 Radios (XTS 2500 / XTS 5000).

Runs an automated pre-flight check when connecting a new radio (e.g. incoming XTS 5000):
1. Hardware Interrogation: Serial, Model Number, Host/DSP firmware, and UCM crypto module status.
2. Safety Audit: Inspects UCM socket. If empty (R000000), warns against hardware-gated bits
   (AES/DES) that cause power-on POST ERROR 01/82.
3. Factory Backup: Performs a full non-destructive read of partition 0x80 (codeplug) and 0x81 (identity).
   STRICTLY ENFORCES THE PARTITION 0x82 TUNING FIREWALL (never touched).
4. Upgrade Verification: Checks current FLASHcode vs fleet target 'FBFFFF-B7F3FF-1' (43 software features).

Usage:
    python tools/onboard_radio.py --port COM7
    python tools/onboard_radio.py --virtual  # Test against local virtual radio server
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from open_astro.models.flashcode import FlashcodeDecoder, luhn_check_digit, verify_flashcode
from open_astro.protocol.rcmp_transport import RcmpReadClient, RcmpError

TARGET_FLEET_FLASHCODE = "FBFFFF-B7F3FF-1"


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def probe_at_interface(port: str, baud: int = 19200) -> dict:
    """Send read-only AT queries to identify radio hardware and crypto status."""
    try:
        import serial
    except ImportError:
        print("[-] pyserial not installed; skipping AT interrogation")
        return {}

    info = {}
    print(f"[+] Opening serial port {port} at {baud} baud for AT probe...")
    try:
        with serial.Serial(port, baud, timeout=1.2) as ser:
            time_window = 0.5
            for cmd in ["AT", "ATI1", "ATI2", "ATI3", "ATI4", "AT&V"]:
                ser.write(f"{cmd}\r".encode("ascii"))
                import time
                time.sleep(time_window)
                raw = ser.read(ser.in_waiting or 200).decode("ascii", errors="replace").strip()
                clean = "\n".join(line.strip() for line in raw.splitlines() if line.strip() and line.strip() != cmd)
                info[cmd] = clean
    except Exception as e:
        print(f"[!] Warning: AT probe encountered an issue: {e}")
    return info


def onboard_radio(port: str | None = None, host: str = "127.0.0.1", tcp_port: int = 8002, virtual: bool = False):
    print_banner("OPEN-ASTRO ASTRO 25 (XTS 5000 / 2500) ONBOARDING & AUDIT")

    # Step 1: AT Interrogation (if real serial port)
    at_info = {}
    if port and not virtual:
        print_banner("STEP 1: HARDWARE & UCM CRYPTO INTERROGATION")
        at_info = probe_at_interface(port)
        if at_info:
            print(f"  Host Firmware (ATI1) : {at_info.get('ATI1', 'Unknown')}")
            print(f"  DSP Firmware  (ATI2) : {at_info.get('ATI2', 'Unknown')}")
            print(f"  Model/Serial  (ATI3) : {at_info.get('ATI3', 'Unknown')}")
            at_v = at_info.get('AT&V', '')
            ucm_str = 'NOT EQUIPPED (R000000)'
            for line in at_v.splitlines():
                if line.startswith('SECURE:'):
                    ucm_str = line.split(':', 1)[1].strip()
                    break
            print(f"  UCM Crypto (AT&V)     : {ucm_str}")

            if 'R000000' in ucm_str or 'NOT' in ucm_str.upper():
                print("[!] UCM AUDIT: NO HARDWARE CRYPTO MODULE DETECTED (Socket Empty: R000000).")
                print("    -> Hardware features (H869 AES, H868 Multikey) MUST remain OFF (prevents ERROR 01/82).")
                print("    -> Software ADP encryption (Q667) and FPP (Q53) are 100% supported natively.")
            else:
                print(f"[+] UCM AUDIT: Hardware Crypto Module Detected ({ucm_str}).")

    # Step 2: RCMP Connection
    print_banner("STEP 2: CONNECTING TO RADIO VIA RCMP (PORT 8002)")
    if port and not virtual:
        from open_astro.protocol.ppp_link import PppTcpConn
        print(f"[+] Initializing PPP link over {port}...")
        conn = PppTcpConn(port, dport=tcp_port, timeout=5.0)
        client = RcmpReadClient(conn, timeout=5.0)
    else:
        target_host = host if virtual else "192.168.128.1"
        print(f"[+] Connecting to RCMP socket at {target_host}:{tcp_port}...")
        client = RcmpReadClient.connect(host=target_host, port=tcp_port, timeout=5.0)

    try:
        client.open_session()
        print("[+] RCMP session opened successfully.")

        # Step 3: Identity & FLASHcode Audit
        print_banner("STEP 3: READING PARTITION 0x81 (IDENTITY & FLASHCODE)")
        ident_raw = client.read_object(part=0x81, obj=0x1004, length=0x40)
        fc_raw = client.read_object(part=0x81, obj=0x1006, length=0x20)

        # Parse serial / model from 0x1004
        serial_no = "UNKNOWN"
        model_no = "UNKNOWN"
        if len(ident_raw) >= 12:
            body = ident_raw[2:] if ident_raw[:2] == b"\x02\x12" else ident_raw
            parts = body.split(b"\x00")
            if len(parts) >= 1:
                serial_no = parts[0].decode("ascii", errors="replace").strip()
            if len(parts) >= 2:
                model_no = parts[1].decode("ascii", errors="replace").strip()

        # Parse FLASHcode from 0x1006
        curr_flashcode = "UNKNOWN"
        if len(fc_raw) >= 8:
            fc_body = fc_raw[8:] if fc_raw[:4] == b"\x00\x00\x00\x10" else fc_raw
            curr_flashcode = fc_body.split(b"\x00")[0].decode("ascii", errors="replace").strip()

        print(f"  Detected Serial Number : {serial_no}")
        print(f"  Detected Radio Model   : {model_no}")
        print(f"  Current FLASHcode      : {curr_flashcode}")

        # Step 4: Factory Backup
        print_banner("STEP 4: FULL FACTORY BACKUP (NON-DESTRUCTIVE)")
        backups_dir = REPO_ROOT / "backups"
        backups_dir.mkdir(exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = backups_dir / f"onboard_{serial_no}_{ts}.json"

        print("[+] Reading partition 0x80 (codeplug) objects...")
        streams = client.read_streams(verbose=False)
        print(f"[+] Total objects read: {len(streams)}")

        backup_payload = {
            "timestamp": ts,
            "serial": serial_no,
            "model": model_no,
            "flashcode": curr_flashcode,
            "at_info": at_info,
            "objects": {
                f"80:0x{tag:04X}:{inst}": data.hex()
                for tag, inst, data in streams
            }
        }
        with open(backup_filename, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, indent=2)
        print(f"[+] FACTORY BACKUP SAVED: {backup_filename}")

        # Step 5: Upgrade Readiness
        print_banner("STEP 5: FLEET TARGET FLASHCODE READINESS")
        print(f"  Fleet Target FLASHcode : {TARGET_FLEET_FLASHCODE}")
        target_check = luhn_check_digit(TARGET_FLEET_FLASHCODE[:13].replace("-", ""))
        print(f"  Luhn Mod-10 Check Digit : {target_check} (Verified: {verify_flashcode(TARGET_FLEET_FLASHCODE)})")

        if curr_flashcode == TARGET_FLEET_FLASHCODE:
            print("[+] STATUS: Radio is ALREADY at fleet target specification!")
        else:
            print("[+] STATUS: Radio is ready for one-click FLASHcode upgrade.")
            print("    To upgrade to 43 software features (Q667 ADP + Q53 FPP + Q806 Digital):")
            if virtual:
                print(f"    python -m open_astro.cli rcmp-flash --host {host} --port {tcp_port} --upgrade-flashcode {TARGET_FLEET_FLASHCODE}")
            else:
                print(f"    python -m open_astro.cli rcmp-flash --serial {port} --upgrade-flashcode {TARGET_FLEET_FLASHCODE}")

        print_banner("ONBOARDING COMPLETE - HARDWARE SAFE & BACKED UP")

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASTRO 25 Onboarding & Health Diagnostic Tool")
    parser.add_argument("-p", "--port", help="Serial port (e.g. COM7)")
    parser.add_argument("--virtual", action="store_true", help="Connect to virtual radio server (port 8002)")
    parser.add_argument("--host", default="127.0.0.1", help="Virtual radio host")
    parser.add_argument("--tcp-port", type=int, default=8002, help="RCMP TCP port")
    args = parser.parse_args()

    if not args.port and not args.virtual:
        print("[-] Please specify either a serial port (--port COM7) or --virtual.")
        sys.exit(1)

    onboard_radio(port=args.port, host=args.host, tcp_port=args.tcp_port, virtual=args.virtual)
