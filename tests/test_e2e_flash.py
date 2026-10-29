"""End-to-end regression tests: the REAL RCMP client driving the virtual radio.

Promoted from scratch/demo_flash.py. Each test drives tools/virtual_radio.py
over loopback TCP with the production RCMP clients
(open_astro.protocol.rcmp_transport.RcmpReadClient /
open_astro.protocol.rcmp_write.RcmpWriteClient) -- no hardware -- and asserts
the simulated flash / codeplug-edit / firewall / security-gate behaviour.

Run (per the task recipe):
    PYTHONPATH=src python -m pytest -q tests/test_e2e_flash.py
"""
from __future__ import annotations

import importlib.util
import os
import re
import socket
import struct

import pytest

from open_astro.parsers.cpg_parser import CpgParser
from open_astro.protocol.rcmp_transport import RcmpReadClient
from open_astro.protocol.rcmp_write import RcmpWriteClient, RcmpWriteError
from open_astro.models.flashcode import set_feature, format_flashcode, ADP_Q667

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPG = os.path.join(REPO, "backups", "205CFR2930.cpg")

# tools/virtual_radio.py is a standalone script, not an importable package --
# load it by path exactly as the demo does.
_spec = importlib.util.spec_from_file_location(
    "virtual_radio", os.path.join(REPO, "tools", "virtual_radio.py"))
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)

PART_CODEPLUG = 0x80
PART_SECURITY = 0x81
PART_TUNING = 0x82

# ASCII FLASHcode: AAAAAA-BBBBBB-C.
_FC_RE = re.compile(rb"([0-9A-Z]{6}-[0-9A-Z]{6}-[0-9A-Z])")

ORIGINAL_FC = "000008-002410-2"
UPGRADED_FC = "000008-006410-3"  # ADP/Q667 added, Luhn check digit recomputed


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _ascii_fc(blob: bytes) -> str:
    """Extract the ASCII FLASHcode from a raw 0x1006 object, or '' if absent."""
    m = _FC_RE.search(blob)
    return m.group(1).decode() if m else ""


def _make_server(lock: bool = False) -> "vr.VirtualRadioServer":
    """Start a fresh virtual radio on an ephemeral port; caller must stop()."""
    data = CpgParser.load_file(CPG)
    srv = vr.VirtualRadioServer(data, host="127.0.0.1", port=0, verbose=False,
                                lock_security=lock)
    srv.start()
    return srv


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from a socket (responses are tiny but be precise)."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _raw_txn(sock: socket.socket, opcode: int, payload: bytes = b"") -> bytes:
    """Send one length-prefixed RCMP record and return the response body
    (opcode:2 + status:1 + ...). Frame = <len:u16 be><opcode:u16 be><payload>."""
    record = struct.pack(">H", opcode) + payload
    sock.sendall(struct.pack(">H", len(record)) + record)
    sock.settimeout(3.0)
    hdr = _recv_exactly(sock, 2)
    assert len(hdr) == 2, "no response length header"
    length = (hdr[0] << 8) | hdr[1]
    body = _recv_exactly(sock, length)
    assert len(body) == length, "truncated response body"
    return body


def _status(body: bytes) -> int:
    """Status byte of an RCMP response record (3rd byte, after the opcode)."""
    assert len(body) >= 3, f"response too short for a status byte: {body.hex()}"
    return body[2]


def _opcode(body: bytes) -> int:
    return (body[0] << 8) | body[1]


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def server():
    """An unlocked virtual radio on an ephemeral port, stopped on teardown."""
    srv = _make_server(lock=False)
    try:
        yield srv
    finally:
        srv.stop()


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
def test_read_identity(server):
    """Read radio identity (serial + FLASHcode) from partition 0x81."""
    r = RcmpReadClient.connect(host="127.0.0.1", port=server.port,
                               timeout=3.0, src_port=0)
    try:
        r.open_session()
        serial_obj = r.read_object(PART_SECURITY, 0x1004, 64)
        fc_obj = r.read_object(PART_SECURITY, 0x1006, 64)
    finally:
        r.close()

    assert b"205CFR2930" in serial_obj
    assert _ascii_fc(fc_obj) == ORIGINAL_FC


def test_flashcode_upgrade_write_readback(server):
    """Compute the ADP (Q667) upgrade offline, WRITE it to 0x81:0x1006 with the
    real write client, then READ BACK and prove the new FLASHcode landed."""
    # --- read the current 0x1006 object -----------------------------------
    r = RcmpReadClient.connect(host="127.0.0.1", port=server.port,
                               timeout=3.0, src_port=0)
    try:
        r.open_session()
        original = r.read_object(PART_SECURITY, 0x1006, 64)
    finally:
        r.close()
    old_fc = _ascii_fc(original)
    assert old_fc == ORIGINAL_FC

    # --- compute the upgrade (flip ADP bit, recompute Luhn check digit) ----
    payload12 = old_fc.replace("-", "")[:12]
    new12 = set_feature(payload12, *ADP_Q667)
    new_fc = format_flashcode(new12)
    assert new_fc == UPGRADED_FC

    # --- build the new object: original 8-byte header + ASCII FC + trailing NUL
    new_obj = original[:8] + new_fc.encode("ascii") + b"\x00"

    # --- WRITE it (allow_write=True required) ------------------------------
    w = RcmpWriteClient.connect(host="127.0.0.1", port=server.port,
                                timeout=3.0, src_port=0, allow_write=True)
    try:
        w.open_session()
        ack = w.write_object(PART_SECURITY, 0x1006, new_obj)
        assert ack.get("opcode") == 0x8101
        w.close_session()
    finally:
        w.close()

    # --- READ BACK with a fresh read client --------------------------------
    r = RcmpReadClient.connect(host="127.0.0.1", port=server.port,
                               timeout=3.0, src_port=0)
    try:
        r.open_session()
        back = r.read_object(PART_SECURITY, 0x1006, 64)
    finally:
        r.close()
    assert _ascii_fc(back) == UPGRADED_FC


def test_codeplug_object_edit(server):
    """Write a known blob to a 0x80 codeplug object and read it back."""
    test_obj, test_inst = 0x0FA8, 0
    blob = b"OPENASTRO-DEMO-\x01\x02\x03\x04"

    w = RcmpWriteClient.connect(host="127.0.0.1", port=server.port,
                                timeout=3.0, src_port=0, allow_write=True)
    try:
        w.open_session()
        w.write_object(PART_CODEPLUG, test_obj, blob, inst=test_inst)
        w.close_session()
    finally:
        w.close()

    r = RcmpReadClient.connect(host="127.0.0.1", port=server.port,
                               timeout=3.0, src_port=0)
    try:
        r.open_session()
        after = r.read_object(PART_CODEPLUG, test_obj, 64, inst=test_inst)
    finally:
        r.close()

    assert after.startswith(blob)


def test_0x82_firewall_client_and_server(server):
    """Partition 0x82 (tuning soft-pots) must be refused both client-side (the
    write client's guard raises) and server-side (a raw frame is rejected)."""
    # --- client-side guard: write_object(0x82, ...) must raise -------------
    w = RcmpWriteClient.connect(host="127.0.0.1", port=server.port,
                                timeout=3.0, src_port=0, allow_write=True)
    try:
        w.open_session()
        with pytest.raises(RcmpWriteError):
            w.write_object(PART_TUNING, 0x0001, b"\xde\xad\xbe\xef")
    finally:
        w.close()

    # --- server-side refusal: raw 0x0101 frame to 0x82 -> non-zero status --
    payload = bytes([0x82, 0x00, 0x01, 0x00, 0x00, 0x00, 0x04,
                     0x00, 0x00, 0x00, 0x04]) + b"\xde\xad\x00\x00"
    s = socket.create_connection(("127.0.0.1", server.port), timeout=3.0)
    try:
        body = _raw_txn(s, 0x0101, payload)
    finally:
        s.close()
    assert _opcode(body) == 0x8101
    assert _status(body) != 0  # refused

    # --- and the firewall never let anything into partition 0x82 -----------
    assert not any(part == PART_TUNING
                   for (part, _obj, _inst) in server.cpg_data.objects)


def test_lock_security_unlock_gate():
    """With lock_security=True a 0x81 write is refused until a 0x0107
    UnlockSecurity; afterwards it is accepted, while 0x82 stays refused."""
    srv = _make_server(lock=True)
    write81 = bytes([0x81, 0x10, 0x06, 0x00, 0x00, 0x00, 0x04,
                     0x00, 0x00, 0x00, 0x04]) + b"ABCD" + b"\x00\x00"
    write82 = bytes([0x82, 0x00, 0x01, 0x00, 0x00, 0x00, 0x04,
                     0x00, 0x00, 0x00, 0x04]) + b"\x00\x00\x00\x00"
    s = socket.create_connection(("127.0.0.1", srv.port), timeout=3.0)
    try:
        # 1. 0x81 write BEFORE unlock -> refused (status != 0)
        before = _raw_txn(s, 0x0101, write81)
        assert _opcode(before) == 0x8101
        assert _status(before) != 0

        # 2. UnlockSecurity -> 0x8107 status 0
        unlock = _raw_txn(s, 0x0107, b"")
        assert _opcode(unlock) == 0x8107
        assert _status(unlock) == 0

        # 3. same 0x81 write AFTER unlock -> accepted (status 0)
        after = _raw_txn(s, 0x0101, write81)
        assert _opcode(after) == 0x8101
        assert _status(after) == 0

        # 4. 0x82 still refused even after unlock (independent firewall)
        tuning = _raw_txn(s, 0x0101, write82)
        assert _opcode(tuning) == 0x8101
        assert _status(tuning) != 0
    finally:
        s.close()
        srv.stop()
