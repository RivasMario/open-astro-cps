"""Tests for the RCMP UnlockSecurity (0x0107) seed->response transform.

The golden vectors below are regression anchors captured from this
implementation (the clean-room port of NextGen10.dll FUN_1000fd89). The
structural invariants, however, are derived independently from the decompiled
algorithm and would catch a wrong port. Final acceptance is a live seed/response
pair from the radio, recorded once the exchange is wired into the write session.
"""
import pytest

from open_astro.protocol.unlock import unlock_response, SEED_LEN


# --- golden vectors (regression anchors) -------------------------------------
GOLDEN = {
    bytes(32): bytes.fromhex(
        "48288490520a20a4144248288490520a20a4144248288490520a20a414424828"),
    bytes(range(32)): bytes.fromhex(
        "56357851b4291addc4a7cae702dfe423bacba4a968b1ca45d427d8e720d9c645"),
    bytes([0xff]) * 32: bytes.fromhex(
        "493779916df321dbe543b7c9876f930ddf251bbd493779916df321dbe543b7c9"),
}


@pytest.mark.parametrize("seed,expected", list(GOLDEN.items()))
def test_golden_vectors(seed, expected):
    assert unlock_response(seed) == expected


def test_length_contract():
    assert len(unlock_response(bytes(32))) == SEED_LEN
    with pytest.raises(ValueError):
        unlock_response(bytes(31))
    with pytest.raises(ValueError):
        unlock_response(bytes(33))


def test_bit0_passthrough():
    # FUN_1000fd89 processes bits 7..1 only; bit 0 of every byte is unchanged.
    for seed in (bytes(range(32)), bytes([0xa5]) * 32, bytes([0xff]) * 32):
        out = unlock_response(seed)
        assert all((out[i] & 1) == (seed[i] & 1) for i in range(32))


def test_deterministic():
    seed = bytes(range(32))
    assert unlock_response(seed) == unlock_response(seed)


def test_sensitive_to_input():
    base = bytes(32)
    flipped = bytes([0x01]) + bytes(31)  # flip one bit of the reversed-read tail
    assert unlock_response(base) != unlock_response(flipped)
