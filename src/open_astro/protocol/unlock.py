"""RCMP ``UnlockSecurity`` (opcode ``0x0107``) seed->response transform.

Clean-room re-implementation of the seed scramble that Motorola CPS runs to
authenticate a Partition ``0x81`` write session. The algorithm was recovered by
static analysis of ``NextGen10.dll`` (the ``CRcmpBundler`` / ``CRcmpProtocol``
engine), function ``FUN_1000fd89``, which ``CRcmpBundler::UnlockSecurity``
(``FUN_1000cce7``) calls between send and reply. Decompile and notes:
``docs/re/RE_0107_UNLOCKSECURITY.md`` and
``docs/re/nextgen10_rcmp_methods_decomp.txt``.

Key finding: the response is derived purely from the radio's 32-byte seed and a
hard-coded constant -- a self-synchronising LFSR scrambler, no per-radio secret,
no key input, no asymmetric crypto. The radio verifies with the same fixed
algorithm, so re-implementing the scramble lets us answer any seed and unlock
``0x81`` offline on any platform.

Pure codec: this module computes bytes only. It does NOT talk to a radio; the
live exchange (send request -> read seed -> scramble -> send response) belongs to
the transport/write-session layer.
"""
from __future__ import annotations

# NextGen10.dll FUN_1000fd89: initial LFSR state, hard-coded in .text.
_INIT_STATE = 0x51E88D21
# Feedback tap: bit 9 of the running state is XORed with each input bit.
_TAP_BIT = 9
# The scramble operates on a fixed 32-byte block.
SEED_LEN = 32
_MASK32 = 0xFFFFFFFF


def unlock_response(seed: bytes) -> bytes:
    """Return the 32-byte ``UnlockSecurity`` response for a 32-byte radio seed.

    Faithful port of ``FUN_1000fd89``. For each output byte ``i`` (0..31):

    * the base value is ``seed[i]``;
    * the keystream is driven by the bits of ``seed[31 - i]`` (the input block is
      read in reverse), bits 7 down to 1 -- **bit 0 is never processed**, so the
      low bit of every byte passes through unchanged;
    * for each processed bit ``b``: ``fb = (in_bit_b) XOR (state >> 9 & 1)``, then
      the state advances ``state = (state * 2 + fb) & 0xFFFFFFFF`` (the input bit
      is fed back into the state), and ``fb`` is XORed into bit ``b`` of the
      output byte.
    """
    if len(seed) != SEED_LEN:
        raise ValueError(f"seed must be {SEED_LEN} bytes, got {len(seed)}")
    state = _INIT_STATE
    out = bytearray(SEED_LEN)
    for i in range(SEED_LEN):
        val = seed[i]
        in_byte = seed[SEED_LEN - 1 - i]
        for b in range(7, 0, -1):  # bits 7..1; bit 0 skipped (matches FUN_1000fd89)
            fb = ((in_byte >> b) & 1) ^ ((state >> _TAP_BIT) & 1)
            state = (state * 2 + fb) & _MASK32
            val ^= fb << b
        out[i] = val & 0xFF
    return bytes(out)
