"""Derive the authoritative partition/object allowlist from CPS capture sessions.

The safe-write allowlist must not be a magic number (an earlier flasher guard
"reject < 0x0020_0000" was meaningless -- ISH items are keyed by partition, not
by memory address). This script builds the allowlist from GROUND TRUTH: the
partitions and object-id ranges that Motorola CPS itself addressed in the
captured read/tuner sessions. Writing is then restricted to exactly the
partitions CPS uses for the codeplug, and partition 0x82 (tuning / soft-pot
calibration) -- which CPS only ever touches in a SEPARATE tuner session -- is
refused outright.

Run:  python tools/derive_partition_map.py   (writes schema/partition_map.json)
It is reproducible: re-run it whenever new capture sessions are added.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from open_astro.protocol import rcmp  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What each partition is, and whether a codeplug write may target it. Roles come
# from the RCMP wire analysis (docs/RCMP_WIRE_PROTOCOL.md); the object ranges are
# measured from the captures below.
ROLES = {
    0x80: ("codeplug (plaintext objects)", True),
    0x81: ("codeplug (RC4-encrypted streams)", True),
    0x82: ("tuning / soft-pot calibration -- NEVER write (unrecoverable)", False),
    0x85: ("codeplug (unidentified region, read within the codeplug session)", True),
}


def main() -> int:
    part_objs = defaultdict(list)
    sources = []
    for f in sorted(glob.glob(os.path.join(REPO, "captures", "cps_*_decoded.json"))):
        d = json.load(open(f))
        hx = d.get("OUT host->radio", {}).get("rcmp_stream_hex", "")
        if not hx:
            continue
        used = False
        for rec in rcmp.iter_records(bytes.fromhex(hx)):
            op = int.from_bytes(rec[:2], "big")
            if op in (rcmp.OP_READ, rcmp.OP_WRITE) and len(rec) >= 7:
                part = rec[2]
                obj = int.from_bytes(rec[3:5], "big")
                part_objs[part].append(obj)
                used = True
        if used:
            sources.append(os.path.basename(f))

    if not part_objs:
        print("[-] no capture object addressing found", file=sys.stderr)
        return 1

    partitions = {}
    for part in sorted(part_objs):
        objs = sorted(set(part_objs[part]))
        role, writable = ROLES.get(part, ("UNKNOWN -- not observed in analysis", False))
        partitions[f"0x{part:02x}"] = {
            "role": role,
            "writable": writable,
            "obj_min": objs[0],
            "obj_max": objs[-1],
            "observed_objs": len(objs),
        }

    out = {
        "_comment": ("Authoritative RCMP partition/object allowlist for codeplug "
                     "writes. Derived from Motorola CPS's own addressing in the "
                     "capture sessions listed in 'sources' -- these are the "
                     "partitions and object-id ranges CPS itself used. A codeplug "
                     "write may target only partitions with writable=true; 0x82 "
                     "(tuning/soft-pots) is a separate tuner session and is never "
                     "writable. Regenerate with tools/derive_partition_map.py."),
        "sources": sources,
        "partitions": partitions,
    }
    dest = os.path.join(REPO, "schema", "partition_map.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"[+] wrote {dest}")
    print(f"    sources: {sources}")
    for p, meta in partitions.items():
        flag = "WRITABLE" if meta["writable"] else "REFUSED "
        print(f"    {p} [{flag}] objs {meta['obj_min']}..{meta['obj_max']} "
              f"({meta['observed_objs']})  {meta['role']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
