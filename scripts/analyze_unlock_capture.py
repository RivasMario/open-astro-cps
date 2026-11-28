#!/usr/bin/env python3
"""Analyze a live CPS capture to confirm the RCMP ``UnlockSecurity`` (0x0107)
wire frame, so ``src/open_astro/protocol/unlock_session.py`` can be finalized.

Dependency-free: parses a classic ``.pcap`` (not pcapng) directly, extracts the
RCMP record stream on the radio TCP port (default 8002) in both directions, and
locates the unlock exchange. The decisive step is self-checking: it brute-forces
the 32-byte seed window in a radio->host reply against the 32-byte response
window in a host->radio record, and reports the (seed, response) pair for which
``unlock.unlock_response(seed) == response``. That pair confirms, from live
ground truth:

  * that the recovered scramble (:func:`open_astro.protocol.unlock.unlock_response`)
    is correct against a real exchange, and
  * where the seed sits in the reply and how the response record is framed --
    i.e. the exact constants needed to set ``WIRE_PROFILE_CONFIRMED = True``.

Usage:
    python scripts/analyze_unlock_capture.py <capture.pcap> [--port 8002]

Capture it on native Windows (real CPS + PortMgr, radio on the programming
cable): start a Wireshark capture on the RAS/PPP dial-up interface the radio
brings up, then in CPS Read the radio and Program it back unchanged. The
UnlockSecurity handshake rides the 0x81 write that programming performs.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from open_astro.protocol import rcmp  # noqa: E402
from open_astro.protocol.unlock import unlock_response, SEED_LEN  # noqa: E402

OP_UNLOCK = 0x0107
OP_UNLOCK_ACK = OP_UNLOCK | rcmp.RESP_FLAG  # 0x8107

# libpcap global-header magics (second form = nanosecond timestamps).
_PCAP_MAGICS = {0xA1B2C3D4: ("<", False), 0xD4C3B2A1: (">", False),
                0xA1B23C4D: ("<", True), 0x4D3CB2A1: (">", True)}

# link-layer header length to strip to reach the IP header, by LINKTYPE.
_LINKTYPE_L2 = {
    0: 4,     # NULL / loopback (4-byte address family)
    1: 14,    # ETHERNET
    101: 0,   # RAW IP
    113: 16,  # LINUX_SLL
    9: 0,     # PPP (payload starts at PPP header; handled below)
    50: 0,    # PPP_ETHER
    51: 0,    # PPP over serial (HDLC) -- handled below
}


def _iter_pcap(path):
    """Yield raw link-layer frames from a classic pcap, with its linktype."""
    with open(path, "rb") as fh:
        hdr = fh.read(24)
        if len(hdr) < 24:
            raise SystemExit(f"{path}: too short to be a pcap")
        magic = struct.unpack("<I", hdr[:4])[0]
        if magic not in _PCAP_MAGICS:
            raise SystemExit(
                f"{path}: not a classic pcap (magic 0x{magic:08x}); if this is "
                f"pcapng, re-export from Wireshark as 'pcap' (not pcapng)")
        endian, _ns = _PCAP_MAGICS[magic]
        linktype = struct.unpack(endian + "I", hdr[20:24])[0]
        while True:
            ph = fh.read(16)
            if len(ph) < 16:
                return
            _ts, _tsf, caplen, _origlen = struct.unpack(endian + "IIII", ph)
            data = fh.read(caplen)
            if len(data) < caplen:
                return
            yield linktype, data


def _l3_from_frame(linktype, frame):
    """Strip the link layer, returning the IP-layer bytes (or None)."""
    if linktype in (9, 51):  # PPP / PPP-HDLC: skip to the IP payload
        # HDLC address/control (ff 03) then PPP protocol (0x0021 = IPv4).
        i = 0
        if frame[:2] == b"\xff\x03":
            i = 2
        if frame[i:i + 2] == b"\x00\x21":
            return frame[i + 2:]
        if frame[i:i + 1] == b"\x21":
            return frame[i + 1:]
        return None
    strip = _LINKTYPE_L2.get(linktype)
    if strip is None:
        return None
    if linktype == 1 and frame[12:14] != b"\x08\x00":  # non-IPv4 EtherType
        return None
    return frame[strip:]


def _tcp_payload(l3, port):
    """Return (src, dst, seq, payload) for an IPv4/TCP segment on `port`, else None."""
    if not l3 or (l3[0] >> 4) != 4:
        return None
    ihl = (l3[0] & 0x0F) * 4
    if l3[9] != 6 or len(l3) < ihl + 20:  # proto 6 = TCP
        return None
    src = ".".join(str(b) for b in l3[12:16])
    dst = ".".join(str(b) for b in l3[16:20])
    tcp = l3[ihl:]
    sport, dport, seq = struct.unpack(">HHI", tcp[:8])
    if port not in (sport, dport):
        return None
    data_off = (tcp[12] >> 4) * 4
    payload = tcp[data_off:]
    if not payload:
        return None
    return (src, sport), (dst, dport), seq, payload


def reassemble(path, port):
    """Return {direction_key: reassembled_bytes} for TCP `port`, ordered by seq."""
    segs = {}  # (src,dst) -> list of (seq, payload)
    for linktype, frame in _iter_pcap(path):
        got = _tcp_payload(_l3_from_frame(linktype, frame), port)
        if not got:
            continue
        src, dst, seq, payload = got
        segs.setdefault((src, dst), []).append((seq, payload))
    streams = {}
    for key, parts in segs.items():
        parts.sort(key=lambda sp: sp[0])
        streams[key] = b"".join(p for _s, p in parts)
    return streams


def _windows(blob, n=SEED_LEN):
    """Yield (offset, n-byte slice) for every n-byte window in blob."""
    for off in range(0, max(0, len(blob) - n + 1)):
        yield off, blob[off:off + n]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcap")
    ap.add_argument("--port", type=int, default=8002, help="radio RCMP TCP port")
    args = ap.parse_args()

    streams = reassemble(args.pcap, args.port)
    if not streams:
        raise SystemExit(f"no TCP :{args.port} payload found in {args.pcap}")

    print(f"[*] {args.pcap}: {len(streams)} TCP :{args.port} direction(s)")
    unlock_reqs, unlock_acks = [], []
    for (src, dst), blob in streams.items():
        recs = rcmp.parse_stream(blob)
        ops = [r.get("opcode") for r in recs if r.get("opcode") is not None]
        print(f"    {src[0]}:{src[1]} -> {dst[0]}:{dst[1]}  "
              f"{len(blob)} B, {len(recs)} records; opcodes: "
              + " ".join(f"0x{o:04x}" for o in ops[:24]) + (" ..." if len(ops) > 24 else ""))
        for rec in recs:
            op = rec.get("opcode")
            body = bytes.fromhex(rec.get("body_hex") or "")
            if op == OP_UNLOCK:
                unlock_reqs.append((src, dst, body))
            elif op == OP_UNLOCK_ACK:
                unlock_acks.append((src, dst, body))

    print(f"\n[*] 0x0107 request records: {len(unlock_reqs)}; "
          f"0x8107 reply records: {len(unlock_acks)}")
    for i, (src, dst, body) in enumerate(unlock_reqs):
        print(f"    req[{i}] {len(body)} B body: {body.hex()}")
    for i, (src, dst, body) in enumerate(unlock_acks):
        print(f"    ack[{i}] {len(body)} B body: {body.hex()}")

    # Decisive check: find a seed window (in any 0x8107 reply body) and a response
    # window (in any 0x0107 request body) where unlock_response(seed) == response.
    seeds = [(ai, off, s) for ai, (_sr, _ds, b) in enumerate(unlock_acks)
             for off, s in _windows(b)]
    resps = [(ri, off, r) for ri, (_sr, _ds, b) in enumerate(unlock_reqs)
             for off, r in _windows(b)]
    for ai, s_off, seed in seeds:
        want = unlock_response(seed)
        for ri, r_off, resp in resps:
            if resp == want:
                print("\n[+] CONFIRMED: live seed->response matches unlock_response()")
                print(f"    seed     : ack[{ai}] offset {s_off} (0x{s_off:x}) : {seed.hex()}")
                print(f"    response : req[{ri}] offset {r_off} (0x{r_off:x}) : {resp.hex()}")
                print(f"\n    => set unlock_session.SEED_OFFSET = {s_off} and record this "
                      f"seed/response as a KAT, then WIRE_PROFILE_CONFIRMED = True.")
                return 0

    print("\n[-] No seed/response pair matched unlock_response().")
    print("    Check: is this the unlock exchange? right port? Is the stream the")
    print("    raw RCMP (TCP :%d) and not still PPP/HDLC-framed?" % args.port)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
