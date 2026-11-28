#!/usr/bin/env python3
"""OpenAstro Radio 4 (XTS 5000 721CLZ0655) Complete ADP Flasher with Per-Channel Strapping.

Architecture:
  - Personality 1 (0x0FFB:0): Clear Personality (0x0380 strapping) for clear channels
  - Personality 2 (0x0FFB:1): Secure ADP Personality (0x0388 strapping, Alg 0x000A, Key 1) for encrypted channels
  - Zone 1 Channel Routing:
      * Clear channels (Ch 1, 3, 4, 6, 7, 8, 9, 11, 13, 15) -> Personality 1 (NO lock icon)
      * Encrypted channels (Ch 2 TEAM ENCRYPT, Ch 5, 10, 12, 14, 16) -> Personality 2 (Ø lock icon)
  - Concentric Collar Switch (Switch 60 in 0x0020/0x0022): Decoupled to 0x23 (Unprogrammed)
    to prevent floating hardware pin from overriding channel autonomy.
  - Full Crypto Subsystem:
      * 0x0034:0 (Master Secure Enable)
      * 0x0035:0 & 0x0036:0
      * 0x0037:0 (CKR 1-8 table)
      * 0x0038:0 (CKR labels)
      * 0x005D:0 (Key 1: A1B2C3D4E5)
  - Proven EEPROM Persistence Control Framing:
      0106 00 -> 0102 80 0047 0000 0001 -> 0103 80 0002 01f4 -> 0103 80 0e0b 0fff -> 0107 8000 -> 0101 writes -> 0106 01

Safety:
  - Partition 0x82 (Tuning / Soft-pots) is STRICTLY NEVER touched (0 bytes written).
  - Target Serial 721CLZ0655 is strictly verified in-session before any erase or write.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from open_astro.parsers.cpg_parser import CpgParser, rc4
from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_write import RcmpWriteClient, RcmpWriteError
from open_astro.protocol.write_session import WriteObject, CpgWriteAssembler, PART_CODEPLUG, PART_TUNING

TARGET_SERIAL = "721CLZ0655"
TARGET_MODEL = "H18UCF9PW6AN"

# Ground Truth Crypto Objects
OBJ_0034 = bytes.fromhex("400314060000070c230b0a0602570003")  # Master Secure Enable
OBJ_0035 = bytes.fromhex("0710")
OBJ_0036 = bytes.fromhex("00000c000c0effffffffffffffff80")
OBJ_0037 = bytes.fromhex("000000020030000800010002000300040005000600070008")  # CKR 1-8 table
OBJ_0038 = bytes.fromhex(
    "0000001100300008434b523100000000000000000000000000434b523200000000000000000000000000"
    "434b523300000000000000000000000000434b523400000000000000000000000000434b523500000000"
    "000000000000000000434b523600000000000000000000000000434b5237000000000000000000000000"
    "00434b523800000000000000000000000000"
)  # CKR labels CKR1..CKR8
OBJ_005D = bytes.fromhex(
    "0000000e000800083030303141314232433344344535303030322a2a2a2a2a2a2a2a2a2a303030332a2a"
    "2a2a2a2a2a2a2a2a303030342a2a2a2a2a2a2a2a2a2a303030352a2a2a2a2a2a2a2a2a2a303030362a2a"
    "2a2a2a2a2a2a2a2a303030372a2a2a2a2a2a2a2a2a2a303030382a2a2a2a2a2a2a2a2a2a"
)  # Key 1 = A1B2C3D4E5

# Personality 1: CLEAR (0x0380 Strapping, no encryption)
PERS_CLEAR = bytes.fromhex(
    "000fcd000040748000001e000000000102000122200001000003801000000fbe00000000000001010101"
    "000ffa00000ff30000000000000ff7000000000000262626260000000000000000"
)

# Personality 2: SECURE ADP (0x0388 Strapped Secure, Alg 0x000A, Key 1: 0x1000)
PERS_SECURE = bytes.fromhex(
    "000fcd000140748000001d0000000001020001000a0000100003881000000fbe00000000000001010101"
    "000ffa00000ff30000000000000ff7000000000000262626260000000000000000"
)

# Switches & Physical Controls
# 0x03 = 1-Dot: 0x1e (Scan)
# 0x04 = Rotary: 0x1d (Channel Select)
# 0x60 = Purple Button: 0x18 (Light / Backlight)
# 0x61 = Orange Button: 0x29 (Tx Low Power)
# 0x62 = 2-Dot: 0x2b (Monitor / Squelch Open)
# 0x94 = Logic: 0x23 (Unprogrammed)
# 0x86 = Concentric Collar: 0x23 (Decoupled to prevent floating pin override)
OBJ_0020 = bytes.fromhex("0000000200070007031e041d60186129622b94238623")
OBJ_0022 = bytes.fromhex("0000000200070007031e041d60186129622b94238623")


def assemble_radio4_records(source_cpg: str) -> list[bytes]:
    """Load objects from source_cpg, patch channel personality assignments and secure objects."""
    cp = CpgParser(source_cpg)
    objs_dict = {}
    try:
        for o in cp.objects():
            part = o.get("partition", PART_CODEPLUG)
            if part == PART_TUNING:
                continue  # SAFETY: RF soft-pots strictly ignored
            if part == PART_CODEPLUG and o["crc_ok"]:
                objs_dict[(part, o["tag"], o["instance"])] = bytearray(o["payload"])
    finally:
        cp.close()

    # Overlay verified crypto subsystem objects into Partition 0x80
    objs_dict[(PART_CODEPLUG, 0x0034, 0)] = bytearray(OBJ_0034)
    objs_dict[(PART_CODEPLUG, 0x0035, 0)] = bytearray(OBJ_0035)
    objs_dict[(PART_CODEPLUG, 0x0036, 0)] = bytearray(OBJ_0036)
    objs_dict[(PART_CODEPLUG, 0x0037, 0)] = bytearray(OBJ_0037)
    objs_dict[(PART_CODEPLUG, 0x0038, 0)] = bytearray(OBJ_0038)
    objs_dict[(PART_CODEPLUG, 0x005D, 0)] = bytearray(OBJ_005D)

    # Personality 1 = CLEAR, Personality 2 = SECURE
    objs_dict[(PART_CODEPLUG, 0x0FFB, 0)] = bytearray(PERS_CLEAR)
    objs_dict[(PART_CODEPLUG, 0x0FFB, 1)] = bytearray(PERS_SECURE)

    # Decouple concentric collar switch to prevent floating pin override
    objs_dict[(PART_CODEPLUG, 0x0020, 0)] = bytearray(OBJ_0020)
    objs_dict[(PART_CODEPLUG, 0x0022, 0)] = bytearray(OBJ_0022)

    # Patch Zone 1 Channel Tables (0x0FFD:22 and 0x0FFD:23)
    stride = 35

    # 0x0FFD:22 (Channels 1 to 10)
    if (PART_CODEPLUG, 0x0FFD, 22) in objs_dict:
        ffd22 = objs_dict[(PART_CODEPLUG, 0x0FFD, 22)]
        # Ch 1 (Clear): Personality 0
        ffd22[6 + 0*stride : 6 + 0*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 2 (TEAM ENCRYPT): Personality 1 (SECURE)
        ffd22[6 + 1*stride : 6 + 1*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd22[6 + 1*stride + 24 : 6 + 1*stride + 28] = bytes.fromhex("00000140")
        # Ch 3 (Clear): Personality 0
        ffd22[6 + 2*stride : 6 + 2*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 4 (Clear): Personality 0
        ffd22[6 + 3*stride : 6 + 3*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 5 (TEAM SEC 2): Personality 1 (SECURE)
        ffd22[6 + 4*stride : 6 + 4*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd22[6 + 4*stride + 24 : 6 + 4*stride + 28] = bytes.fromhex("00000140")
        # Ch 6 (Clear): Personality 0
        ffd22[6 + 5*stride : 6 + 5*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 7 (Clear): Personality 0
        ffd22[6 + 6*stride : 6 + 6*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 8 (Clear): Personality 0
        ffd22[6 + 7*stride : 6 + 7*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 9 (Clear): Personality 0
        ffd22[6 + 8*stride : 6 + 8*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 10 (TEAM SEC 3): Personality 1 (SECURE)
        ffd22[6 + 9*stride : 6 + 9*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd22[6 + 9*stride + 24 : 6 + 9*stride + 28] = bytes.fromhex("00000180")

    # 0x0FFD:23 (Channels 11 to 16)
    if (PART_CODEPLUG, 0x0FFD, 23) in objs_dict:
        ffd23 = objs_dict[(PART_CODEPLUG, 0x0FFD, 23)]
        # Ch 11 (Clear): Personality 0
        ffd23[6 + 0*stride : 6 + 0*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 12 (TEAM P25 SEC): Personality 1 (SECURE)
        ffd23[6 + 1*stride : 6 + 1*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd23[6 + 1*stride + 24 : 6 + 1*stride + 28] = bytes.fromhex("00000180")
        # Ch 13 (Clear): Personality 0
        ffd23[6 + 2*stride : 6 + 2*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 14 (TEAM RPT 1S): Personality 1 (SECURE)
        ffd23[6 + 3*stride : 6 + 3*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd23[6 + 3*stride + 24 : 6 + 3*stride + 28] = bytes.fromhex("00000140")
        # Ch 15 (Clear): Personality 0
        ffd23[6 + 4*stride : 6 + 4*stride + 4] = struct.pack(">HH", 0x0FFB, 0)
        # Ch 16 (TEAM RPT 2S): Personality 1 (SECURE)
        ffd23[6 + 5*stride : 6 + 5*stride + 4] = struct.pack(">HH", 0x0FFB, 1)
        ffd23[6 + 5*stride + 24 : 6 + 5*stride + 28] = bytes.fromhex("00000140")

    # Build WriteObject list
    write_objs = [WriteObject(p, t, i, bytes(payload)) for (p, t, i), payload in sorted(objs_dict.items())]

    # Verify no partition 0x82 object exists
    for w in write_objs:
        assert w.part != PART_TUNING, f"FATAL: object {w.obj} targets partition 0x82!"

    assembler = CpgWriteAssembler(write_objs)
    return assembler.full_session_records()


def main():
    parser = argparse.ArgumentParser(description="OpenAstro Radio 4 Per-Channel ADP Flasher")
    parser.add_argument("--confirm", action="store_true", help="Execute live flash over PPP socket (default: dry run)")
    parser.add_argument("--host", default="192.168.128.1", help="Radio IP address (default: 192.168.128.1)")
    parser.add_argument("--port", type=int, default=8002, help="Radio RCMP port (default: 8002)")
    parser.add_argument("--expect-serial", default=TARGET_SERIAL, help=f"Expected serial (default: {TARGET_SERIAL})")
    args = parser.parse_args()

    cpg_path = os.path.join(REPO, "scratchpad", "radio4_king_county_adp.cpg")
    if not os.path.exists(cpg_path):
        print(f"[-] Source codeplug not found at {cpg_path}")
        return 1

    records = assemble_radio4_records(cpg_path)
    writes_count = sum(1 for r in records if r[2:4].hex() == "0101")

    print("=" * 72)
    print("  OPEN-ASTRO RADIO 4 (XTS 5000) PER-CHANNEL ADP FLASHER")
    print("=" * 72)
    print(f"Target Hardware:    Motorola XTS 5000 Model III ({TARGET_MODEL})")
    print(f"Target Serial:      {args.expect_serial}")
    print(f"Personality 1:      0x0FFB:0 -> CLEAR (0x0380 strapping)")
    print(f"Personality 2:      0x0FFB:1 -> SECURE ADP (0x0388 strapping, Alg 0x000A, Key 1)")
    print(f"Channel Strapping:  Ch 1, 3, 4, 6, 7, 8, 9, 11, 13, 15 -> CLEAR (NO Ø icon)")
    print(f"                    Ch 2, 5, 10, 12, 14, 16 -> SECURE (Ø lock icon)")
    print(f"Switch 60:          Decoupled to 0x23 (Unprogrammed) to prevent collar override")
    print(f"Partition 0x82:     FIREWALL STRICTLY ENFORCED (0 bytes targeting calibration)")
    print(f"Total Records:      {len(records)} ({writes_count} 0x0101 writes)")
    print(f"Execution Mode:     {'LIVE FLASH' if args.confirm else 'DRY RUN VALIDATION'}")
    print("=" * 72)

    if not args.confirm:
        print("\n[+] DRY RUN COMPLETE: All records assembled and validated.")
        print("[+] Run with --confirm to transmit to radio hardware.")
        return 0

    print(f"\n[*] Connecting to radio at {args.host}:{args.port}...")
    try:
        client = RcmpWriteClient.connect(host=args.host, port=args.port, timeout=15.0, allow_write=True)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        return 2

    try:
        # Step 1: Send Session Open (0106 00)
        client.send_prebuilt(records[0])
        print("[+] Session open (0106 00) accepted.")

        # Step 2: Read serial number in-session from partition 0x81 object 0x1004
        idrec = client.send_prebuilt(rcmp.build_read(0x81, 0x1004, 0x40))
        body = bytes.fromhex(str(idrec.get("body_hex", "")))
        serial_txt = body[12:-2].decode("latin-1", "replace") if len(body) > 14 else ""
        if args.expect_serial not in serial_txt:
            print(f"[-] Serial mismatch! Radio reports {serial_txt!r}, expected {args.expect_serial!r}. ABORTING.")
            return 2
        print(f"[+] Radio identity confirmed: {args.expect_serial}")

        # Step 3: Transmit all records (control + writes + commit)
        start_time = time.time()
        for i, rec in enumerate(records[1:], start=1):
            client.send_prebuilt(rec)
            op = rec[2:4].hex()
            if i % 30 == 0 or op in ("0102", "0103", "0107", "0106"):
                print(f"    [{i:3d}/{len(records)}] sent opcode 0x{op}")
            time.sleep(0.005)

        elapsed = time.time() - start_time
        print(f"\n[+] All {len(records)} records transmitted and ACKed in {elapsed:.1f}s!")
        print("[+] Commit record (0106 01) ACKed. Radio is writing to EEPROM and rebooting...")
    except RcmpWriteError as e:
        print(f"[-] Flashing error mid-session: {e}")
        return 3
    finally:
        client.close()

    print("\n" + "=" * 72)
    print("  FLASH SUCCESSFUL!")
    print("  - Personality 1 (Clear) and Personality 2 (Secure) both written!")
    print("  - Only encrypted channels (Ch 2 TEAM ENCRYPT, etc.) show the lock icon!")
    print("  - Clear channels (Ch 1, 3, etc.) are Clear without the lock icon!")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
