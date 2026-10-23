"""Offline tests for the gated RCMP write client. A fake conn replays acks; no
radio. Verifies the safety gate, the partition guard, exact bytes on the wire,
and ack validation."""
import pytest

from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_write import (
    RcmpWriteClient, RcmpWriteError, RcmpWriteDisabled, PART_TUNING,
)


class FakeConn:
    def __init__(self, script: bytes = b"", chunk: int = 5):
        self._script = bytearray(script)
        self._chunk = chunk
        self.sent = bytearray()
        self.closed = False

    def sendall(self, data): self.sent.extend(data)

    def recv(self, n):
        take = min(self._chunk, n, len(self._script))
        out = bytes(self._script[:take]); del self._script[:take]
        return out

    def close(self): self.closed = True


def _ack(opcode, body=b""):
    return rcmp.frame(opcode.to_bytes(2, "big") + body)


def test_gate_blocks_without_allow_write():
    with pytest.raises(RcmpWriteDisabled):
        RcmpWriteClient(FakeConn())
    with pytest.raises(RcmpWriteDisabled):
        RcmpWriteClient(FakeConn(), allow_write=False)


def test_allow_write_true_constructs():
    c = RcmpWriteClient(FakeConn(), allow_write=True)
    assert c is not None


def test_write_object_refuses_tuning_partition():
    c = RcmpWriteClient(FakeConn(), allow_write=True)
    with pytest.raises(RcmpWriteError):
        c.write_object(PART_TUNING, 0x0001, b"\x00\x00")


def test_write_object_sends_encoded_record_and_checks_ack():
    payload = b"\x01\x02\x03\x04"
    conn = FakeConn(_ack(rcmp.OP_WRITE | rcmp.RESP_FLAG, b"\x00\x80\x0f\xff"))
    c = RcmpWriteClient(conn, allow_write=True)
    c.write_object(0x80, 0x0FFF, payload, inst=1)
    assert bytes(conn.sent) == rcmp.build_write(0x80, 0x0FFF, payload, inst=1)


def test_write_object_raises_on_wrong_ack():
    conn = FakeConn(_ack(rcmp.OP_READ | rcmp.RESP_FLAG))  # not a write ack
    c = RcmpWriteClient(conn, allow_write=True)
    with pytest.raises(RcmpWriteError):
        c.write_object(0x80, 0x0FFF, b"\x00\x00")


def test_open_and_close_session_bytes():
    conn = FakeConn(_ack(rcmp.OP_SESSION | rcmp.RESP_FLAG) +
                    _ack(rcmp.OP_SESSION | rcmp.RESP_FLAG))
    c = RcmpWriteClient(conn, allow_write=True)
    c.open_session()
    c.close_session()
    assert bytes(conn.sent) == rcmp.frame(b"\x01\x06\x00") + rcmp.frame(b"\x01\x06\x01")


def test_send_prebuilt_guards_tuning():
    c = RcmpWriteClient(FakeConn(), allow_write=True)
    # a verbatim write record targeting partition 0x82 must be refused
    bad = rcmp.build_write(PART_TUNING, 0x0001, b"\x00\x00")
    with pytest.raises(RcmpWriteError):
        c.send_prebuilt(bad)
