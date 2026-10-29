"""Verify a LIVE RCMP read against the offline .cpg backups.

Reads the channel-name object (0x0fff, instance 0) off the connected radio over
the verified read-only RCMP client, then compares it to the same stream decoded
from every backups/*.cpg. Prints which backup it matches -- that both confirms
the live read is correct and identifies which radio is on the cable.

Two transports: with a serial port argument it brings PPP up itself over that
port (no Windows RAS entry); otherwise it connects to an already-up PPP link.
Read-only; never writes the radio. Usage:

    python tools/verify_live_read.py COM7        # self-contained (recommended)
    python tools/verify_live_read.py             # via an already-up PPP link
"""
from __future__ import annotations

import glob
import os
import sys

from open_astro.protocol.rcmp_transport import RcmpReadClient, RcmpError
from open_astro.protocol import rcmp
from open_astro.parsers.cpg_decode import CpgDecoder, TAG_CHANNEL_NAMES

OBJ_CHANNEL_NAMES = 0x0FFF
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _backup_name_tables():
    """{cpg_path: names_list} for the 0x0fff inst0 table of each backup."""
    out = {}
    for path in glob.glob(os.path.join(REPO, "backups", "*.cpg")):
        try:
            d = CpgDecoder(path)
            streams = d._decoded_streams()
            d.close()
        except Exception:
            continue
        tabs = [p for t, i, p in streams if t == TAG_CHANNEL_NAMES and i == 0]
        if tabs:
            out[path] = [n for n in CpgDecoder._name_table(tabs[0]) if n]
    return out


def main() -> int:
    serial_port = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        if serial_port:
            from open_astro.protocol.ppp_link import PppTcpConn
            client = RcmpReadClient(PppTcpConn(serial_port))
        else:
            client = RcmpReadClient.connect()
    except (RcmpError, Exception) as e:
        print(f"[-] connect failed: {e}")
        return 1
    try:
        client.open_session()
        live_payload = client.read_object(rcmp.PART_CODEPLUG, OBJ_CHANNEL_NAMES, 0x0120)
    except RcmpError as e:
        print(f"[-] live read failed: {e}")
        return 1
    finally:
        client.close()

    live_names = [n for n in CpgDecoder._name_table(live_payload) if n]
    print(f"[+] live 0x0fff read: {len(live_payload)} bytes, "
          f"{len(live_names)} named channels")
    print(f"    {live_names}")

    match = None
    for path, names in _backup_name_tables().items():
        if names == live_names:
            match = path
            break
    if match:
        print(f"[PASS] live read matches backup: {os.path.basename(match)}")
        return 0
    print("[FAIL] live read did not match any backup in backups/*.cpg")
    return 2


if __name__ == "__main__":
    sys.exit(main())
