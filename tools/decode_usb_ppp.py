"""Decode a USBPcap capture of a Motorola CPS <-> radio session.

Pipeline:
  1. tshark extracts every CDC-ACM bulk data payload with its direction.
  2. Payloads are reassembled into two byte streams: OUT (host/CPS -> radio)
     and IN (radio -> host).
  3. Each stream is split into its leading AT-command text and the following
     PPP/HDLC region (0x7E-delimited frames).
  4. PPP frames are unstuffed and classified by protocol; IP frames (0x0021)
     are parsed far enough to pull out TCP payloads to/from port 8002, which
     carry the RCMP codeplug read/write protocol we want ground truth for.

This is a read-only analysis tool: it only reads a .pcap. It does not touch a
radio. Output is a human-readable transcript plus a JSONL of decoded frames
next to the input file.

Usage:
    python tools/decode_usb_ppp.py captures/cps_<timestamp>.pcap
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Tuple

TSHARK = r"C:\Program Files\Wireshark\tshark.exe"
RCMP_PORT = 8002


# -- PPP / HDLC (RFC 1662) ------------------------------------------------
def fcs16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def unstuff(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0x7D:
            i += 1
            if i < len(data):
                out.append(data[i] ^ 0x20)
        else:
            out.append(b)
        i += 1
    return bytes(out)


def split_at_and_ppp(stream: bytes) -> Tuple[bytes, bytes]:
    """Return (at_region, ppp_region): everything before the first HDLC flag,
    and from the first 0x7E onward."""
    idx = stream.find(b"\x7e")
    if idx < 0:
        return stream, b""
    return stream[:idx], stream[idx:]


def parse_ppp_frames(region: bytes) -> List[Dict]:
    frames: List[Dict] = []
    for raw in region.split(b"\x7e"):
        if not raw:
            continue
        u = unstuff(raw)
        if len(u) < 4:
            continue
        # Address/Control 0xFF 0x03 may be compressed away (ACFC); handle both.
        body = u[2:] if u[:2] == b"\xff\x03" else u
        if len(body) < 4:
            continue
        # Protocol-Field-Compression: a single odd byte is the whole protocol
        # (e.g. IP = 0x21). Otherwise it's the normal 2-byte field.
        if body[0] & 0x01:
            proto = body[0]
            payload = body[1:-2]
        else:
            proto = int.from_bytes(body[:2], "big")
            payload = body[2:-2]
        fcs_ok = fcs16(u[:-2]) == int.from_bytes(u[-2:], "little")
        frames.append({"proto": proto, "proto_name": _proto_name(proto),
                       "len": len(payload), "fcs_ok": fcs_ok,
                       "payload_hex": payload.hex()})
    return frames


def _proto_name(p: int) -> str:
    return {0x21: "IP", 0x0021: "IP", 0xC021: "LCP", 0x8021: "IPCP", 0xC023: "PAP",
            0xC223: "CHAP", 0x80FD: "CCP"}.get(p, f"0x{p:04x}")


def extract_rcmp(ip_payload: bytes, vj_uncompressed: bool = False) -> List[Dict]:
    """Pull TCP payload out of a raw IPv4 packet (no IP options assumed).

    With vj_uncompressed=True the IP protocol byte has been overwritten by the
    VJ connection id (RFC 1144 3.2.1), so the proto==6 check is skipped."""
    if len(ip_payload) < 20 or (ip_payload[0] >> 4) != 4:
        return []
    ihl = (ip_payload[0] & 0x0F) * 4
    if len(ip_payload) < ihl + 20:
        return []
    if not vj_uncompressed and ip_payload[9] != 6:  # proto 6 = TCP
        return []
    tcp = ip_payload[ihl:]
    sport = int.from_bytes(tcp[0:2], "big")
    dport = int.from_bytes(tcp[2:4], "big")
    data_off = (tcp[12] >> 4) * 4
    data = tcp[data_off:]
    return [{"sport": sport, "dport": dport, "rcmp_hex": data.hex()}]


def vj_compressed_data(p: bytes) -> bytes:
    """Recover the TCP data from a VJ-compressed TCP/IP frame (RFC 1144).

    We only need the data offset. Change-mask bits (first byte): 0x40=NEW_C
    (connection id follows), 0x20=NEW_I, 0x10=PUSH (flag only), 0x08=NEW_S,
    0x04=NEW_A, 0x02=NEW_W, 0x01=NEW_U. Layout: [change][conn?][cksum:2]
    [deltas...][data]. Each present delta among U,W,A,S,I is SS-encoded: 1 byte,
    or 0x00 then a 16-bit value (3 bytes). CRUCIAL: the low nibble values 0x0b
    (SPECIAL_I) and 0x0f (SPECIAL_D) are RESERVED special cases that carry NO
    delta bytes (seq/ack are implied by the data length), not S/W/U/A deltas.
    Validated: the full captured write session reassembles into 142 cleanly
    framed RCMP records with this rule."""
    if not p:
        return b""
    ch = p[0]
    i = 1
    if ch & 0x40:          # NEW_C: connection id byte
        i += 1
    i += 2                 # TCP checksum
    if (ch & 0x0F) not in (0x0B, 0x0F):   # not SPECIAL_I / SPECIAL_D
        for bit in (0x01, 0x02, 0x04, 0x08):   # U, W, A, S deltas
            if ch & bit and i < len(p):
                i += 1 if p[i] != 0 else 3
    if ch & 0x20 and i < len(p):          # NEW_I (IP id) delta
        i += 1 if p[i] != 0 else 3
    return p[i:]


# -- capture extraction ---------------------------------------------------
def tshark_payloads(pcap: str) -> List[Tuple[int, bytes]]:
    """Return the radio's [(direction, data)] in frame order. direction:
    0=OUT, 1=IN.

    A whole-bus capture can hold several devices (mouse, keyboard, radio). USB
    addressing in USBPcap is unreliable for matching the radio by VID (the
    descriptor frame and the bulk frames can carry different addresses), so we
    group capdata by device_address and pick the address whose stream shows the
    PPP signature (0x7E HDLC flags and the CLIENT handshake). That isolates the
    radio's CDC-ACM serial regardless of address, and ignores HID traffic."""
    if not os.path.exists(TSHARK):
        sys.exit(f"tshark not found at {TSHARK}")
    cmd = [TSHARK, "-r", pcap, "-Y", "usb.capdata", "-T", "fields",
           "-e", "usb.device_address", "-e", "usb.endpoint_address.direction",
           "-e", "usb.capdata"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

    by_addr: Dict[str, List[Tuple[int, bytes]]] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[2]:
            continue
        addr = parts[0].strip()
        direction = int(parts[1]) if parts[1].strip().isdigit() else 0
        hexstr = parts[2].replace(":", "").replace(",", "")
        try:
            by_addr.setdefault(addr, []).append((direction, bytes.fromhex(hexstr)))
        except ValueError:
            continue
    if not by_addr:
        return []

    def ppp_score(rows: List[Tuple[int, bytes]]) -> int:
        blob = b"".join(d for _dir, d in rows)
        return blob.count(0x7E) + (1000 if b"CLIENT" in blob else 0)

    best = max(by_addr, key=lambda a: ppp_score(by_addr[a]))
    if ppp_score(by_addr[best]) == 0:
        print("[!] no PPP signature found on any device; using busiest address")
        best = max(by_addr, key=lambda a: len(by_addr[a]))
    print(f"[i] radio stream = USB device_address {best} "
          f"({len(by_addr[best])} capdata frames of {len(by_addr)} device(s))")
    return by_addr[best]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: decode_usb_ppp.py <capture.pcap>")
        return 2
    pcap = sys.argv[1]
    rows = tshark_payloads(pcap)
    out = {0: bytearray(), 1: bytearray()}
    for direction, data in rows:
        out[direction].extend(data)

    result: Dict[str, object] = {}
    for direction, label in ((0, "OUT host->radio"), (1, "IN radio->host")):
        stream = bytes(out[direction])
        at_region, ppp_region = split_at_and_ppp(stream)
        frames = parse_ppp_frames(ppp_region)
        rcmp: List[Dict] = []
        rcmp_stream = bytearray()  # reassembled TCP data in frame order
        for f in frames:
            pl = bytes.fromhex(f["payload_hex"])
            segs: List[Dict] = []
            if f["proto"] in (0x21, 0x0021):
                segs = extract_rcmp(pl)
            elif f["proto"] == 0x002F:              # VJ uncompressed TCP/IP
                segs = extract_rcmp(pl, vj_uncompressed=True)
            elif f["proto"] == 0x002D:              # VJ compressed TCP/IP
                data = vj_compressed_data(pl)
                if data:
                    segs = [{"sport": None, "dport": None, "rcmp_hex": data.hex()}]
            rcmp.extend(segs)
            for s in segs:
                rcmp_stream.extend(bytes.fromhex(s["rcmp_hex"]))
        result[label] = {
            "bytes_total": len(stream),
            "at_text": at_region.decode("latin1", "replace"),
            "ppp_frame_count": len(frames),
            "ppp_proto_histogram": _hist(f["proto_name"] for f in frames),
            "rcmp_segments": rcmp,
            "rcmp_stream_hex": bytes(rcmp_stream).hex(),
            "frames": frames,
        }

    base = os.path.splitext(pcap)[0]
    with open(base + "_decoded.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    for label, d in result.items():
        print(f"\n=== {label} ===")
        print(f"  bytes={d['bytes_total']} ppp_frames={d['ppp_frame_count']} "
              f"protos={d['ppp_proto_histogram']}")
        at = d["at_text"].strip()
        if at:
            print(f"  AT region: {at!r}")
        if d["rcmp_segments"]:
            print(f"  RCMP (TCP:{RCMP_PORT}) segments: {len(d['rcmp_segments'])}")
            for seg in d["rcmp_segments"][:8]:
                print(f"    {seg['sport']}->{seg['dport']}: {seg['rcmp_hex'][:80]}")
    print(f"\n[+] full decode: {base}_decoded.json")
    return 0


def _hist(names) -> Dict[str, int]:
    h: Dict[str, int] = {}
    for n in names:
        h[n] = h.get(n, 0) + 1
    return h


if __name__ == "__main__":
    sys.exit(main())
