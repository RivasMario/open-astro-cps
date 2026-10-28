"""
RCMP-over-TCP transport using the OS PPP stack (pppd) + a normal kernel socket.

Why this exists
---------------
`ppp_flasher.py` brings up PPP *and* builds raw TCP by hand in pure Python. The
handshake logic there is correct, but it rides on a hand-rolled PPP/IP stack
whose LCP/IPCP correctness the Fedora session flagged as "worked by luck on an
id match" -- a fragile foundation for TCP. The real Motorola CPS avoids this
entirely: `ByteData10.dll::CRawBytes::Open` calls its own
`RadioCustStack10.dll` stack --

    PPPConnect(...)                          ; bring up PPP (returns 1 on OK)
    PPPGetRemoteIPaddr(...)                  ; LEARN the radio's IP, don't assume
    CUSNETdpi::Nopen(ip, svc, 8001, 8002, 0) ; TCP connect to radio:8002
    CS_SOCKET_TCPCLOSE_TOUT = 200 ms
    CS_SOCKET_RXTOUT        = 5000 ms
    ... then Nread / Nwrite carry RCMP frames.

(All of that is confirmed by disassembly -- see
docs/NEXTGEN10_RCMP_DISASSEMBLY.md section 8.3.)

On Linux we have a better-tested equivalent of that stack: the kernel's own
`pppd` (which the Fedora session proved brings up a real `ppp0` that answers
ICMP), plus ordinary `socket` TCP. This module uses those instead of a
pure-Python PPP/IP/TCP reimplementation, which removes the most likely cause of
the earlier write failures (nothing was ever ACKed by the radio).

STATUS: UNTESTED against hardware as of 2026-10-22 (written on a box with no
radio attached). The RCMP opcodes and the port are verified from the CPS
binaries; the end-to-end socket path has not yet been exercised on a radio.

Bring up the link first (needs root + a real tty; run it yourself, not from an
automation shell -- see docs/AT_INTERFACE_DISCOVERY.md):

    sudo pppd /dev/ttyACM0 9600 192.168.128.2:192.168.128.1 noauth local \
        nodetach debug nocrtscts lock connect 'chat -v "" ATD CONNECT'

Then run this module's read-side probe. Writing is hard-gated (see below).
"""
from __future__ import annotations

import socket
import struct
import subprocess
from typing import Optional, Tuple

# --- RCMP opcodes: VERIFIED from NextGen10.dll (docs/NEXTGEN10_RCMP_DISASSEMBLY.md) ---
OP_UNLOCK = 0x000C        # CRcmpBundler::UnlockSecurity
OP_LOCK = 0x000D          # commit: flush RAM->flash; carries the 16-byte UUID
OP_QUERY_UUID = 0x0012    # CRcmpBundler::GetRadioUUID -> 16-byte token
OP_READ_ISH = 0x0100      # read one ISH item chunk (<= 0x370 = 880 bytes)
OP_WRITE_ISH = 0x0101     # write one ISH item chunk
OP_ENTER_MODE = 0x0106    # mode 4 = write, 6 = program; + timeout (seconds)
# NOTE: the branch's "OP_QUERY_SERIAL = 0x0011" is REFUTED -- 0x11 is the
# VT_UI1 SafeArray type tag, not an opcode. Serial is read via an ISH item.

RESP_FLAG = 0x8000        # radio response opcode = 0x8000 | request opcode

# --- Partition AccessRights enum: VERIFIED from cgIsh10c.dll ---
# (IsROPartition/IsRWPartition/IsRWLockedPartition each call GetAccessRights and
#  test the result: ==0 RO, ==1 RW, ==2 RW-locked. See NEXTGEN10 doc section 8.1.)
ACCESS_READ_ONLY = 0          # calibration / security -- NEVER write
ACCESS_READ_WRITE = 1         # the ONLY writable class
ACCESS_READ_WRITE_LOCKED = 2  # NEVER write


def partition_is_writable(access_rights: int) -> bool:
    """A partition is safe to write only if its schema AccessRights == ReadWrite.
    Soft-pot calibration and security partitions are ReadOnly / ReadWriteLocked."""
    return access_rights == ACCESS_READ_WRITE


def serialize_rcmp_ish_read(partition: int, item_id: int, offset: int = 0, length: int = 880) -> bytes:
    """Constructs the ASTRO 25 RCMP TLV binary payload for Opcode 0x0100 (Read ISH Item).
    Mirrors the TLV header structure of Write ISH (0x0101) without trailing write data:
      [Tag 1: 0x01] [Partition: 1 byte (e.g. 0x80)]
      [Tag 0: 0x00] [Item ID: 2 bytes BE]
      [Tag 0: 0x00] [Offset: 2 bytes BE]
      [Tag 0: 0x00] [Length: 2 bytes BE]
      [Tag 0: 0x00] [0x0000: 2 bytes BE]
      [Tag 0: 0x00] [Length: 2 bytes BE]
    """
    buf = bytearray()
    buf.append(1)
    buf.append(partition & 0xFF)
    buf.append(0)
    buf.extend(struct.pack("!H", item_id))
    buf.append(0)
    buf.extend(struct.pack("!H", offset))
    buf.append(0)
    buf.extend(struct.pack("!H", length))
    buf.append(0)
    buf.extend(struct.pack("!H", 0))
    buf.append(0)
    buf.extend(struct.pack("!H", length))
    return bytes(buf)

DEFAULT_RADIO_IP = "192.168.128.1"
FLASH_PORT = 8002         # confirmed: ByteData10 Nopen remote port (0x1F42)
LOCAL_PORT = 8001         # confirmed: ByteData10 Nopen local port  (0x1F41)
RX_TIMEOUT_S = 5.0        # matches CS_SOCKET_RXTOUT = 5000 ms


class RcmpError(RuntimeError):
    pass


def detect_radio_ip(iface: str = "ppp0") -> str:
    """Read the PPP peer (radio) IP from the interface, mirroring the real
    software's PPPGetRemoteIPaddr. Falls back to the known default."""
    try:
        out = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", iface],
            capture_output=True, text=True, timeout=5,
        ).stdout
        # "inet 192.168.128.2 peer 192.168.128.1/32 ..."
        for tok in out.split():
            if tok.count(".") == 3:
                pass
        import re
        m = re.search(r"peer\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    return DEFAULT_RADIO_IP


class RcmpSocketTransport:
    """RCMP framing over a kernel TCP socket (PPP link provided by pppd)."""

    def __init__(self, radio_ip: Optional[str] = None, port: int = FLASH_PORT,
                 local_port: int = LOCAL_PORT, bind_local: bool = False):
        self.radio_ip = radio_ip or detect_radio_ip()
        self.port = port
        self.local_port = local_port
        self.bind_local = bind_local
        self.sock: Optional[socket.socket] = None

    # -- connection -------------------------------------------------------
    def connect(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self.bind_local:
            # The real software uses local port 8001; binding it is optional
            # for a client connect and may require the port to be free.
            s.bind(("0.0.0.0", self.local_port))
        s.settimeout(RX_TIMEOUT_S)
        s.connect((self.radio_ip, self.port))
        self.sock = s

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def __enter__(self) -> "RcmpSocketTransport":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- RCMP framing -----------------------------------------------------
    @staticmethod
    def _frame(opcode: int, payload: bytes) -> bytes:
        # [length: u16 BE = 2 + len(payload)] [opcode: u16 BE] [payload]
        return struct.pack(">HH", 2 + len(payload), opcode) + payload

    def _send(self, opcode: int, payload: bytes = b"") -> Tuple[int, bytes]:
        """Send one RCMP request, return (status_byte, response_payload)."""
        if not self.sock:
            raise RcmpError("not connected")
        self.sock.sendall(self._frame(opcode, payload))

        # response: [len: u16 BE] [opcode: u16 BE] [status: u8] [payload...]
        hdr = self._recv_exact(2)
        (length,) = struct.unpack(">H", hdr)
        body = self._recv_exact(length)
        if len(body) < 3:
            raise RcmpError(f"short response ({len(body)} bytes)")
        resp_op, status = struct.unpack(">HB", body[:3])
        if resp_op != (RESP_FLAG | opcode):
            raise RcmpError(
                f"opcode mismatch: sent 0x{opcode:04X}, got 0x{resp_op:04X}")
        return status, body[3:]

    def _recv_exact(self, n: int) -> bytes:
        assert self.sock is not None
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RcmpError("connection closed mid-frame")
            buf.extend(chunk)
        return bytes(buf)

    # -- safe (read-only / session) operations ---------------------------
    def unlock(self) -> int:
        """OP_UNLOCK (0x0C). Opens the CPS session. Returns status byte."""
        status, _ = self._send(OP_UNLOCK, b"")
        return status

    def query_uuid(self) -> bytes:
        """OP_QUERY_UUID (0x12). Returns the 16-byte authorization token
        needed to later commit. Read-only."""
        status, payload = self._send(OP_QUERY_UUID, b"")
        if status != 0x00:
            raise RcmpError(f"query_uuid status 0x{status:02X}")
        return payload[:16]

    def read_ish(self, item_tlv: bytes) -> Tuple[int, bytes]:
        """OP_READ_ISH (0x100). Read one ISH item chunk (max 880 bytes).
        `item_tlv` is the item descriptor (type/id/partition/offset/length);
        its exact byte layout still needs confirming against WriteIshList's
        callee -- read-only, safe to probe."""
        return self._send(OP_READ_ISH, item_tlv)

    def read_ish_item(self, item_id: int, partition: int = 0x80,
                      offset: int = 0, length: int = 880) -> Tuple[int, bytes]:
        """Convenience wrapper around read_ish() using serialize_rcmp_ish_read()."""
        tlv = serialize_rcmp_ish_read(partition=partition, item_id=item_id,
                                      offset=offset, length=length)
        return self.read_ish(tlv)

    def probe(self, read_ish_id: Optional[int] = None,
              partition: int = 0x80, read_len: int = 880) -> dict:
        """Minimal end-to-end transport proof: connect, unlock, query UUID,
        and optionally perform a read-only ISH item read (e.g. item 2 = radio identity).
        No state change, no write. Use this as the first hardware test."""
        info = {"radio_ip": self.radio_ip, "port": self.port}
        info["unlock_status"] = self.unlock()
        info["uuid"] = self.query_uuid().hex()
        if read_ish_id is not None:
            status, data = self.read_ish_item(item_id=read_ish_id,
                                              partition=partition,
                                              offset=0,
                                              length=read_len)
            info["read_ish"] = {
                "item_id": read_ish_id,
                "partition": f"0x{partition:02X}",
                "status": status,
                "length": len(data),
                "data_hex": data.hex(),
            }
        return info

    # -- WRITE PATH: hard-gated ------------------------------------------
    def write_ish(self, *_args, **_kwargs):
        raise RcmpError(
            "write_ish is disabled. The codeplug and the soft-pot CALIBRATION "
            "data share this same ISH/RCMP channel, separated only by partition "
            "number (there is NO address boundary). Writing the wrong partition "
            "can destroy factory calibration unrecoverably. A write path must "
            "first gate every item against the schema's partition access class "
            "(cgIsh10c.dll: IsRWPartition true, IsROPartition / "
            "IsRWLockedPartition false). That allowlist is not built yet. See "
            "docs/NEXTGEN10_RCMP_DISASSEMBLY.md section 6b/8.1.")

    def enter_write_mode(self, *_args, **_kwargs):
        raise RcmpError("enter_write_mode is disabled until the partition "
                        "allowlist exists -- see write_ish().")

    def commit(self, *_args, **_kwargs):
        raise RcmpError("commit (OP_LOCK) is disabled until the partition "
                        "allowlist exists -- see write_ish().")


def main(argv: Optional[list] = None) -> int:
    """Read-only CLI transport probe for Fedora/Linux hardware bringup."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Read-only RCMP-over-TCP hardware probe (requires ppp0 up via pppd)"
    )
    parser.add_argument("ip", nargs="?", default=None,
                        help="Radio IP address (default: auto-detect from --iface or 192.168.128.1)")
    parser.add_argument("--ip", dest="ip_flag", default=None,
                        help="Explicit radio IP address (overrides positional ip)")
    parser.add_argument("--iface", default="ppp0",
                        help="PPP interface to query peer IP from (default: ppp0)")
    parser.add_argument("--port", type=int, default=FLASH_PORT,
                        help=f"Remote TCP flasher port (default: {FLASH_PORT})")
    parser.add_argument("--bind-local", action="store_true",
                        help=f"Bind local TCP port {LOCAL_PORT} (matches CPS ByteData10)")
    parser.add_argument("--read-ish", type=int, default=None, metavar="ITEM_ID",
                        help="Perform a safe read-only OP_READ_ISH test for ITEM_ID (e.g., 2 for Radio Identity)")
    parser.add_argument("--partition", type=lambda x: int(x, 0), default=0x80,
                        help="ISH partition ID for --read-ish (default: 0x80)")
    parser.add_argument("--length", type=int, default=880,
                        help="Max bytes to request in --read-ish (default: 880)")
    parser.add_argument("--json", action="store_true",
                        help="Print probe result as formatted JSON")

    args = parser.parse_args(argv)
    target_ip = args.ip_flag or args.ip or detect_radio_ip(args.iface)

    try:
        with RcmpSocketTransport(radio_ip=target_ip, port=args.port,
                                 bind_local=args.bind_local) as t:
            if not args.json:
                print(f"[+] Connected to {t.radio_ip}:{t.port}")
            res = t.probe(read_ish_id=args.read_ish,
                          partition=args.partition,
                          read_len=args.length)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"[+] Unlock status : 0x{res['unlock_status']:02X}")
                print(f"[+] Radio UUID    : {res['uuid']}")
                if "read_ish" in res:
                    rish = res["read_ish"]
                    print(f"[+] Read ISH #{rish['item_id']} ({rish['partition']}): "
                          f"status=0x{rish['status']:02X}, {rish['length']} bytes")
                    if rish["data_hex"]:
                        print(f"    Hex preview   : {rish['data_hex'][:64]}"
                              f"{'...' if len(rish['data_hex']) > 64 else ''}")
            return 0
    except Exception as e:
        print(f"[-] Transport probe failed: {e}")
        print("    Is ppp0 up? Run the pppd command in this module's docstring.")
        return 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
