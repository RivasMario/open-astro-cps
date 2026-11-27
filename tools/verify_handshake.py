#!/usr/bin/env python3
"""
Verify the ``UnlockSecurity`` (0x0107 / 0x2011) handshake against ground truth.

Given an RCMP capture (the JSONL that ``tools/virtual_radio.py`` writes, i.e.
the file produced by the Docker CPS-capture rig), this tool pulls the radio's
32-byte seed and the client's 32-byte scrambled response out of the handshake
exchange, recomputes the response with our clean-room
``open_astro.protocol.unlock.unlock_response`` and checks they match.

If the capture came from real Motorola CPS (NextGen10.dll) driving the virtual
radio, a PASS proves our reimplementation reproduces the real seed->response
transform for that exact seed -- the handshake is understood, not guessed.

This is a read-only analysis tool: it only reads a .jsonl. It never touches a
radio and performs no network I/O.

Usage:
    python tools/verify_handshake.py captures/rcmp_trace_<timestamp>.jsonl

Exit code 0 on PASS, 1 on mismatch or if no handshake was found.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from open_astro.protocol.unlock import SEED_LEN, unlock_response

# Handshake request opcodes and their response (request | 0x8000) forms.
REQ_OPCODES = (0x0107, 0x2011)
RESP_OPCODES = tuple(op | 0x8000 for op in REQ_OPCODES)  # 0x8107, 0xA011


def _record_bytes(event: dict) -> bytes:
    """Return the RCMP record (opcode + payload) for a capture event.

    Prefer ``record_hex``; fall back to ``framed_hex`` (strip the 2-byte length
    prefix). Returns b"" if neither is present/parseable.
    """
    rec = event.get("record_hex")
    if isinstance(rec, str) and rec:
        return bytes.fromhex(rec)
    framed = event.get("framed_hex")
    if isinstance(framed, str) and len(framed) >= 4:
        return bytes.fromhex(framed)[2:]
    return b""


def _opcode(record: bytes) -> int | None:
    if len(record) < 2:
        return None
    return (record[0] << 8) | record[1]


def _extract_seed(payload: bytes) -> bytes | None:
    """Pull the 32-byte seed out of a seed-response payload (bytes after opcode).

    virtual_radio frames the seed response as opcode + 32-byte seed (no status
    byte). Be defensive about a leading status byte or trailing padding in a
    real capture: take the exact 32 bytes if present, else a 33-byte
    status+seed, else the last 32 bytes.
    """
    if len(payload) == SEED_LEN:
        return payload
    if len(payload) == SEED_LEN + 1:  # status byte + seed
        return payload[1:]
    if len(payload) > SEED_LEN:
        return payload[-SEED_LEN:]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the 0x0107 UnlockSecurity handshake from a capture.")
    ap.add_argument("capture", help="RCMP capture JSONL (from virtual_radio.py / Docker rig)")
    args = ap.parse_args()

    seed: bytes | None = None
    client_resp: bytes | None = None

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
            record = _record_bytes(event)
            opcode = _opcode(record)
            if opcode is None:
                continue
            payload = record[2:]
            # Radio -> client: seed response.
            if opcode in RESP_OPCODES and seed is None:
                cand = _extract_seed(payload)
                if cand is not None:
                    seed = cand
            # Client -> radio: scrambled response (last 32 bytes of the request).
            elif opcode in REQ_OPCODES and len(payload) >= SEED_LEN:
                client_resp = payload[-SEED_LEN:]

    if seed is None:
        print("FAIL: no 32-byte seed response (opcode 0x8107/0xA011) found in capture.")
        print("      Was the virtual radio run with --challenge-security?")
        return 1
    if client_resp is None:
        print("FAIL: no client UnlockSecurity response (opcode 0x0107/0x2011 with >=32-byte payload) found.")
        print(f"      Seed observed: {seed.hex()}")
        return 1

    expected = unlock_response(seed)
    ok = expected == client_resp

    print(f"seed (radio -> client):      {seed.hex()}")
    print(f"response (client -> radio):  {client_resp.hex()}")
    print(f"unlock_response(seed):       {expected.hex()}")
    if ok:
        print("\nPASS: client response matches our unlock_response(seed).")
        print("      The 0x0107 seed->response transform is reproduced exactly.")
        return 0
    print("\nFAIL: client response does NOT match unlock_response(seed).")
    # Show first differing byte to aid analysis.
    for i, (a, b) in enumerate(zip(expected, client_resp)):
        if a != b:
            print(f"      first mismatch at byte {i}: expected 0x{a:02x}, got 0x{b:02x}")
            break
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
