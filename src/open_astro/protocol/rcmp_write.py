"""RCMP WRITE client for Motorola ASTRO 25 radios.

SAFETY / SCOPE
--------------
Writing a radio is irreversible if done wrong. This module is therefore:
  * GATED: the client refuses to construct unless allow_write=True is passed
    explicitly, so no code path writes a radio by accident.
  * Partition-guarded: it refuses to address partition 0x82 (tuning / soft-pot
    calibration), which cannot be restored in software if corrupted.
  * Ack-checked: every record sent is matched against the radio's response
    opcode (request | 0x8000); a missing or wrong ack raises before continuing.
  * Separate from RcmpReadClient, which stays provably read-only.

It does NOT decide to write. The caller must have a verified backup and should
read back and diff after writing. The verified write-record encoder and the
captured session flow live in rcmp.py / docs/RCMP_WIRE_PROTOCOL.md.

Write session flow (from the capture):
    0106 open -> ... reads ... -> 0102 -> 0103 prepare xN -> 0101 writes xN
    -> 0106 01 close/commit
"""
from __future__ import annotations

import socket
import struct
from typing import List, Optional

from . import rcmp

PART_TUNING = 0x82  # forbidden target
RADIO_PPP_HOST = "192.168.128.1"
RCMP_PORT = 8002
HOST_SRC_PORT = 8001
LOCAL_PPP_IP = "192.168.128.2"


class RcmpWriteError(Exception):
    pass


class RcmpWriteDisabled(RcmpWriteError):
    """Raised when a write client is created without explicit allow_write."""


class RcmpWriteClient:
    """Gated RCMP write client over a socket-like conn (sendall/recv/close)."""

    def __init__(self, conn, allow_write: bool = False, timeout: float = 10.0):
        if allow_write is not True:
            raise RcmpWriteDisabled(
                "RcmpWriteClient requires allow_write=True. Writing a radio is "
                "irreversible; enable it only with a verified backup and a "
                "read-back plan.")
        self._conn = conn
        self._buf = bytearray()
        self._timeout = timeout

    @classmethod
    def connect(cls, host: str = RADIO_PPP_HOST, port: int = RCMP_PORT,
                timeout: float = 15.0, src_port: int = HOST_SRC_PORT,
                src_ip: str = LOCAL_PPP_IP, *, allow_write: bool = False):
        """Write over the OS TCP stack via an already-up PPP link (RAS dial-up
        or pppd). The OS stack handles windowing/retransmit/pacing, which our
        minimal userspace TCP does not -- required for the sustained write
        burst. The PPP link must be up (192.168.128.1 reachable)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        try:
            if src_port:
                try:
                    sock.bind((src_ip, src_port))
                except OSError:
                    sock.bind(("", src_port))
            sock.settimeout(timeout)
            sock.connect((host, port))
        except OSError as e:
            sock.close()
            raise RcmpWriteError(
                f"cannot reach radio at {host}:{port} from :{src_port} ({e}); "
                f"is the PPP (RAS) link up?") from e
        return cls(sock, allow_write=allow_write, timeout=timeout)

    # -- low-level framed IO (same framing as the read client) -----------
    def _fill(self, need: int) -> None:
        while len(self._buf) < need:
            chunk = self._conn.recv(4096)
            if not chunk:
                raise RcmpWriteError("connection closed while reading a record")
            self._buf.extend(chunk)

    def _recv_record(self) -> bytes:
        self._fill(2)
        length = (self._buf[0] << 8) | self._buf[1]
        self._fill(2 + length)
        payload = bytes(self._buf[2:2 + length])
        del self._buf[:2 + length]
        return payload

    def _txn(self, framed: bytes, expect_op: int) -> dict:
        """Send one framed record, read one response, require its opcode to be
        `expect_op` (the request opcode | 0x8000)."""
        self._conn.sendall(framed)
        rec = rcmp.parse_record(self._recv_record())
        got = rec.get("opcode")
        if got != expect_op:
            raise RcmpWriteError(
                f"expected ack 0x{expect_op:04x}, got {rec.get('op')} "
                f"(0x{got:04x})" if got is not None else
                f"expected ack 0x{expect_op:04x}, got malformed record")
        return rec

    @staticmethod
    def _guard_partition(part: int) -> None:
        if part == PART_TUNING:
            raise RcmpWriteError(
                "refusing to write partition 0x82 (tuning/soft-pots): "
                "unrecoverable if corrupted")

    # -- session ---------------------------------------------------------
    def open_session(self) -> dict:
        return self._txn(rcmp.frame(bytes([0x01, 0x06, 0x00])),
                         rcmp.OP_SESSION | rcmp.RESP_FLAG)

    def close_session(self) -> dict:
        """Send the 0106 01 finalize/commit that ends a write session."""
        return self._txn(rcmp.frame(bytes([0x01, 0x06, 0x01])),
                         rcmp.OP_SESSION | rcmp.RESP_FLAG)

    def prepare(self, framed_prepare: bytes) -> dict:
        """Send a captured 0103 program/erase-prepare record verbatim."""
        return self._txn(framed_prepare, rcmp.OP_PREPARE | rcmp.RESP_FLAG)

    # -- writes ----------------------------------------------------------
    def write_object(self, part: int, obj: int, payload: bytes,
                     inst: int = 0) -> dict:
        """Encode and send one object write; require the 0x8101 write-ack."""
        self._guard_partition(part)
        framed = rcmp.build_write(part, obj, payload, inst)
        return self._txn(framed, rcmp.OP_WRITE | rcmp.RESP_FLAG)

    def send_prebuilt(self, framed: bytes) -> dict:
        """Send an already-framed record (e.g. replayed verbatim from a capture)
        and validate its ack by the record's own opcode. Partition-guarded for
        read/write records."""
        payload = framed[2:] if len(framed) >= 2 else b""
        if len(payload) >= 3 and payload[:2].hex() in ("0100", "0101"):
            self._guard_partition(payload[2])
        opcode = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 0
        return self._txn(framed, opcode | rcmp.RESP_FLAG)

    # -- lifecycle -------------------------------------------------------
    def close(self) -> None:
        try:
            self._conn.close()
        except OSError:
            pass

    def __enter__(self) -> "RcmpWriteClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
