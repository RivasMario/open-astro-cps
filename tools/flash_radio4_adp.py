#!/usr/bin/env python3
"""OpenAstro Standalone Automated FLASHcode Upgrade & ADP Flasher for Radio 4 (XTS 5000).

Hardware Target:
  - Radio: Motorola XTS 5000 Model III (700/800 MHz)
  - Serial: 721CLZ0655
  - Model: H18UCF9PW6AN
  - Current FLASHcode: 400008-002000-0
  - Target FLASHcode:  400008-006000-1 (Option A: Q667 ADP software encryption)
  - Key 1:             A1B2C3D4E5 (40-bit RC4 Software ADP)
  - Features Armed:    Q806 ASTRO Digital + Q53 FPP + Q667 Software ADP + Q888 SSK
  - Fleet Channels:    13 Zones / 194 Channels (Redmond PD & King County Fleet)
  - Controls:          Side 3 (2-Dot) Scan Toggle [Z icon], Side 2 Monitor, Side 1 Light
  - Safety Firewall:   Partition 0x82 (RF Calibration / Soft-pots) strictly NEVER touched!
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Windows consoles default to cp1252; force UTF-8 so emoji/arrows in
# output do not raise UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))

from open_astro.parsers.cpg_parser import CpgParser, rc4
from open_astro.protocol import rcmp, unlock_session
from open_astro.protocol.rcmp_write import RcmpWriteClient
from open_astro.protocol.rcmp_transport import RcmpReadClient
from open_astro.protocol.write_session import CpgWriteAssembler
import rcmp_replay_write

SERIAL = "721CLZ0655"
MODEL = "H18UCF9PW6AN"
TARGET_FLASHCODE = "400008-006000-1"

# Ground Truth Identity & License Blobs
OBJ_1004 = bytes.fromhex(
    "0212373231434c5a303635350048313855434639505736414e000000000000030005000100000000000000000000101218010001001c0100101218091835000000000000"
)
# Depot-derived license bitmask for 400008-006000-1 (byte 15 = 0x3c)
OBJ_1005 = bytes.fromhex(
    "1d17325b7ef5b534fbebb9e20218c53c008000801000000310e8000000000c040000000008000002000000"
)
# ASCII FLASHcode: 8-byte header + "400008-006000-1\0"
OBJ_1006 = bytes.fromhex(
    "00000010000100013430303030382d3030363030302d3100"
)

# Secure Subsystem Objects
OBJ_0034 = bytes.fromhex("400314060000070c230b0a0602570003")  # Radio Wide Secure Master Enable
OBJ_0035 = bytes.fromhex("0710")
OBJ_0036 = bytes.fromhex("00000c000c0effffffffffffffff80")
OBJ_0037 = bytes.fromhex("000000020030000800010002000300040005000600070008")  # CKR 1-8
OBJ_0038 = bytes.fromhex(
    "0000001100300008434b523100000000000000000000000000434b523200000000000000000000000000434b523300000000000000000000000000434b523400000000000000000000000000434b523500000000000000000000000000434b523600000000000000000000000000434b523700000000000000000000000000434b523800000000000000000000000000"
)
OBJ_005D = bytes.fromhex(
    "0000000e000800083030303141314232433344344535303030322a2a2a2a2a2a2a2a2a2a303030332a2a2a2a2a2a2a2a2a2a303030342a2a2a2a2a2a2a2a2a2a303030352a2a2a2a2a2a2a2a2a2a303030362a2a2a2a2a2a2a2a2a2a303030372a2a2a2a2a2a2a2a2a2a303030382a2a2a2a2a2a2a2a2a2a"
)


def build_radio4_stream(source_cpg: str, template_pcap: str | None = None) -> list[bytes]:
    """Assemble the validated write records for Radio 4 (XTS 5000)."""
    cp = CpgParser(source_cpg)
    cpg_objs = {}
    for entry in cp.directory():
        p, item, inst = entry['partition'], entry['item_id'], entry['instance']
        if p == 0x82:
            continue  # RF calibration firewall!
        strm_name = 'Strm_' + str(entry['stream'])
        strm = cp._read(['DataStg', strm_name])
        dec = rc4(cp.key, strm)[6:-2]
        cpg_objs[(p, item, inst)] = dec
    cp.close()

    custom_objs = {
        (0x81, 0x1004, 0): OBJ_1004,
        (0x81, 0x1005, 0): OBJ_1005,
        (0x81, 0x1006, 0): OBJ_1006,
        (0x80, 0x0034, 0): OBJ_0034,
        (0x80, 0x0035, 0): OBJ_0035,
        (0x80, 0x0036, 0): OBJ_0036,
        (0x80, 0x0037, 0): OBJ_0037,
        (0x80, 0x0038, 0): OBJ_0038,
        (0x80, 0x005d, 0): OBJ_005D,
    }

    if template_pcap and os.path.exists(template_pcap):
        recs, _ = rcmp_replay_write.extract_out_records(template_pcap, 5)
        writes = [r for r in recs if r[:2].hex() == '0101']
        pcap_keys = set((r[2], int.from_bytes(r[3:5], 'big'), int.from_bytes(r[5:7], 'big')) for r in writes)

        edits, adds = [], []
        for k, data in cpg_objs.items():
            p, o, i = k
            if p == 0x82:
                continue
            val = custom_objs.get(k, data)
            arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
            (edits if k in pcap_keys else adds).append(arg)

        for k, val in custom_objs.items():
            if k not in cpg_objs:
                p, o, i = k
                if p == 0x82:
                    continue
                arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
                (edits if k in pcap_keys else adds).append(arg)

        edited_records = rcmp_replay_write.apply_edits(recs, edits, rcmp)
        final_records = rcmp_replay_write.apply_adds(edited_records, adds, rcmp)
        return rcmp_replay_write.validate(final_records, rcmp)

    # Pure-Python cross-platform synthesis (no gitignored .pcap needed)
    merged = dict(cpg_objs)
    merged.update(custom_objs)
    raw_records: list[bytes] = [bytes([0x01, 0x06, 0x00])]
    for pr in CpgWriteAssembler.default_prepare_records():
        raw_records.append(pr[2:])
    for (p, o, i) in sorted(merged.keys(), key=lambda x: (x[0] == 0x81, x[0], x[1], x[2])):
        if p == 0x82:
            continue
        raw_records.append(rcmp.build_write(p, o, merged[(p, o, i)], i)[2:])
    raw_records.append(bytes([0x01, 0x06, 0x01]))
    return rcmp_replay_write.validate(raw_records, rcmp)


def main():
    parser = argparse.ArgumentParser(description="Radio 4 (XTS 5000) Option A FLASHcode Upgrade & Flasher")
    parser.add_argument("--write", action="store_true", help="Transmit over TCP link (default is dry run)")
    parser.add_argument("--host", default="192.168.128.1", help="Radio IP address over PPP (default 192.168.128.1)")
    parser.add_argument("--port", type=int, default=8002, help="Radio RCMP TCP port (default 8002)")
    args = parser.parse_args()

    cpg_path = os.path.join(REPO, "backups", "721CLZ0655_OptionA_ADP.cpg")
    pcap_path = os.path.join(REPO, "captures", "cps_20261023_101302.pcap")

    print("=" * 70)
    print("  OPEN-ASTRO RADIO 4 (XTS 5000) FLASHCODE UPGRADE (OPTION A)")
    print("=" * 70)
    print(f"Target Serial:      {SERIAL}")
    print(f"Target Model:       {MODEL} (XTS 5000 Model III 700/800 MHz)")
    print(f"Current FLASHcode:  400008-002000-0")
    print(f"Target FLASHcode:   {TARGET_FLASHCODE} (Q806 Digital + Q53 FPP + Q667 ADP + Q888 SSK)")
    print(f"Software Key 1:     A1B2C3D4E5 (40-bit RC4 Software ADP Encryption)")
    print(f"Controls:           Side 3 (2-Dot) Scan Toggle [Z Icon], Side 2 Monitor, Side 1 Light")
    print(f"RF Firewall:        Partition 0x82 STRICTLY ENFORCED (0 bytes written)")
    print(f"Execution Mode:     {'LIVE WRITE' if args.write else 'DRY RUN VALIDATION'}")
    print("=" * 70)

    framed = build_radio4_stream(cpg_path, pcap_path)
    print(f"[+] Total validated RCMP records compiled: {len(framed)}")

    if not args.write:
        print("\n[+] DRY RUN SUCCESSFUL: All records validated byte-exact against CRC-16 CCITT.")
        print("[+] Partition 0x82 RF firewall verified: 0 objects targeting calibration.")
        print("[+] Run with --write to transmit over PPP link.")
        return 0

    print(f"\n[!] Beginning transmission of {len(framed)} records to {args.host}:{args.port}...")
    time.sleep(0.5)
    client = RcmpWriteClient.connect(host=args.host, port=args.port, allow_write=True, src_port=0)
    try:
        def _send_raw(fr: bytes) -> None:
            client._conn.sendall(fr)

        def _recv_body() -> bytes:
            rec = client._recv_record()
            return rec[2:] if len(rec) > 2 else b""

        usess = unlock_session.UnlockSession(_send_raw, _recv_body, part=0x81, inst=0)
        usess.exchange()
        ack_rec = client._recv_record()
        print(f"[+] UnlockSecurity (0x0107) 32-byte LFSR seed->response ACKed: {ack_rec.hex()}")

        for i, fr in enumerate(framed):
            client.send_prebuilt(fr)
            time.sleep(0.005)
            if (i + 1) % 50 == 0 or (i + 1) == len(framed):
                print(f"    Transmitted {i+1}/{len(framed)} records...")
        print(f"[+] All {len(framed)} records ACKed by radio bootloader!")
    finally:
        client.close()

    print("\n[+] SUCCESS! Radio 4 is now rebooting with FLASHcode 400008-006000-1 and ADP Active!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
