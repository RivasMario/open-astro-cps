"""Tests for the capture validators tools/verify_handshake.py and
tools/verify_codeplug.py.

Both tools are CLI scripts that read an RCMP capture JSONL (the schema
tools/virtual_radio.py writes) and exit 0 on PASS, 1 on FAIL. These tests build
synthetic captures with the exact wire framing the virtual radio uses, so a
regression in the parsers (seed extraction, READ_ACK layout, CRC) is caught
before the one-shot real-CPS capture on the Fedora rig.
"""
import json
import os
import struct
import subprocess
import sys

import pytest

from open_astro.protocol.unlock import unlock_response
from open_astro.parsers.cpg_parser import CpgParser, crc16_ccitt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
REF_CPG = os.path.join(REPO, "backups", "721CLZ0655.cpg")

# Fixed 32-byte seed for the handshake fixtures.
SEED = bytes(range(1, 33))


def _event(record: bytes, direction: str) -> dict:
    opcode = (record[0] << 8) | record[1]
    return {"direction": direction, "opcode": opcode, "record_hex": record.hex()}


def _write_jsonl(path, events):
    with open(path, "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")


def _seed_response_record(seed: bytes) -> bytes:
    # virtual_radio seed response: opcode 0x8107 + 32-byte seed.
    return struct.pack(">H", 0x8107) + seed


def _client_unlock_record(resp32: bytes) -> bytes:
    # client UnlockSecurity: opcode 0x0107 + 32-byte scrambled response.
    return struct.pack(">H", 0x0107) + resp32


def _read_ack_record(obj: int, inst: int, data: bytes) -> bytes:
    # Mirrors tools/virtual_radio.py READ_ACK framing for Partition 0x80.
    acklen = len(data)
    header = struct.pack(">BBHHHHH", 0x00, 0x80, obj, inst, 0, 0x0000, acklen)
    return struct.pack(">H", 0x8100) + header + data + struct.pack(">H", crc16_ccitt(data))


def _run(tool: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, os.path.join(TOOLS, tool), *args],
        capture_output=True, text=True,
    )


# --- verify_handshake --------------------------------------------------------

def test_handshake_pass(tmp_path):
    cap = tmp_path / "hs_pass.jsonl"
    _write_jsonl(cap, [
        _event(_seed_response_record(SEED), "OUT"),
        _event(_client_unlock_record(unlock_response(SEED)), "IN"),
    ])
    r = _run("verify_handshake.py", str(cap))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


def test_handshake_fail_wrong_response(tmp_path):
    bad = bytearray(unlock_response(SEED))
    bad[0] ^= 0xFF
    cap = tmp_path / "hs_fail.jsonl"
    _write_jsonl(cap, [
        _event(_seed_response_record(SEED), "OUT"),
        _event(_client_unlock_record(bytes(bad)), "IN"),
    ])
    r = _run("verify_handshake.py", str(cap))
    assert r.returncode == 1
    assert "FAIL" in r.stdout


def test_handshake_no_handshake(tmp_path):
    cap = tmp_path / "hs_none.jsonl"
    _write_jsonl(cap, [_event(struct.pack(">H", 0x0106) + b"\x00", "IN")])
    r = _run("verify_handshake.py", str(cap))
    assert r.returncode == 1


# --- verify_codeplug ---------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(REF_CPG), reason="reference .cpg missing")
def test_codeplug_pass(tmp_path):
    ref = CpgParser.load_file(REF_CPG)
    objs = sorted(k for k in ref if k[0] == 0x80)[:4]
    assert objs, "no 0x80 objects in reference cpg"
    events = [_event(_read_ack_record(obj, inst, bytes(ref[(0x80, obj, inst)])), "OUT")
              for (_p, obj, inst) in objs]
    cap = tmp_path / "cp_pass.jsonl"
    _write_jsonl(cap, events)
    r = _run("verify_codeplug.py", str(cap), "--cpg", REF_CPG)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


@pytest.mark.skipif(not os.path.exists(REF_CPG), reason="reference .cpg missing")
def test_codeplug_fail_mutated(tmp_path):
    ref = CpgParser.load_file(REF_CPG)
    obj, inst = sorted(k[1:] for k in ref if k[0] == 0x80)[0]
    data = bytearray(ref[(0x80, obj, inst)])
    data[0] ^= 0xFF  # corrupt one byte; CRC recomputed so divergence is vs the .cpg
    cap = tmp_path / "cp_fail.jsonl"
    _write_jsonl(cap, [_event(_read_ack_record(obj, inst, bytes(data)), "OUT")])
    r = _run("verify_codeplug.py", str(cap), "--cpg", REF_CPG)
    assert r.returncode == 1
    assert "FAIL" in r.stdout


@pytest.mark.skipif(not os.path.exists(REF_CPG), reason="reference .cpg missing")
def test_codeplug_bad_crc_detected(tmp_path):
    ref = CpgParser.load_file(REF_CPG)
    obj, inst = sorted(k[1:] for k in ref if k[0] == 0x80)[0]
    data = bytes(ref[(0x80, obj, inst)])
    rec = bytearray(_read_ack_record(obj, inst, data))
    rec[-1] ^= 0xFF  # corrupt the trailing CRC-16
    cap = tmp_path / "cp_crc.jsonl"
    _write_jsonl(cap, [_event(bytes(rec), "OUT")])
    r = _run("verify_codeplug.py", str(cap), "--cpg", REF_CPG)
    assert r.returncode == 1
    assert "CRC" in r.stdout
