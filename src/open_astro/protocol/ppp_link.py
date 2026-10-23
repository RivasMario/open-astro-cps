"""Self-contained userspace PPP + reliable TCP over the radio's serial port.

This removes the need for a Windows RAS dial-up entry (or pppd): the tool opens
COM7 directly, performs the CLIENT handshake, negotiates LCP and IPCP, and runs
a small TCP client -- then hands a socket-like object to the RCMP clients. One
command brings the link up and talks to the radio, and the same code path works
on Linux/Fedora (just a different serial device, e.g. /dev/ttyACM0).

We control the negotiation, so we DECLINE Van Jacobson compression; the radio
then sends plain IP (PPP proto 0x0021) and no VJ decompressor is needed.

Scope: a single TCP connection (host:8001 -> radio:8002), which is all RCMP
needs. The serial link is reliable *per byte* (HDLC FCS drops corrupt frames)
but a whole PPP frame can still be lost, so the TCP layer here is RELIABLE:

  * outbound data is tracked until the radio ACKs it and retransmitted on an
    RTO timeout (bounded retries, then a clean PppError -- never a silent
    desync),
  * bytes-in-flight are bounded by a small send window and the radio's
    advertised receive window, so a write burst cannot overrun the radio
    (the failure that corrupted a codeplug mid-write over the old fire-and-
    forget sender),
  * a duplicate/retransmitted inbound segment is re-ACKed so the radio does
    not stall.

This makes `--serial` safe for WRITES, not just reads: one serial path does
everything and the RAS dial-up modem is no longer required. The write path is
still gated + partition-guarded by RcmpWriteClient; this module is pure
transport.

Addresses (from captures): us 192.168.128.2, radio 192.168.128.1.
"""
from __future__ import annotations

import struct
import time
from typing import List, Optional, Tuple

LOCAL_IP = bytes([192, 168, 128, 2])
RADIO_IP = bytes([192, 168, 128, 1])

# PPP protocol numbers
P_IP = 0x0021
P_LCP = 0xC021
P_IPCP = 0x8021

FLAG = 0x7E

# TCP reliability tuning. The link is a 115200-baud serial PPP; segments are
# small and round-trips are tens of ms, so a conservative window + ~0.4s RTO is
# safe and still fast. MSS is kept small to match the captured segment sizes and
# to stay well under the radio's receive buffer.
DEFAULT_MSS = 512
DEFAULT_WINDOW = 2048          # our max bytes in flight (before peer window)
DEFAULT_RTO = 0.4              # retransmit timeout (seconds)
DEFAULT_MAX_RETRIES = 6        # per segment, then give up with PppError


# -- HDLC async framing (RFC 1662) ---------------------------------------
def _fcs16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def _stuff(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if b in (0x7E, 0x7D) or b < 0x20:
            out += bytes([0x7D, b ^ 0x20])
        else:
            out.append(b)
    return bytes(out)


def _unstuff(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0x7D:
            i += 1
            if i < len(data):
                out.append(data[i] ^ 0x20)
        else:
            out.append(data[i])
        i += 1
    return bytes(out)


def ppp_frame(proto: int, payload: bytes) -> bytes:
    body = bytes([0xFF, 0x03]) + struct.pack(">H", proto) + payload
    return bytes([FLAG]) + _stuff(body + struct.pack("<H", _fcs16(body))) + bytes([FLAG])


# -- IP / TCP helpers -----------------------------------------------------
def _cksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f">{len(data)//2}H", data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


def _ip(src: bytes, dst: bytes, proto: int, payload: bytes, ident: int) -> bytes:
    hdr = bytearray(20)
    hdr[0] = 0x45
    struct.pack_into(">H", hdr, 2, 20 + len(payload))
    struct.pack_into(">H", hdr, 4, ident)
    hdr[6] = 0x40  # don't fragment
    hdr[8] = 64    # TTL
    hdr[9] = proto
    hdr[12:16] = src
    hdr[16:20] = dst
    struct.pack_into(">H", hdr, 10, _cksum(bytes(hdr)))
    return bytes(hdr) + payload


def _tcp(sport: int, dport: int, seq: int, ack: int, flags: int,
         payload: bytes, window: int = 8192) -> bytes:
    hdr = bytearray(20)
    struct.pack_into(">HHIIBBHHH", hdr, 0, sport, dport, seq, ack,
                     0x50, flags, window, 0, 0)
    pseudo = LOCAL_IP + RADIO_IP + bytes([0, 6]) + struct.pack(">H", 20 + len(payload))
    struct.pack_into(">H", hdr, 16, _cksum(pseudo + bytes(hdr) + payload))
    return bytes(hdr) + payload


# TCP flags
FIN, SYN, RST, PSH, ACK = 0x01, 0x02, 0x04, 0x08, 0x10

_U32 = 0xFFFFFFFF


def _seq_le(a: int, b: int) -> bool:
    """True if a <= b in 32-bit sequence space (RFC 1982 wrap-safe)."""
    return ((b - a) & _U32) < 0x80000000


class PppError(Exception):
    pass


class _OutSeg:
    """One unacked outbound data segment, tracked for retransmission."""
    __slots__ = ("seq", "data", "t_sent", "retries")

    def __init__(self, seq: int, data: bytes, t_sent: float):
        self.seq = seq
        self.data = data
        self.t_sent = t_sent
        self.retries = 0

    @property
    def end(self) -> int:
        return (self.seq + len(self.data)) & _U32


class PppTcpConn:
    """Opens the serial port, brings up PPP, and exposes ONE reliable TCP
    connection (host:8001 -> radio:8002) as a socket-like object (sendall /
    recv / close) for the RCMP read and write clients.

    Reliability: outbound data is retransmitted until ACKed (bounded), and
    bytes-in-flight are capped by `window` and the radio's advertised window.
    """

    def __init__(self, port: str, sport: int = 8001, dport: int = 8002,
                 timeout: float = 8.0, *, serial_obj=None,
                 mss: int = DEFAULT_MSS, window: int = DEFAULT_WINDOW,
                 rto: float = DEFAULT_RTO, max_retries: int = DEFAULT_MAX_RETRIES):
        if serial_obj is not None:
            # Injected transport (tests / a pre-opened port); must quack like
            # pyserial: write/read/flush/reset_input_buffer/close.
            self._ser = serial_obj
        else:
            import serial  # pyserial
            self._ser = serial.Serial(port, 115200, timeout=0.3)
        self._timeout = timeout
        self._sport = sport
        self._dport = dport
        self._ident = 1
        self._rxbuf = bytearray()          # HDLC byte accumulator
        self._appbuf = bytearray()         # reassembled inbound TCP payload
        # TCP state
        self._iss = 0x1000                 # initial send seq (before SYN)
        self._snd_una = self._iss          # oldest unacked seq
        self._snd_nxt = self._iss          # next seq to assign
        self._rcv = 0                      # next expected inbound seq
        self._peer_win = 0xFFFF            # radio's advertised receive window
        self._unacked: List[_OutSeg] = []
        self._mss = max(1, mss)
        self._window = max(self._mss, window)
        self._rto = rto
        self._max_retries = max_retries
        self._bring_up_ppp()
        self._tcp_connect()

    # -- serial frame IO -------------------------------------------------
    def _send_ppp(self, proto: int, payload: bytes) -> None:
        self._ser.write(ppp_frame(proto, payload))
        self._ser.flush()

    def _read_frame(self, deadline: float) -> Optional[Tuple[int, bytes]]:
        """Return (proto, payload) of the next PPP frame, or None on timeout."""
        while time.time() < deadline:
            chunk = self._ser.read(512)
            if chunk:
                self._rxbuf.extend(chunk)
            while True:
                try:
                    i = self._rxbuf.index(FLAG)
                    j = self._rxbuf.index(FLAG, i + 1)
                except ValueError:
                    break
                raw = bytes(self._rxbuf[i + 1:j])
                del self._rxbuf[:j + 1]
                if not raw:
                    continue
                u = _unstuff(raw)
                if len(u) < 4:
                    continue
                body = u[2:] if u[:2] == b"\xff\x03" else u
                proto = struct.unpack(">H", body[:2])[0]
                return proto, body[2:-2]
        return None

    # -- PPP negotiation -------------------------------------------------
    def _bring_up_ppp(self) -> None:
        # CLIENT handshake (Windows direct-serial style; the radio answers
        # CLIENTSERVER). Also tolerate an AT/CONNECT modem path.
        self._ser.reset_input_buffer()
        self._ser.write(b"CLIENT")
        self._ser.flush()
        time.sleep(0.3)
        self._ser.write(b"CLIENTCLIENT")  # some stacks want it repeated
        self._ser.flush()
        time.sleep(0.3)
        self._ser.read(64)  # consume CLIENTSERVER / banner if present

        deadline = time.time() + self._timeout
        # LCP: send a basic Configure-Request (magic number only) and converge.
        magic = b"\x05\x06\x12\x34\x56\x78"
        self._send_ppp(P_LCP, bytes([0x01, 0x01]) + struct.pack(">H", 4 + len(magic)) + magic)
        lcp_done_local = lcp_done_remote = False
        while time.time() < deadline and not (lcp_done_local and lcp_done_remote):
            f = self._read_frame(deadline)
            if not f:
                continue
            proto, pl = f
            if proto != P_LCP or len(pl) < 4:
                continue
            code, ident = pl[0], pl[1]
            if code == 0x01:  # peer Configure-Request -> Ack it verbatim
                self._send_ppp(P_LCP, bytes([0x02, ident]) + pl[2:])
                lcp_done_remote = True
            elif code == 0x02:  # our ConfReq acked
                lcp_done_local = True
            elif code in (0x03, 0x04):  # Nak/Reject -> resend minimal ConfReq
                self._send_ppp(P_LCP, bytes([0x01, (ident + 1) & 0xFF]) +
                               struct.pack(">H", 4 + len(magic)) + magic)
        if not (lcp_done_local and lcp_done_remote):
            raise PppError("LCP negotiation did not complete")

        # IPCP: request our IP; DECLINE VJ so the radio sends plain IP.
        ipcp_req = bytes([0x03, 0x06]) + LOCAL_IP  # option 3 = IP-Address
        self._send_ppp(P_IPCP, bytes([0x01, 0x01]) + struct.pack(">H", 4 + len(ipcp_req)) + ipcp_req)
        ipcp_local = ipcp_remote = False
        while time.time() < deadline and not (ipcp_local and ipcp_remote):
            f = self._read_frame(deadline)
            if not f:
                continue
            proto, pl = f
            if proto != P_IPCP or len(pl) < 4:
                continue
            code, ident = pl[0], pl[1]
            if code == 0x01:  # peer ConfReq: Ack IP options, Reject VJ (0x02)
                opts = pl[4:]
                ack, rej = bytearray(), bytearray()
                k = 0
                while k + 2 <= len(opts):
                    otype, olen = opts[k], opts[k + 1]
                    if olen < 2 or k + olen > len(opts):
                        break
                    chunk = opts[k:k + olen]
                    (rej if otype == 0x02 else ack).extend(chunk)  # 0x02 = VJ
                    k += olen
                if rej:
                    self._send_ppp(P_IPCP, bytes([0x04, ident]) +
                                   struct.pack(">H", 4 + len(rej)) + bytes(rej))
                else:
                    self._send_ppp(P_IPCP, bytes([0x02, ident]) +
                                   struct.pack(">H", 4 + len(ack)) + bytes(ack))
                    ipcp_remote = True
            elif code == 0x02:  # our ConfReq acked
                ipcp_local = True
            elif code in (0x03, 0x04):  # Nak/Reject of our IP -> take suggestion
                ipcp_req2 = pl[4:] if code == 0x03 else (bytes([0x03, 0x06]) + LOCAL_IP)
                self._send_ppp(P_IPCP, bytes([0x01, (ident + 1) & 0xFF]) +
                               struct.pack(">H", 4 + len(ipcp_req2)) + ipcp_req2)
        if not (ipcp_local and ipcp_remote):
            raise PppError("IPCP negotiation did not complete")

    # -- IP/TCP plumbing -------------------------------------------------
    def _send_ip(self, tcp_payload: bytes) -> None:
        self._ident = (self._ident + 1) & 0xFFFF
        self._send_ppp(P_IP, _ip(LOCAL_IP, RADIO_IP, 6, tcp_payload, self._ident))

    def _send_seg(self, seq: int, flags: int, data: bytes) -> None:
        self._send_ip(_tcp(self._sport, self._dport, seq, self._rcv, flags, data))

    def _bare_ack(self) -> None:
        self._send_seg(self._snd_nxt, ACK, b"")

    def _in_flight(self) -> int:
        return (self._snd_nxt - self._snd_una) & _U32

    def _process_ack(self, ack: int, window: int) -> None:
        """Advance snd_una on a valid cumulative ACK and drop acked segments."""
        if _seq_le(self._snd_una, ack) and _seq_le(ack, self._snd_nxt):
            self._snd_una = ack
            self._unacked = [s for s in self._unacked if not _seq_le(s.end, ack)]
        self._peer_win = window

    def _pump(self, deadline: float) -> bool:
        """Read one inbound IP/TCP segment to our port; update ACK/seq state,
        buffer any data, and ACK it. Returns True if a segment was processed."""
        f = self._read_frame(deadline)
        if not f:
            return False
        proto, pl = f
        if proto != P_IP or len(pl) < 40 or (pl[0] >> 4) != 4:
            return False
        ihl = (pl[0] & 0x0F) * 4
        if pl[9] != 6:
            return False
        tcp = pl[ihl:]
        sport, dport = struct.unpack(">HH", tcp[:4])
        if dport != self._sport:
            return False
        seq, ack = struct.unpack(">II", tcp[4:12])
        flags = tcp[13]
        window = struct.unpack(">H", tcp[14:16])[0]
        data_off = (tcp[12] >> 4) * 4
        data = tcp[data_off:]
        if flags & SYN:
            # SYN or SYN-ACK: peer's ISS; next byte we expect is seq+1.
            self._rcv = (seq + 1) & _U32
        if flags & ACK:
            self._process_ack(ack, window)
        if data:
            if seq == self._rcv:
                self._appbuf.extend(data)
                self._rcv = (self._rcv + len(data)) & _U32
                self._bare_ack()
            elif _seq_le(seq, self._rcv):
                # Duplicate / retransmitted data we already have: re-ACK so the
                # radio stops retransmitting and makes progress.
                self._bare_ack()
            else:
                # Out-of-order (gap). We don't buffer ahead on this link; send a
                # duplicate ACK for what we do have so the peer backfills.
                self._bare_ack()
        if flags & FIN:
            self._rcv = (self._rcv + 1) & _U32
            self._bare_ack()
        return True

    def _retransmit_due(self) -> None:
        """Resend the oldest unacked segment if its RTO expired; give up (raise)
        after max_retries so a dead link fails loudly instead of desyncing."""
        if not self._unacked:
            return
        seg = self._unacked[0]
        now = time.time()
        if now - seg.t_sent < self._rto:
            return
        if seg.retries >= self._max_retries:
            raise PppError(
                f"TCP retransmit limit reached (seq {seg.seq}, "
                f"{seg.retries} retries) -- radio not ACKing; link lost")
        seg.retries += 1
        seg.t_sent = now
        self._send_seg(seg.seq, PSH | ACK, seg.data)

    def _tcp_connect(self) -> None:
        deadline = time.time() + self._timeout
        self._send_seg(self._iss, SYN, b"")
        self._snd_nxt = (self._iss + 1) & _U32   # SYN consumes one seq
        self._snd_una = self._snd_nxt
        while time.time() < deadline:
            if self._pump(deadline) and self._rcv:
                # SYN-ACK seen (rcv set, our SYN acked); send the final ACK.
                self._bare_ack()
                return
        raise PppError("TCP connect to radio:8002 timed out (no SYN-ACK)")

    # -- socket-like API for the RCMP clients ----------------------------
    def sendall(self, data: bytes) -> None:
        """Reliably send all `data`: segment it, keep bytes-in-flight within the
        window, retransmit on timeout, and return only once every byte is ACKed
        by the radio. Raises PppError if the radio stops ACKing."""
        queue = bytearray(data)
        deadline = time.time() + self._timeout + self._rto * (self._max_retries + 1)
        while queue or self._unacked:
            # Fill the window with new segments.
            while queue and self._in_flight() < min(self._window, self._peer_win):
                take = min(self._mss, len(queue),
                           min(self._window, self._peer_win) - self._in_flight())
                if take <= 0:
                    break
                chunk = bytes(queue[:take])
                del queue[:take]
                seg = _OutSeg(self._snd_nxt, chunk, time.time())
                self._unacked.append(seg)
                self._snd_nxt = (self._snd_nxt + len(chunk)) & _U32
                self._send_seg(seg.seq, PSH | ACK, chunk)
            # Collect ACKs (and any interleaved inbound data) briefly.
            self._pump(time.time() + self._rto)
            # Time out / retransmit the oldest outstanding segment.
            self._retransmit_due()
            if time.time() > deadline and (queue or self._unacked):
                raise PppError("sendall timed out before all data was ACKed")

    def recv(self, n: int) -> bytes:
        deadline = time.time() + self._timeout
        while not self._appbuf and time.time() < deadline:
            self._pump(deadline)
        out = bytes(self._appbuf[:n])
        del self._appbuf[:len(out)]
        return out

    def close(self) -> None:
        try:
            self._send_seg(self._snd_nxt, FIN | ACK, b"")
            self._snd_nxt = (self._snd_nxt + 1) & _U32
        except Exception:
            pass
        try:
            self._ser.close()
        except Exception:
            pass
