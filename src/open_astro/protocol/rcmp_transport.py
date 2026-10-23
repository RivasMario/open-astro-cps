"""Live, READ-ONLY RCMP transport for Motorola ASTRO 25 radios.

Layering (see docs/RCMP_WIRE_PROTOCOL.md):
  * The radio speaks RCMP over TCP, port 8002, reachable at 192.168.128.1 once
    the PPP link is up.
  * Bringing the PPP link up is left to the OS / CPS's RAS entry (Windows RAS
    "CLIENT"->"CLIENTSERVER" direct-serial dial). This module does NOT dial PPP
    and does NOT reimplement PPP/VJ/TCP -- it opens an ordinary TCP socket to
    the radio's PPP address, so any working bring-up (rasdial, pppd) is fine.
  * rcmp.py builds/parses the records; this module just moves them over a
    socket.

SAFETY: this client is deliberately read-only. It exposes session-open and
object reads only. There is no write method -- writing a real radio stays
gated in flasher.py until the write framing is fully verified.
"""
from __future__ import annotations

import socket
import struct
from typing import List, Optional, Protocol

from . import rcmp

RADIO_PPP_HOST = "192.168.128.1"
RCMP_PORT = 8002
HOST_SRC_PORT = 8001   # captures show the host always connects from TCP 8001
LOCAL_PPP_IP = "192.168.128.2"
ACK_HEADER_LEN = 12    # read-ack echoes a 12-byte request header before data
ACK_CRC_LEN = 2        # ...and a 2-byte CRC-16 trailer after the object bytes

# Object tags the codeplug decoder consumes (== .cpg OLE stream tags): channel
# names, conventional freq/NAC, channel->personality refs, talkgroups, sites,
# and scan-list tables. read_streams() probes instances of each.
CODEPLUG_OBJECT_TAGS = [
    0x0FFF, 0x0FFD, 0x0FFC, 0x0FF8, 0x0FDC,
    0x004C, 0x004D, 0x004F, 0x006C, 0x006E,
]


class _Conn(Protocol):
    """Minimal socket-like interface so tests can inject a fake transport."""
    def sendall(self, data: bytes) -> None: ...
    def recv(self, n: int) -> bytes: ...
    def close(self) -> None: ...


class RcmpError(Exception):
    pass


class RcmpReadClient:
    """Read-only RCMP client over a socket-like connection.

    Usage:
        with RcmpReadClient.connect() as c:
            c.open_session()
            data = c.read_object(rcmp.PART_CODEPLUG, 0x0047, 0x0010)
    """

    def __init__(self, conn: _Conn, timeout: float = 5.0):
        self._conn = conn
        self._buf = bytearray()
        self._timeout = timeout

    # -- construction ----------------------------------------------------
    @classmethod
    def connect(cls, host: str = RADIO_PPP_HOST, port: int = RCMP_PORT,
                timeout: float = 10.0, src_port: int = HOST_SRC_PORT,
                src_ip: str = LOCAL_PPP_IP) -> "RcmpReadClient":
        """Open a TCP socket to the radio. Requires the PPP link already up
        (host reachable). The radio's RCMP server accepts connections from the
        host's PPP address on source port 8001 (as every capture shows), so we
        bind that local endpoint; pass src_port=0 to let the OS pick. Raises
        RcmpError with a clear hint on failure."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # RST-close instead of lingering, so our fixed source port 8001 does not
        # sit in TIME_WAIT and block the next read (the radio drops PPP after
        # each session, so reconnects come fast). l_onoff=1, l_linger=0.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                        struct.pack("ii", 1, 0))
        try:
            if src_port:
                try:
                    sock.bind((src_ip, src_port))
                except OSError:
                    sock.bind(("", src_port))  # fall back to any local IP
            sock.settimeout(timeout)
            sock.connect((host, port))
        except OSError as e:
            sock.close()
            raise RcmpError(
                f"cannot reach radio at {host}:{port} from :{src_port} ({e}). "
                f"Is the PPP link up (192.168.128.2) and CPS closed?"
            ) from e
        return cls(sock, timeout=timeout)

    # -- low-level record IO ---------------------------------------------
    def _fill(self, need: int) -> None:
        while len(self._buf) < need:
            chunk = self._conn.recv(4096)
            if not chunk:
                raise RcmpError("connection closed while reading a record")
            self._buf.extend(chunk)

    def _recv_record(self) -> bytes:
        """Read one framed record payload (<len:u16 be><payload>)."""
        self._fill(2)
        length = (self._buf[0] << 8) | self._buf[1]
        self._fill(2 + length)
        payload = bytes(self._buf[2:2 + length])
        del self._buf[:2 + length]
        return payload

    def _send(self, framed: bytes) -> None:
        self._conn.sendall(framed)

    # -- operations (read-only) ------------------------------------------
    def open_session(self) -> dict:
        """Send the session-open record and return the parsed ack."""
        self._send(rcmp.build_session_open())
        ack = rcmp.parse_record(self._recv_record())
        if ack.get("opcode") != (rcmp.OP_SESSION | rcmp.RESP_FLAG):
            # Some firmware may ack differently; surface it rather than guess.
            raise RcmpError(f"unexpected session-open reply: {ack}")
        return ack

    def read_object(self, part: int, obj: int, length: int,
                    inst: int = 0) -> bytes:
        """Issue a READ and return the response body bytes.

        Sends one READ request and collects response record bodies until the
        requested length is satisfied or the radio stops sending. Returns the
        concatenated response payload (header stripped)."""
        self._send(rcmp.build_read(part, obj, length, inst))
        # The radio answers a read with ONE response record carrying whatever it
        # has for that object -- not necessarily the full requested length. So
        # read exactly one READ_ACK and return its data; do not loop waiting for
        # `length` bytes (that hangs when the object is shorter than requested).
        rec = rcmp.parse_record(self._recv_record())
        if rec.get("opcode") != (rcmp.OP_READ | rcmp.RESP_FLAG):
            raise RcmpError(f"expected READ_ACK, got {rec.get('op')}")
        # Read-ack body = 12-byte echoed request header
        # (00 <part> <obj:2> <inst:2> <reqlen:2> 00 00 <acklen:2>) + the object
        # bytes + a 2-byte CRC-16 trailer. Strip BOTH so we return exactly the
        # object payload (equal to the decrypted .cpg stream). Verified live on
        # 407CHT0214 (0x0fff, 278 B) and 205CFR2930 (0x0fff, 40 B).
        body = bytes.fromhex(str(rec["body_hex"]))
        if len(body) <= ACK_HEADER_LEN + ACK_CRC_LEN:
            return b""
        return body[ACK_HEADER_LEN:-ACK_CRC_LEN]

    # -- lifecycle -------------------------------------------------------
    def read_streams(self, tags=None, max_inst: int = 32, block: int = 0x0370,
                     verbose: bool = False):
        """Read a full codeplug as (tag, instance, payload) records.

        For each object tag, reads instances 0,1,2... until the radio returns
        empty or errors, which self-adapts to radios with more zones than any
        single captured plan. Returns the list the CpgDecoder consumes via
        build_from_streams(). Read-only."""
        if tags is None:
            tags = CODEPLUG_OBJECT_TAGS
        import sys as _sys
        out = []
        for tag in tags:
            for inst in range(max_inst):
                try:
                    data = self.read_object(rcmp.PART_CODEPLUG, tag, block, inst)
                except Exception as e:
                    # A missing instance (or a transient) ends this tag; never
                    # let one object abort the whole dump -- return what we got.
                    if verbose:
                        print(f"    0x{tag:04x} inst {inst}: stop ({e})", file=_sys.stderr)
                    break
                if not data:
                    if verbose:
                        print(f"    0x{tag:04x} inst {inst}: stop (empty)", file=_sys.stderr)
                    break
                if verbose:
                    print(f"    0x{tag:04x} inst {inst}: {len(data)} bytes", file=_sys.stderr)
                out.append((tag, inst, data))
        return out

    def close(self) -> None:
        try:
            self._conn.close()
        except OSError:
            pass

    def __enter__(self) -> "RcmpReadClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
