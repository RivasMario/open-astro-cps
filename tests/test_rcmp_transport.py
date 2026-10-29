"""Offline tests for the read-only RCMP transport, using a fake socket that
replays framed records. No radio required; verifies the record IO, session
handshake, read flow, and that no write capability is exposed."""
import pytest

from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_transport import RcmpReadClient, RcmpError


class FakeConn:
    """Socket-like stub. `script` is the bytes the 'radio' sends back; recv
    hands them out in chunks. Everything written is recorded in `sent`."""
    def __init__(self, script: bytes, chunk: int = 7):
        self._script = bytearray(script)
        self._chunk = chunk
        self.sent = bytearray()
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, n: int) -> bytes:
        take = min(self._chunk, n, len(self._script))
        out = bytes(self._script[:take])
        del self._script[:take]
        return out

    def close(self) -> None:
        self.closed = True


def _ack(opcode: int, body: bytes = b"") -> bytes:
    return rcmp.frame(opcode.to_bytes(2, "big") + body)


def test_recv_record_reassembles_across_chunks():
    # Record split across small recv() chunks must still parse whole.
    rec = rcmp.frame(b"\x81\x00hello-world-data")
    c = RcmpReadClient(FakeConn(rec, chunk=3))
    assert c._recv_record() == b"\x81\x00hello-world-data"


def test_open_session_sends_and_validates_ack():
    conn = FakeConn(_ack(rcmp.OP_SESSION | rcmp.RESP_FLAG, b"\x00"))
    c = RcmpReadClient(conn)
    ack = c.open_session()
    assert bytes(conn.sent) == rcmp.build_session_open()
    assert ack["op"] == "SESSION_ACK"


def test_open_session_rejects_wrong_ack():
    conn = FakeConn(_ack(rcmp.OP_READ | rcmp.RESP_FLAG))
    with pytest.raises(RcmpError):
        RcmpReadClient(conn).open_session()


def test_read_object_sends_request_and_returns_body():
    # Read-ack = 12-byte echoed header + object data + 2-byte CRC trailer
    # (verified live on 407CHT0214 and 205CFR2930). Both are stripped.
    header = bytes.fromhex("008000470000001000000010")
    body = bytes(range(16))
    crc = b"\xab\xa7"
    conn = FakeConn(_ack(rcmp.OP_READ | rcmp.RESP_FLAG, header + body + crc))
    c = RcmpReadClient(conn)
    data = c.read_object(rcmp.PART_CODEPLUG, 0x0047, 0x0010)
    # Request on the wire is the verified read request.
    assert bytes(conn.sent) == rcmp.build_read(rcmp.PART_CODEPLUG, 0x0047, 0x0010)
    assert data == body  # header + CRC stripped, raw object bytes returned


def test_read_object_raises_on_non_ack():
    conn = FakeConn(_ack(rcmp.OP_SESSION | rcmp.RESP_FLAG))
    with pytest.raises(RcmpError):
        RcmpReadClient(conn).read_object(rcmp.PART_CODEPLUG, 0x0047, 0x0010)


def test_connection_closed_midrecord_raises():
    c = RcmpReadClient(FakeConn(b"\x00"))  # 1 byte then EOF
    with pytest.raises(RcmpError):
        c._recv_record()


def test_client_is_read_only():
    # The transport must expose no write/program method.
    assert not hasattr(RcmpReadClient, "write_object")
    assert not hasattr(RcmpReadClient, "write")
    methods = {m for m in dir(RcmpReadClient) if not m.startswith("_")}
    assert "read_object" in methods and "open_session" in methods
    assert not any("write" in m or "program" in m or "erase" in m for m in methods)


def test_context_manager_closes():
    conn = FakeConn(b"")
    with RcmpReadClient(conn):
        pass
    assert conn.closed
