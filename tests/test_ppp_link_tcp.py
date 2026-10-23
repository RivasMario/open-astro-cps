"""Offline reliability tests for the userspace PPP + TCP transport.

No radio required. A `FakeSerial` wires the client to a `MockRadio` that speaks
the same PPP/IP/TCP framing and injects faults (dropped data segments, dropped
ACKs). These prove the hardened transport is safe for WRITES -- the property
that was missing when a fire-and-forget sender corrupted a codeplug mid-write:

  * every byte the client sends arrives at the radio exactly once and in order,
    even when segments or ACKs are dropped (retransmission recovers, dedup by
    sequence number means no record is written twice),
  * bytes-in-flight never exceed the radio's advertised receive window,
  * a radio that stops ACKing fails loudly (PppError) instead of silently
    desyncing.
"""
import threading
import time

import pytest

from open_astro.protocol import ppp_link as pl
from open_astro.protocol.ppp_link import PppTcpConn, PppError


# ---------------------------------------------------------------------------
# Fake full-duplex serial line
# ---------------------------------------------------------------------------
class FakeSerial:
    """In-memory two-way byte pipe mimicking the pyserial API the client uses
    (write/flush/read/reset_input_buffer/close). `a2b` carries client->radio,
    `b2a` carries radio->client."""

    def __init__(self, rx: "bytearray", tx: "bytearray", lock: threading.Lock,
                 timeout: float = 0.05):
        self._rx = rx          # bytes available to THIS endpoint's read()
        self._tx = tx          # bytes THIS endpoint's write() appends
        self._lock = lock
        self.timeout = timeout
        self.closed = False

    def write(self, data: bytes) -> int:
        with self._lock:
            self._tx.extend(data)
        return len(data)

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        with self._lock:
            self._rx.clear()

    def read(self, n: int) -> bytes:
        end = time.time() + self.timeout
        while True:
            with self._lock:
                if self._rx:
                    take = min(n, len(self._rx))
                    out = bytes(self._rx[:take])
                    del self._rx[:take]
                    return out
            if time.time() >= end:
                return b""
            time.sleep(0.001)

    def close(self) -> None:
        self.closed = True


def make_serial_pair(timeout: float = 0.05):
    """Return (client_serial, radio_serial) sharing two buffers + a lock."""
    a2b = bytearray()   # client -> radio
    b2a = bytearray()   # radio -> client
    lock = threading.Lock()
    client = FakeSerial(rx=b2a, tx=a2b, lock=lock, timeout=timeout)
    radio = FakeSerial(rx=a2b, tx=b2a, lock=lock, timeout=timeout)
    return client, radio


# ---------------------------------------------------------------------------
# Mock radio: PPP peer + minimal TCP server + RCMP echo, with fault injection
# ---------------------------------------------------------------------------
class MockRadio(threading.Thread):
    """Runs on its own thread. Completes the CLIENT/LCP/IPCP handshake (plain
    IP, no VJ), accepts one TCP connection on :8002, reassembles inbound data,
    and ACKs it. For every complete length-prefixed RCMP record received it
    sends back a response record (opcode | 0x8000).

    Fault injection:
      drop_data_seqs: set of client sequence numbers whose data segment is
        silently dropped the FIRST time it is seen (forces a retransmit).
      drop_acks: number of outgoing ACKs to silently drop (the data is still
        accepted; only the ACK frame is lost).
      adv_window: the receive window the radio advertises (caps client flight).
      stop_acking_after: once the radio has accepted this many data bytes, it
        stops ACKing entirely (to test the client's retransmit-limit raise).
    """

    def __init__(self, serial_obj, *, drop_data_seqs=frozenset(), drop_acks=0,
                 adv_window=0xFFFF, stop_acking_after=None, echo=True):
        super().__init__(daemon=True)
        self._ser = serial_obj
        self._rxbuf = bytearray()
        self._drop_data_seqs = set(drop_data_seqs)
        self._drop_acks = drop_acks
        self._echo = echo
        self._adv_window = adv_window
        self._stop_after = stop_acking_after
        self._iss = 0x7000
        self._snd = self._iss
        self._rcv = None
        self._app = bytearray()        # reassembled inbound TCP payload
        self.received = bytearray()    # all RCMP record payloads (for asserts)
        self._dup_bytes = 0            # inbound data bytes that were duplicates
        self.dup_bytes = 0
        self._running = True
        self._max_in_flight_seen = 0
        self.max_in_flight_seen = 0

    def stop(self):
        self._running = False

    # -- framing helpers (reuse the module's encoders) ------------------
    def _send_ppp(self, proto, payload):
        self._ser.write(pl.ppp_frame(proto, payload))

    def _send_tcp(self, flags, data=b"", seq=None):
        seq = self._snd if seq is None else seq
        ackno = self._rcv or 0
        tcp = pl._tcp(8002, 8001, seq, ackno, flags, data, window=self._adv_window)
        self._ser.write(pl.ppp_frame(pl.P_IP,
                                     pl._ip(pl.RADIO_IP, pl.LOCAL_IP, 6, tcp, 1)))

    def _read_frame(self):
        chunk = self._ser.read(512)
        if chunk:
            self._rxbuf.extend(chunk)
        while True:
            try:
                i = self._rxbuf.index(pl.FLAG)
                j = self._rxbuf.index(pl.FLAG, i + 1)
            except ValueError:
                return None
            raw = bytes(self._rxbuf[i + 1:j])
            del self._rxbuf[:j + 1]
            if not raw:
                continue
            u = pl._unstuff(raw)
            if len(u) < 4:
                continue
            body = u[2:] if u[:2] == b"\xff\x03" else u
            proto = int.from_bytes(body[:2], "big")
            return proto, body[2:-2]

    # -- RCMP echo ------------------------------------------------------
    def _drain_records(self):
        """Pull complete <len:u16><payload> records out of the app buffer and
        queue an echo response (opcode | 0x8000) for each."""
        while len(self._app) >= 2:
            length = (self._app[0] << 8) | self._app[1]
            if length == 0 or len(self._app) < 2 + length:
                break
            payload = bytes(self._app[2:2 + length])
            del self._app[:2 + length]
            self.received.extend(payload)
            if not self._echo:
                continue
            opcode = int.from_bytes(payload[:2], "big")
            resp = (opcode | 0x8000).to_bytes(2, "big") + payload[2:]
            self._send_data(len(resp).to_bytes(2, "big") + resp)

    def _send_data(self, data):
        self._send_tcp(pl.PSH | pl.ACK, data)
        self._snd = (self._snd + len(data)) & pl._U32

    # -- main loop ------------------------------------------------------
    def run(self):
        # 1) CLIENT handshake
        deadline = time.time() + 3.0
        buf = bytearray()
        while time.time() < deadline and b"CLIENT" not in bytes(buf):
            buf.extend(self._ser.read(64))
        self._ser.write(b"CLIENTSERVER")

        lcp_ok = ipcp_ok = tcp_syn = False
        sent_own_lcp = sent_own_ipcp = False
        total_acked = 0
        while self._running and time.time() < deadline:
            fr = self._read_frame()
            if not fr:
                continue
            deadline = time.time() + 3.0
            proto, body = fr
            if proto == pl.P_LCP:
                code, ident = body[0], body[1]
                if code == 0x01:  # ConfReq from client -> Ack + our own ConfReq
                    self._send_ppp(pl.P_LCP, bytes([0x02, ident]) + body[2:])
                    if not sent_own_lcp:
                        magic = b"\x05\x06\x11\x22\x33\x44"
                        self._send_ppp(pl.P_LCP, bytes([0x01, 0x01]) +
                                       (4 + len(magic)).to_bytes(2, "big") + magic)
                        sent_own_lcp = True
                elif code == 0x02:
                    lcp_ok = True
            elif proto == pl.P_IPCP:
                code, ident = body[0], body[1]
                if code == 0x01:  # client ConfReq (its IP) -> Ack verbatim
                    self._send_ppp(pl.P_IPCP, bytes([0x02, ident]) + body[2:])
                    if not sent_own_ipcp:
                        ipopt = bytes([0x03, 0x06]) + pl.RADIO_IP  # IP only, no VJ
                        self._send_ppp(pl.P_IPCP, bytes([0x01, 0x01]) +
                                       (4 + len(ipopt)).to_bytes(2, "big") + ipopt)
                        sent_own_ipcp = True
                elif code == 0x02:
                    ipcp_ok = True
            elif proto == pl.P_IP and lcp_ok and ipcp_ok:
                if len(body) < 40 or body[9] != 6:
                    continue
                ihl = (body[0] & 0x0F) * 4
                tcp = body[ihl:]
                sport, dport = int.from_bytes(tcp[0:2], "big"), int.from_bytes(tcp[2:4], "big")
                if dport != 8002:
                    continue
                seq = int.from_bytes(tcp[4:8], "big")
                ackno = int.from_bytes(tcp[8:12], "big")
                flags = tcp[13]
                off = (tcp[12] >> 4) * 4
                data = tcp[off:]
                if flags & pl.SYN:
                    self._rcv = (seq + 1) & pl._U32
                    self._send_tcp(pl.SYN | pl.ACK, seq=self._iss)
                    self._snd = (self._iss + 1) & pl._U32
                    tcp_syn = True
                    continue
                if not tcp_syn:
                    continue
                if data:
                    # Track in-flight the client exposed (new bytes beyond rcv).
                    if pl._seq_le(self._rcv, seq):
                        inflight = ((seq + len(data)) - ackno) & pl._U32
                        self._max_in_flight_seen = max(self._max_in_flight_seen, inflight)
                    if seq in self._drop_data_seqs:
                        self._drop_data_seqs.discard(seq)  # drop once, then allow
                        continue
                    if self._stop_after is not None and total_acked >= self._stop_after:
                        continue  # radio has gone silent
                    if seq == self._rcv:
                        self._app.extend(data)
                        self._rcv = (self._rcv + len(data)) & pl._U32
                        total_acked += len(data)
                        if self._drop_acks > 0:
                            self._drop_acks -= 1   # accept data, drop the ACK
                        else:
                            self._send_tcp(pl.ACK)
                        self._drain_records()
                    elif pl._seq_le(seq, self._rcv):
                        self._dup_bytes += len(data)   # retransmit we already have
                        self.dup_bytes = self._dup_bytes   # publish live (no join race)
                        self._send_tcp(pl.ACK)         # re-ACK to unstick client
                if flags & pl.FIN:
                    self._rcv = (self._rcv + 1) & pl._U32
                    self._send_tcp(pl.ACK)
        self.dup_bytes = self._dup_bytes
        self.max_in_flight_seen = self._max_in_flight_seen


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _records(*payloads):
    """Frame several RCMP payloads into one wire stream."""
    out = bytearray()
    for p in payloads:
        out += len(p).to_bytes(2, "big") + p
    return bytes(out)


def _connect(radio_kwargs=None, **conn_kwargs):
    cser, rser = make_serial_pair()
    radio = MockRadio(rser, **(radio_kwargs or {}))
    radio.start()
    conn = PppTcpConn("FAKE", serial_obj=cser, timeout=3.0, **conn_kwargs)
    return conn, radio


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_handshake_and_clean_roundtrip():
    conn, radio = _connect()
    try:
        req = b"\x01\x06\x00"                    # session open
        conn.sendall(_records(req))
        resp = conn.recv(4096)
    finally:
        conn.close(); radio.stop()
    # Radio got exactly our record, once.
    assert bytes(radio.received) == req
    # We got the echoed ack record back (opcode | 0x8000).
    assert resp[2:4] == b"\x81\x06"
    assert radio.dup_bytes == 0


def test_multisegment_send_is_reassembled_in_order():
    # Payload larger than one MSS must arrive intact and in order.
    conn, radio = _connect(mss=16)
    try:
        big = bytes((i * 7) & 0xFF for i in range(200))
        rec = _records(b"\x01\x01" + big)        # looks like a write record
        conn.sendall(rec)
        conn.recv(4096)
    finally:
        conn.close(); radio.stop()
    assert bytes(radio.received) == b"\x01\x01" + big


def test_recovers_from_dropped_data_segments():
    # The radio drops the client's first two data segments; retransmission must
    # still deliver the whole stream EXACTLY ONCE (no double-write). Client data
    # starts at ISS+1 == 0x1001; with mss=16 the first two segments are 0x1001
    # and 0x1011.
    conn, radio = _connect(radio_kwargs={"drop_data_seqs": {0x1001, 0x1011}},
                           mss=16)
    try:
        body = bytes(range(64))
        conn.sendall(_records(b"\x01\x01" + body))
        conn.recv(4096)
    finally:
        conn.close(); radio.stop()
    assert bytes(radio.received) == b"\x01\x01" + body   # delivered, once


def test_recovers_from_dropped_ack():
    # Radio accepts all data but withholds every normal ACK (and does not echo),
    # so no cumulative or piggybacked ACK masks the loss. The client's RTO must
    # fire, it retransmits, the radio re-ACKs the duplicate, and the record is
    # delivered EXACTLY ONCE.
    conn, radio = _connect(radio_kwargs={"drop_acks": 100, "echo": False}, mss=16)
    try:
        body = bytes(range(40))
        conn.sendall(_records(b"\x01\x01" + body))   # returns only once ACKed
    finally:
        conn.close(); radio.stop()
    assert bytes(radio.received) == b"\x01\x01" + body
    assert radio.dup_bytes > 0           # a retransmit really happened


def test_in_flight_never_exceeds_peer_window():
    # Radio advertises a tiny receive window; the client must pace to it and
    # never put more than that many bytes in flight at once. Measured on the
    # client's own send state (snd_nxt - snd_una) at each segment send.
    win = 48
    conn, radio = _connect(radio_kwargs={"adv_window": win}, mss=16)
    samples = []
    orig_send_seg = conn._send_seg

    def spy(seq, flags, data):
        orig_send_seg(seq, flags, data)
        samples.append((conn._snd_nxt - conn._snd_una) & pl._U32)

    conn._send_seg = spy
    try:
        conn.sendall(_records(b"\x01\x01" + bytes(range(256))))
        conn.recv(4096)
    finally:
        conn.close(); radio.stop()
    assert samples, "no segments were sent"
    assert max(samples) <= win           # never overran the radio's window
    assert max(samples) > 0


def test_dead_radio_raises_instead_of_desync():
    # Radio goes silent after accepting the first bytes: the client must hit its
    # retransmit limit and raise PppError rather than hang or desync silently.
    conn, radio = _connect(
        radio_kwargs={"stop_acking_after": 1}, mss=16,
        rto=0.05, max_retries=3)
    try:
        with pytest.raises(PppError):
            conn.sendall(_records(b"\x01\x01" + bytes(range(128))))
    finally:
        conn.close(); radio.stop()
