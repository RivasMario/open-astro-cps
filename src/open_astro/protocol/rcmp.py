"""RCMP codec for Motorola ASTRO 25 radios -- VERIFIED against live captures.

Unlike the placeholder encoding in flasher.py, every byte layout here is
confirmed against real Motorola CPS <-> XTS 2500 sessions captured on
2026-10-23 (see docs/RCMP_WIRE_PROTOCOL.md). This module is pure codec: it
builds request records and parses response/record streams. It does NOT talk to
a radio (no PPP bring-up, no socket) -- a transport is a separate, later layer.
Keeping the codec transport-free lets it be verified byte-for-byte against the
captures with no hardware and no risk.

Wire model
----------
RCMP rides a TCP stream (host:8001 -> radio:8002, over RAS PPP + VJ). The byte
stream is a sequence of records:

    <length: u16 big-endian> <payload[length]>

The payload starts with a 2-byte opcode. A response echoes the request opcode
with the top bit of the first byte set (0x01xx request -> 0x81xx response).

Read request payload (VERIFIED, byte-exact vs capture):

    01 00 <part:u8> <obj:u16 be> <inst:u16 be> <len:u16 be> 00 00

`part` selects the memory partition (0x80 codeplug, 0x82 tuning). `obj` is the
object id; these equal the .cpg OLE stream tags the offline reader uses. `len`
is how many bytes to read. The trailing 00 00 is a reserved/second-instance
field, always zero in the captures.

Write request payload: op 01 01 with the same addressing, followed by the block
payload and a CRC-16 trailer. The exact write sub-framing is only PARTIALLY
confirmed (see docs TODO), so build_write() is marked experimental and must not
be used to drive a real radio yet.
"""
from __future__ import annotations

import struct
from typing import Dict, Iterator, List, Optional

# Opcodes (first two payload bytes).
OP_READ = 0x0100
OP_WRITE = 0x0101
OP_PREPARE = 0x0103   # program / erase-prepare, precedes a write burst
OP_SESSION = 0x0106   # session open
RESP_FLAG = 0x8000    # response = request | 0x8000 on the opcode's high byte

# Partition selectors (high-level memory map; see docs/RCMP_WIRE_PROTOCOL.md).
PART_CODEPLUG = 0x80
PART_TUNING = 0x82

_OP_NAMES = {
    OP_READ: "READ", OP_WRITE: "WRITE", OP_PREPARE: "PREPARE",
    OP_SESSION: "SESSION",
    OP_READ | RESP_FLAG: "READ_ACK", OP_WRITE | RESP_FLAG: "WRITE_ACK",
    OP_PREPARE | RESP_FLAG: "PREPARE_ACK", OP_SESSION | RESP_FLAG: "SESSION_ACK",
}


def op_name(opcode: int) -> str:
    return _OP_NAMES.get(opcode, f"0x{opcode:04x}")


# -- framing --------------------------------------------------------------
def frame(payload: bytes) -> bytes:
    """Wrap a record payload with its 2-byte big-endian length prefix."""
    return struct.pack(">H", len(payload)) + payload


def iter_records(stream: bytes) -> Iterator[bytes]:
    """Yield record payloads from a reassembled RCMP byte stream. Stops at a
    zero length or a truncated trailing record (returns what parsed cleanly)."""
    i = 0
    n = len(stream)
    while i + 2 <= n:
        length = struct.unpack_from(">H", stream, i)[0]
        if length == 0 or i + 2 + length > n:
            break
        yield stream[i + 2:i + 2 + length]
        i += 2 + length


# -- requests -------------------------------------------------------------
def build_read(part: int, obj: int, length: int, inst: int = 0) -> bytes:
    """Build a framed READ request record (VERIFIED layout)."""
    payload = struct.pack(">BBB", 0x01, 0x00, part) + \
        struct.pack(">HHH", obj, inst, length) + b"\x00\x00"
    return frame(payload)


def build_session_open() -> bytes:
    """Build the session-open record seen first in every captured session."""
    return frame(bytes([0x01, 0x06, 0x00]))


def build_write(part: int, obj: int, data: bytes, inst: int = 0) -> bytes:
    """EXPERIMENTAL: build a WRITE record. The write sub-framing and CRC are
    only partially confirmed (docs/RCMP_WIRE_PROTOCOL.md). Provided for offline
    analysis and tests ONLY; do not transmit to a radio until verified."""
    body = struct.pack(">BBB", 0x01, 0x01, part) + \
        struct.pack(">HHH", obj, inst, len(data)) + \
        struct.pack(">H", inst) + data
    return frame(body + struct.pack(">H", _crc16(body)))


# -- parsing --------------------------------------------------------------
def parse_record(payload: bytes) -> Dict[str, object]:
    """Decode one record payload into a dict. Reads/writes/acks expose their
    partition/object/instance/length header; other records are returned raw."""
    if len(payload) < 2:
        return {"opcode": None, "raw": payload.hex()}
    opcode = struct.unpack_from(">H", payload, 0)[0]
    info: Dict[str, object] = {"opcode": opcode, "op": op_name(opcode)}
    if opcode in (OP_READ, OP_WRITE) and len(payload) >= 9:
        info["partition"] = payload[2]
        info["object"] = struct.unpack_from(">H", payload, 3)[0]
        info["instance"] = struct.unpack_from(">H", payload, 5)[0]
        info["length"] = struct.unpack_from(">H", payload, 7)[0]
    info["body_hex"] = payload[2:].hex()
    return info


def parse_stream(stream: bytes) -> List[Dict[str, object]]:
    return [parse_record(p) for p in iter_records(stream)]


# CRC-16-CCITT (same polynomial the offline .cpg reader validates with).
def _crc16(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc
