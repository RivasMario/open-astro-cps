#!/usr/bin/env python3
"""
Utility to diff two RCMP capture files (JSONL format).

Usage:
    python diff_captures.py <capture_a.jsonl> <capture_b.jsonl>

The script loads both files, normalizes each packet dict (removes any
`timestamp` field and sorts keys), and then prints a unified diff of the
JSON serializations.  It is intended for quick sanity‑checks between the
live virtual‑radio capture and a reference capture from a real radio.
"""

import json, sys, pathlib
from difflib import unified_diff

def load_normalized(path: pathlib.Path):
    packets = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                pkt = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Remove volatile fields that change per run
            pkt.pop("timestamp", None)
            # Ensure deterministic ordering
            packets.append(json.dumps(pkt, sort_keys=True))
    return packets

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: diff_captures.py <file1.jsonl> <file2.jsonl>")
        sys.exit(1)
    a_path = pathlib.Path(sys.argv[1])
    b_path = pathlib.Path(sys.argv[2])
    a_packets = load_normalized(a_path)
    b_packets = load_normalized(b_path)
    diff = unified_diff(a_packets, b_packets, fromfile=str(a_path), tofile=str(b_path), lineterm="")
    for line in diff:
        print(line)
