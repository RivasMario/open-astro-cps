"""RCMP ``UnlockSecurity`` handshake orchestration (Partition 0x81 unlock).

This wires the recovered seed->response scramble (:mod:`unlock`) into the
send/seed/respond exchange that ``CRcmpBundler::UnlockSecurity`` (NextGen10.dll
``FUN_1000cce7``) performs: build a request, send it, read a 32-byte seed from
the reply, scramble it, send the scrambled response, and read the acknowledgement.

What is CONFIRMED (static RE of NextGen10.dll):
  * the exchange shape -- one request, a 32-byte seed in the reply, one response
    record, one ack (``FUN_1000cce7`` build->send->``FUN_1000fd89``->reply);
  * the seed->response transform (:func:`unlock.unlock_response`, tested).

What is NOT yet byte-confirmed (needs one live CPS "unlock/program" capture or a
deeper COM-interface trace):
  * the wire opcode of the request -- ROADMAP calls it ``0x0107``; the decompile
    sets a message tag ``0x2011``. Which one rides the RCMP record header is open.
  * the exact request body, and the seed's offset within the reply body.

Because those bytes are unconfirmed, :data:`WIRE_PROFILE_CONFIRMED` is ``False``
and :meth:`UnlockSession.perform` refuses to transmit. The orchestration and the
scramble are fully exercised by the mock-transport test; finishing is a matter of
dropping in the confirmed constants and flipping the flag. Do NOT transmit a
guessed frame to a radio: a wrong UnlockSecurity frame can wedge the link.
"""
from __future__ import annotations

from typing import Callable

from . import rcmp
from .unlock import unlock_response, SEED_LEN

# RCMP opcode candidates for the request (see module docstring -- UNCONFIRMED).
OP_UNLOCK = 0x0107
# Message tag written by FUN_1000cce7 (``*(u16*)(ebp-0x30) = 0x2011``).
MSG_TAG_UNLOCK = 0x2011
# Offset of the 32-byte seed inside the reply record body (UNCONFIRMED).
SEED_OFFSET = 0

# Flip to True only once the request/seed framing is confirmed against a live
# capture and a recorded seed/response pair passes as a test vector.
WIRE_PROFILE_CONFIRMED = False


class UnlockError(RuntimeError):
    pass


def build_unlock_request(part: int = 0x81, inst: int = 0) -> bytes:
    """Provisional UnlockSecurity request record (framing per RCMP; body UNCONFIRMED).

    Modelled as opcode ``0x0107`` carrying the ``0x2011`` message tag for the
    target partition. Exact body layout must be confirmed before transmit.
    """
    payload = (bytes([OP_UNLOCK >> 8, OP_UNLOCK & 0xFF, part])
               + bytes([MSG_TAG_UNLOCK >> 8, MSG_TAG_UNLOCK & 0xFF])
               + bytes([inst & 0xFF]))
    return rcmp.frame(payload)


def extract_seed(reply_body: bytes, offset: int = SEED_OFFSET) -> bytes:
    """Pull the 32-byte seed out of a reply record body (offset UNCONFIRMED)."""
    seed = reply_body[offset:offset + SEED_LEN]
    if len(seed) != SEED_LEN:
        raise UnlockError(
            f"reply too short for a {SEED_LEN}-byte seed at offset {offset} "
            f"(got {len(seed)} of {len(reply_body)} body bytes)")
    return seed


def build_unlock_response_record(response: bytes, part: int = 0x81,
                                 inst: int = 0) -> bytes:
    """Provisional record carrying the scrambled 32-byte response (UNCONFIRMED)."""
    if len(response) != SEED_LEN:
        raise UnlockError(f"response must be {SEED_LEN} bytes")
    payload = bytes([OP_UNLOCK >> 8, OP_UNLOCK & 0xFF, part]) + response
    return rcmp.frame(payload)


class UnlockSession:
    """Drives the UnlockSecurity handshake over an abstract record transport.

    ``send`` sends one framed record; ``recv`` returns one reply record body
    (header stripped by the caller's transport). The transport is injected so
    this stays hardware-free and unit-testable.
    """

    def __init__(self, send: Callable[[bytes], None],
                 recv: Callable[[], bytes], part: int = 0x81, inst: int = 0):
        self._send = send
        self._recv = recv
        self.part = part
        self.inst = inst
        self.seed: bytes | None = None
        self.response: bytes | None = None

    def exchange(self) -> bytes:
        """Run the handshake, return the scrambled response that was sent.

        Pure orchestration -- usable with a mock transport. It does not itself
        gate on :data:`WIRE_PROFILE_CONFIRMED`; :meth:`perform` is the guarded
        entry point for live use.
        """
        self._send(build_unlock_request(self.part, self.inst))
        reply = self._recv()
        self.seed = extract_seed(reply)
        self.response = unlock_response(self.seed)
        self._send(build_unlock_response_record(self.response, self.part, self.inst))
        return self.response

    def perform(self) -> bytes:
        """Guarded live entry point. Refuses until the wire frame is confirmed."""
        if not WIRE_PROFILE_CONFIRMED:
            raise UnlockError(
                "UnlockSecurity wire frame is not confirmed -- refusing to "
                "transmit. Confirm the request opcode/body and seed offset "
                "against a live capture, record a seed/response vector, then "
                "set WIRE_PROFILE_CONFIRMED = True.")
        return self.exchange()
