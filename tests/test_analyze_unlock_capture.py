"""Regression test for scripts/analyze_unlock_capture.py.

Builds a synthetic classic-pcap of an RCMP UnlockSecurity exchange (0x0107
request / 0x8107 seed reply / 0x0107 response over TCP :8002) and asserts the
analyzer reassembles it and confirms the seed->response against unlock_response.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys

from open_astro.protocol import rcmp
from open_astro.protocol.unlock import unlock_response

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "analyze_unlock_capture.py")


def _ipv4_tcp(src, dst, sport, dport, seq, payload):
    tcp = struct.pack(">HHIIBBHHH", sport, dport, seq, 0, (5 << 4), 0x18,
                      8192, 0, 0) + payload
    tot = 20 + len(tcp)
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, tot, 0, 0, 64, 6, 0,
                     bytes(int(x) for x in src.split(".")),
                     bytes(int(x) for x in dst.split(".")))
    eth = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\x08\x00"
    return eth + ip + tcp


def _write_pcap(path, pkts):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for p in pkts:
            f.write(struct.pack("<IIII", 0, 0, len(p), len(p)))
            f.write(p)


def test_analyzer_confirms_synthetic_unlock(tmp_path):
    seed = bytes(range(0x20, 0x40))
    resp = unlock_response(seed)
    req1 = rcmp.frame(b"\x01\x07" + b"\x81\x00\x00")
    ack1 = rcmp.frame(b"\x81\x07\x00" + b"\xAA\xBB" + seed)   # seed at body offset 3
    req2 = rcmp.frame(b"\x01\x07" + b"\x81" + resp)          # response at body offset 1
    pcap = tmp_path / "unlock.pcap"
    _write_pcap(str(pcap), [
        _ipv4_tcp("192.168.128.2", "192.168.128.1", 1050, 8002, 1, req1),
        _ipv4_tcp("192.168.128.1", "192.168.128.2", 8002, 1050, 1, ack1),
        _ipv4_tcp("192.168.128.2", "192.168.128.1", 1050, 8002, 1 + len(req1), req2),
    ])
    out = subprocess.run([sys.executable, SCRIPT, str(pcap)],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "CONFIRMED" in out.stdout
    assert "SEED_OFFSET = 3" in out.stdout
