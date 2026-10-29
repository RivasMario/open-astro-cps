"""Tests for the UnlockSecurity handshake orchestration.

Exercise the send/seed/respond flow with a mock transport (no hardware) and
confirm the guard refuses live transmit while the wire frame is unconfirmed.
"""
import pytest

from open_astro.protocol import unlock_session as us
from open_astro.protocol.unlock import unlock_response, SEED_LEN


class FakeTransport:
    """Records sent frames; returns a scripted reply body carrying a seed."""

    def __init__(self, seed: bytes):
        self._reply = bytes(us.SEED_OFFSET) + seed  # seed at SEED_OFFSET
        self.sent = []
        self._recv_calls = 0

    def send(self, frame: bytes):
        self.sent.append(frame)

    def recv(self) -> bytes:
        self._recv_calls += 1
        return self._reply


def test_exchange_scrambles_seed_and_sends_response():
    seed = bytes(range(SEED_LEN))
    t = FakeTransport(seed)
    sess = us.UnlockSession(t.send, t.recv)
    resp = sess.exchange()

    assert sess.seed == seed
    assert resp == unlock_response(seed)
    # one request then one response were sent
    assert len(t.sent) == 2
    # the response record carries the scrambled bytes
    assert resp in t.sent[1]


def test_extract_seed_too_short():
    with pytest.raises(us.UnlockError):
        us.extract_seed(b"\x00" * (SEED_LEN - 1))


def test_response_record_length_contract():
    with pytest.raises(us.UnlockError):
        us.build_unlock_response_record(b"\x00" * 10)


def test_perform_refuses_until_frame_confirmed():
    assert us.WIRE_PROFILE_CONFIRMED is False
    sess = us.UnlockSession(lambda f: None, lambda: bytes(SEED_LEN))
    with pytest.raises(us.UnlockError):
        sess.perform()


def test_request_record_is_framed():
    rec = us.build_unlock_request()
    # 2-byte big-endian length prefix matches the remaining bytes
    assert int.from_bytes(rec[:2], "big") == len(rec) - 2
