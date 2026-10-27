"""Unit tests for the Virtual ASTRO 25 Radio RCMP Server (tools/virtual_radio.py).

Tests live RCMP reads over TCP loopback using both:
  1. `src/open_astro/protocol/rcmp_transport.py` (RcmpReadClient / rcmp.py)
  2. Direct length-prefixed RCMP TCP framing (Opcodes 0x000C, 0x000D, 0x0001, 0x0002)

Verifies:
  - Reading Partition 0x81 Object 0x1004 (Serial Number)
  - Reading Partition 0x81 Object 0x1006 (FLASHcode)
  - Reading Partition 0x80 Object 0x0FFF (Channel Names)
  - WriteObject to Partition 0x80 (Allowed)
  - WriteObject to Partition 0x82 (Tuning Firewall - Strictly Refused!)
  - Overriding Serial and FLASHcode via CLI / loader
"""
from __future__ import annotations

import os
import socket
import struct
import sys
import threading
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
for p in (SRC_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from open_astro.parsers.cpg_parser import CpgParser
from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_transport import RcmpReadClient
from virtual_radio import (
    DEFAULT_CPG,
    PART_CODEPLUG,
    PART_SECURITY,
    PART_TUNING,
    VirtualRadioServer,
    load_codeplug,
    print_banner,
)


@pytest.fixture
def running_server():
    """Fixture that starts a VirtualRadioServer on an ephemeral port."""
    cpg_data = load_codeplug(DEFAULT_CPG)
    server = VirtualRadioServer(cpg_data, host="127.0.0.1", port=0, verbose=False)
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _recv_rcmp_frame(sock: socket.socket) -> Tuple[int, bytes]:
    """Helper to receive one length-prefixed RCMP frame from a socket."""
    header = sock.recv(2)
    assert len(header) == 2, "Failed to read length header"
    length = struct.unpack(">H", header)[0]
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        assert chunk, "Connection closed prematurely"
        payload += chunk
    opcode = struct.unpack(">H", payload[:2])[0]
    body = payload[2:]
    return opcode, body


def _send_rcmp_frame(sock: socket.socket, opcode: int, body: bytes = b"") -> None:
    """Helper to send one length-prefixed RCMP frame."""
    payload = struct.pack(">H", opcode) + body
    frame = struct.pack(">H", len(payload)) + payload
    sock.sendall(frame)


def test_server_banner_and_metadata(running_server):
    """Test server initialization and metadata extraction."""
    assert running_server.cpg_data.model == "H46UCF9PW6AN"
    assert running_server.cpg_data.serial == "205CFR2930"
    assert running_server.cpg_data.flashcode == "000008-002410-2"
    assert len(running_server.cpg_data.objects) > 100
    # Banner should print without error
    print_banner(running_server)


def test_rcmp_live_read_with_rcmp_client(running_server):
    """Perform a live read using open_astro's official RcmpReadClient over TCP.

    Verifies reading 0x1004 (Serial) and 0x1006 (FLASHcode).
    """
    client = RcmpReadClient.connect(
        host=running_server.host,
        port=running_server.port,
        src_port=0,
    )
    try:
        # 1. Session Open (Opcode 0x0106 -> 0x8106)
        ack = client.open_session()
        assert ack.get("op") == "SESSION_ACK"

        # 2. Read Object 0x1004 (Serial Number) in partition 0x81
        p1004 = client.read_object(PART_SECURITY, 0x1004, 0x0044, inst=0)
        assert b"205CFR2930" in p1004
        assert b"H46UCF9PW6AN" in p1004

        # 3. Read Object 0x1006 (FLASHcode) in partition 0x81
        p1006 = client.read_object(PART_SECURITY, 0x1006, 0x0018, inst=0)
        assert b"000008-002410-2" in p1006

        # 4. Read Object 0x0FFF (Channel Names) in partition 0x80
        p0fff = client.read_object(PART_CODEPLUG, 0x0FFF, 0x0120, inst=0)
        assert len(p0fff) > 0
    finally:
        client.close()


def test_rcmp_opcodes_000c_000d_0001_raw_tcp(running_server):
    """Test raw TCP length-prefixed RCMP framing with opcodes 0x000C, 0x000D, 0x0001."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((running_server.host, running_server.port))
    try:
        # Step 1: Unlock / Start Session (Opcode 0x000C)
        _send_rcmp_frame(sock, 0x000C, b"")
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x800C
        assert resp_body == b"\x00"  # Status 0 = success

        # Step 2: ReadObject (Opcode 0x0001) for 0x1004 (Serial)
        # Payload: partition (u8), obj (u16), inst (u16), offset (u16), length (u16)
        read_1004_req = struct.pack(">BHHHH", PART_SECURITY, 0x1004, 0, 0, 68)
        _send_rcmp_frame(sock, 0x0001, read_1004_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8001
        assert b"205CFR2930" in resp_body
        assert b"H46UCF9PW6AN" in resp_body

        # Step 3: ReadObject (Opcode 0x0001) for 0x1006 (FLASHcode)
        read_1006_req = struct.pack(">BHHHH", PART_SECURITY, 0x1006, 0, 0, 24)
        _send_rcmp_frame(sock, 0x0001, read_1006_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8001
        assert b"000008-002410-2" in resp_body

        # Step 4: Lock / End Session (Opcode 0x000D)
        _send_rcmp_frame(sock, 0x000D, b"")
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x800D
        assert resp_body == b"\x00"  # Status 0 = success
    finally:
        sock.close()


def test_rcmp_write_and_partition_82_firewall(running_server):
    """Test Opcode 0x0002 (WriteObject) and verify that Partition 0x82 is refused."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((running_server.host, running_server.port))
    try:
        # Write to Partition 0x80 (Allowed)
        test_data = b"VIRTUAL_RADIO_TEST_CHANNELS"
        write_80_req = struct.pack(">BHHH", PART_CODEPLUG, 0x0FFF, 0, len(test_data)) + test_data
        _send_rcmp_frame(sock, 0x0002, write_80_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x00"  # Success

        # Read back written data
        read_80_req = struct.pack(">BHHHH", PART_CODEPLUG, 0x0FFF, 0, 0, len(test_data))
        _send_rcmp_frame(sock, 0x0001, read_80_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8001
        assert resp_body == test_data

        # Write to Partition 0x82 (Tuning Firewall - MUST BE REFUSED!)
        write_82_req = struct.pack(">BHHH", PART_TUNING, 0x0001, 0, 4) + b"\xDE\xAD\xBE\xEF"
        _send_rcmp_frame(sock, 0x0002, write_82_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x01"  # Error status 1 (Refused)
    finally:
        sock.close()


def test_serial_and_flashcode_overrides():
    """Test overriding serial and FLASHcode via CLI args or load_codeplug."""
    custom_serial = "407CHT0214"
    custom_fc = "000008-006410-3"
    cpg_data = load_codeplug(
        DEFAULT_CPG,
        serial_override=custom_serial,
        flashcode_override=custom_fc,
    )
    assert cpg_data.serial == custom_serial
    assert cpg_data.flashcode == custom_fc

    server = VirtualRadioServer(cpg_data, host="127.0.0.1", port=0)
    server.start()
    try:
        client = RcmpReadClient.connect(host=server.host, port=server.port, src_port=0)
        try:
            client.open_session()
            p1004 = client.read_object(PART_SECURITY, 0x1004, 0x0044)
            assert custom_serial.encode("ascii") in p1004

            p1006 = client.read_object(PART_SECURITY, 0x1006, 0x0018)
            assert custom_fc.encode("ascii") in p1006
        finally:
            client.close()
    finally:
        server.stop()


def test_lock_security_gates_partition_81_writes():
    """With lock_security=True, 0x81 writes are refused until a 0x0107 UnlockSecurity.

    Also verifies that 0x82 stays refused regardless of the unlock (independent
    firewall), and that the 0x0107 request is acknowledged with 0x8107 status 0.
    """
    cpg_data = load_codeplug(DEFAULT_CPG)
    server = VirtualRadioServer(cpg_data, host="127.0.0.1", port=0,
                                verbose=False, lock_security=True)
    server.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server.host, server.port))
    try:
        # 1. Write to Partition 0x81 BEFORE unlock -> refused (status 1)
        sec_data = b"LOCKED_SERIAL\x00"
        write_81_req = struct.pack(">BHHH", PART_SECURITY, 0x1004, 0, len(sec_data)) + sec_data
        _send_rcmp_frame(sock, 0x0002, write_81_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x01"  # Refused: security locked

        # 2. 0x82 is always refused, even while locked
        write_82_req = struct.pack(">BHHH", PART_TUNING, 0x0001, 0, 4) + b"\xDE\xAD\xBE\xEF"
        _send_rcmp_frame(sock, 0x0002, write_82_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x01"

        # 3. Send UnlockSecurity (0x0107) -> acknowledged with 0x8107 status 0
        _send_rcmp_frame(sock, 0x0107, b"")
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8107
        assert resp_body == b"\x00"

        # 4. Write to Partition 0x81 AFTER unlock -> accepted (status 0)
        _send_rcmp_frame(sock, 0x0002, write_81_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x00"

        # Confirm the write actually landed
        read_81_req = struct.pack(">BHHHH", PART_SECURITY, 0x1004, 0, 0, len(sec_data))
        _send_rcmp_frame(sock, 0x0001, read_81_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8001
        assert resp_body == sec_data

        # 5. 0x82 STILL refused after unlock (firewall independent of lock_security)
        _send_rcmp_frame(sock, 0x0002, write_82_req)
        resp_op, resp_body = _recv_rcmp_frame(sock)
        assert resp_op == 0x8002
        assert resp_body == b"\x01"
    finally:
        sock.close()
        server.stop()


def test_load_structural_json():
    """Test loading codeplug from structural JSON file."""
    json_path = os.path.join(REPO_ROOT, "backups", "205CFR2930_structural.json")
    if not os.path.exists(json_path):
        pytest.skip(f"{json_path} does not exist")

    cpg_data = load_codeplug(json_path)
    assert cpg_data.model == "H46UCF9PW6AN"
    assert cpg_data.serial == "205CFR2930"

    server = VirtualRadioServer(cpg_data, host="127.0.0.1", port=0)
    server.start()
    try:
        client = RcmpReadClient.connect(host=server.host, port=server.port, src_port=0)
        try:
            client.open_session()
            p1004 = client.read_object(PART_SECURITY, 0x1004, 0x0044)
            assert b"205CFR2930" in p1004
        finally:
            client.close()
    finally:
        server.stop()
