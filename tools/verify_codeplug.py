#!/usr/bin/env python3
"""
Verify a captured Partition 0x80 code-plug read against our reference .cpg.

Given an RCMP capture (the JSONL that ``tools/virtual_radio.py`` writes, i.e.
the file produced by the Docker CPS-capture rig) and a reference ``.cpg`` file,
this tool reassembles every object returned by a real ``OP_READ`` (0x0100 ->
0x8100 READ_ACK) on Partition 0x80 and diffs each object's bytes against the
same (partition, object, instance) in our offline ``CpgParser`` decode.

A clean match proves our .cpg decode produces the exact bytes the radio streams
over the wire -- the code-plug read format is understood, not guessed. It also
validates each READ_ACK's CRC-16-CCITT.

This is a read-only analysis tool: it only reads a .jsonl and a .cpg. It never
touches a radio and performs no network I/O.

Usage:
    python tools/verify_codeplug.py captures/rcmp_trace_<ts>.jsonl \
        --cpg backups/721CLZ0655.cpg

Exit code 0 when every captured object matches (and at least one was found),
1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from open_astro.parsers.cpg_parser import CpgParser, crc16_ccitt

PART_CODEPLUG = 0x80
READ_ACK = 0x8100
# READ_ACK record layout (matches tools/virtual_radio.py):
#   [0:2]  opcode 0x8100
#   [2]    status (0x00 = data follows; nonzero = no object)
#   [3]    partition
#   [4:6]  object
#   [6:8]  instance
#   [8:10] reqlen
#   [10:12] 0x0000
#   [12:14] acklen (length of the data region)
#   [14:14+acklen] data
#   [last 2] CRC-16-CCITT over data
_HDR_LEN = 14


def _record_bytes(event: dict) -> bytes:
    rec = event.get("record_hex")
    if isinstance(rec, str) and rec:
        return bytes.fromhex(rec)
    framed = event.get("framed_hex")
    if isinstance(framed, str) and len(framed) >= 4:
        return bytes.fromhex(framed)[2:]
    return b""


def _parse_read_ack(record: bytes):
    """Return (obj, inst, data, crc_ok) for a Partition 0x80 READ_ACK, else None."""
    if len(record) < _HDR_LEN + 2:
        return None
    opcode = (record[0] << 8) | record[1]
    if opcode != READ_ACK:
        return None
    status = record[2]
    part = record[3]
    if status != 0x00 or part != PART_CODEPLUG:
        return None  # error ack / not the code-plug partition
    obj = struct.unpack_from(">H", record, 4)[0]
    inst = struct.unpack_from(">H", record, 6)[0]
    acklen = struct.unpack_from(">H", record, 12)[0]
    data = record[_HDR_LEN:_HDR_LEN + acklen]
    if len(data) != acklen:
        return None  # truncated
    crc_field = struct.unpack_from(">H", record, _HDR_LEN + acklen)[0]
    crc_ok = crc16_ccitt(data) == crc_field
    return obj, inst, bytes(data), crc_ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a captured Partition 0x80 read against a reference .cpg.")
    ap.add_argument("capture", help="RCMP capture JSONL (from virtual_radio.py / Docker rig)")
    ap.add_argument("--cpg", required=True, help="Reference .cpg file to diff against")
    args = ap.parse_args()

    ref = CpgParser.load_file(args.cpg)  # CpgData: (part, obj, inst) -> bytes

    captured: dict[tuple[int, int], tuple[bytes, bool]] = {}
    with open(args.capture, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: line {lineno} is not valid JSON, skipping", file=sys.stderr)
                continue
            parsed = _parse_read_ack(_record_bytes(event))
            if parsed is None:
                continue
            obj, inst, data, crc_ok = parsed
            captured[(obj, inst)] = (data, crc_ok)

    if not captured:
        print("FAIL: no Partition 0x80 READ_ACK (opcode 0x8100, status 0x00) objects found in capture.")
        return 1

    matched = mismatched = crc_bad = missing = 0
    for (obj, inst), (data, crc_ok) in sorted(captured.items()):
        tag = f"obj=0x{obj:04x} inst={inst}"
        if not crc_ok:
            crc_bad += 1
            print(f"CRC  {tag}: READ_ACK CRC-16 mismatch over {len(data)} bytes")
        ref_data = ref.get_object(PART_CODEPLUG, obj, inst)
        if ref_data is None:
            missing += 1
            print(f"MISS {tag}: present in capture, absent from {os.path.basename(args.cpg)}")
        elif bytes(ref_data) == data:
            matched += 1
        else:
            mismatched += 1
            print(f"DIFF {tag}: capture {len(data)}B vs cpg {len(ref_data)}B")
            print(f"       capture: {data.hex()}")
            print(f"       cpg:     {bytes(ref_data).hex()}")

    total = len(captured)
    print(f"\n{matched}/{total} objects match; mismatched={mismatched}, "
          f"missing-in-cpg={missing}, crc-bad={crc_bad}")
    ok = matched == total and mismatched == 0 and missing == 0 and crc_bad == 0
    if ok:
        print("PASS: every captured Partition 0x80 object matches our .cpg decode (CRC valid).")
        return 0
    print("FAIL: capture and .cpg decode diverge (see rows above).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
