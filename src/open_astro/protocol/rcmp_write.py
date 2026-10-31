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

    def __init__(self, conn, allow_write: bool = False, timeout: float = 10.0,
                 policy=None):
        if allow_write is not True:
            raise RcmpWriteDisabled(
                "RcmpWriteClient requires allow_write=True. Writing a radio is "
                "irreversible; enable it only with a verified backup and a "
                "read-back plan.")
        self._conn = conn
        self._buf = bytearray()
        self._timeout = timeout
        # Defense in depth: on top of the per-object 0x82 guard, an optional
        # CPS-derived PartitionPolicy checks every write record on the wire
        # (partition writable + object id in CPS's observed range). Loaded lazily
        # to avoid a hard dependency when no policy is wanted.
        if policy is None:
            try:
                from .write_session import PartitionPolicy
                policy = PartitionPolicy.load()
            except Exception:
                policy = None
        self._policy = policy
        # Partitions unlocked this session via UnlockSecurity (0x0107). A
        # RW-Locked partition (0x81) is re-locked by every reboot, so this is
        # per-connection state, never cached across sessions.
        self._unlocked: set = set()

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

    def _policy_check(self, part: int, obj: int) -> None:
        """Apply the CPS-derived partition allowlist to a write, if loaded."""
        if self._policy is None:
            return
        try:
            self._policy.check(part, obj)
        except Exception as e:
            raise RcmpWriteError(str(e)) from e

    # -- security unlock (0x0107) ----------------------------------------
    def _needs_unlock(self, part: int) -> bool:
        """True if `part` is declared ReadWriteLocked by CPS and this session
        has not unlocked it yet. No policy -> no unlock gate (we cannot know)."""
        if part in self._unlocked:
            return False
        return self._policy is not None and self._policy.requires_unlock(part)

    def unlock_security(self, part: int = 0x81, inst: int = 0) -> bytes:
        """Run the UnlockSecurity (0x0107) handshake so a RW-Locked partition
        will accept persistent writes, and mark it unlocked for this session.

        Delegates to UnlockSession.perform(), which refuses to transmit until
        the request/seed wire frame is confirmed (WIRE_PROFILE_CONFIRMED). So
        this never sends a guessed unlock frame to a radio -- on an unconfirmed
        profile it raises UnlockError. The handshake runs over this client's own
        framed transport (same socket as the writes)."""
        from .unlock_session import UnlockSession
        session = UnlockSession(self._conn.sendall, self._recv_record,
                                part=part, inst=inst)
        resp = session.perform()
        self._unlocked.add(part)
        return resp

    @staticmethod
    def _ack_status(rec: dict) -> Optional[int]:
        """Status byte of a write/unlock ACK: the first body byte after the
        opcode (0 = accepted). None if the record carries no status byte."""
        body_hex = rec.get("body_hex") or ""
        return int(body_hex[:2], 16) if len(body_hex) >= 2 else None

    def _retry_if_locked(self, part: int, inst: int, framed: bytes,
                         rec: dict, expect_op: int) -> dict:
        """A bare write to a RW-Locked partition is ACKed but refused with a
        non-zero 0x8101 status (and dropped by the bootloader on reboot). When
        that happens on a partition CPS marks RW-Locked and we have not unlocked
        yet, run UnlockSecurity (0x0107) and retry the write once. A refusal we
        cannot clear by unlocking is raised, not silently swallowed."""
        status = self._ack_status(rec)
        if status in (None, 0):
            return rec
        if not self._needs_unlock(part):
            raise RcmpWriteError(
                f"radio refused write to partition 0x{part:02x} "
                f"(0x8101 status 0x{status:02x})")
        # UnlockError here if the 0x0107 wire frame is not yet confirmed.
        self.unlock_security(part, inst)
        rec = self._txn(framed, expect_op)
        status = self._ack_status(rec)
        if status not in (None, 0):
            raise RcmpWriteError(
                f"radio still refused write to partition 0x{part:02x} after "
                f"UnlockSecurity (0x8101 status 0x{status:02x})")
        return rec

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
        self._policy_check(part, obj)
        framed = rcmp.build_write(part, obj, payload, inst)
        expect = rcmp.OP_WRITE | rcmp.RESP_FLAG
        rec = self._txn(framed, expect)
        return self._retry_if_locked(part, inst, framed, rec, expect)

    def send_prebuilt(self, framed: bytes) -> dict:
        """Send an already-framed record (e.g. replayed verbatim from a capture)
        and validate its ack by the record's own opcode. Partition-guarded for
        read/write records."""
        payload = framed[2:] if len(framed) >= 2 else b""
        write_part: Optional[int] = None
        write_inst = 0
        if len(payload) >= 3 and payload[:2].hex() in ("0100", "0101"):
            self._guard_partition(payload[2])
            # Policy applies to writes (0101); reads (0100) are harmless.
            if payload[:2].hex() == "0101" and len(payload) >= 5:
                self._policy_check(payload[2], int.from_bytes(payload[3:5], "big"))
                # Write record body: [0101][part:1][obj:2][inst:2][len:2][data].
                write_part = payload[2]
                write_inst = int.from_bytes(payload[5:7], "big") if len(payload) >= 7 else 0
        opcode = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 0
        expect = opcode | rcmp.RESP_FLAG
        rec = self._txn(framed, expect)
        if write_part is not None:
            rec = self._retry_if_locked(write_part, write_inst, framed, rec, expect)
        return rec

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
