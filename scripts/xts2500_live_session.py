"""
Live session utility for Motorola XTS 2500 over OEM USB (0CAD:1001).
IMPORTANT: Never send PPP LCP Terminate-Request (0xC021 Code 5), as R15.00.00
firmware tears down the PPP daemon without re-attaching the AT command parser.
Always exit PPP via the Hayes escape sequence: 1.1s pause -> '+++' -> 1.1s pause -> 'ATH\\r' -> 'AT#DATLCL=0\\r'.
"""
import serial
import struct
import time
import sys


def ppp_fcs16(data: bytes) -> bytes:
    fcs = 0xFFFF
    for b in data:
        fcs ^= b
        for _ in range(8):
            fcs = (fcs >> 1) ^ 0x8408 if (fcs & 1) else (fcs >> 1)
    fcs ^= 0xFFFF
    return bytes([fcs & 0xFF, (fcs >> 8) & 0xFF])


def ppp_escape(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if b < 0x20 or b in (0x7E, 0x7D):
            out.append(0x7D)
            out.append(b ^ 0x20)
        else:
            out.append(b)
    return bytes(out)


def ppp_unescape(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0x7D and i + 1 < len(data):
            out.append(data[i + 1] ^ 0x20)
            i += 2
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def parse_frames(raw: bytes):
    frames = []
    for part in raw.split(b"\x7e"):
        if not part:
            continue
        u = ppp_unescape(part)
        if len(u) >= 4:
            frames.append(u[:-2])
    return frames


def send_ppp_ctrl(s: serial.Serial, proto: int, code: int, pkt_id: int, payload: bytes = b""):
    length = 4 + len(payload)
    body = bytes([0xFF, 0x03, (proto >> 8) & 0xFF, proto & 0xFF, code, pkt_id, (length >> 8) & 0xFF, length & 0xFF]) + payload
    frame = b"\x7e" + ppp_escape(body + ppp_fcs16(body)) + b"\x7e"
    s.write(frame)
    s.flush()


def send_ppp_ip(s: serial.Serial, ip_pkt: bytes):
    body = b"\xff\x03\x00\x21" + ip_pkt
    frame = b"\x7e" + ppp_escape(body + ppp_fcs16(body)) + b"\x7e"
    s.write(frame)
    s.flush()


def ip_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def build_tcp(src_port: int, dst_port: int, seq: int, ack: int, flags: int, payload: bytes = b"") -> bytes:
    src_ip = b"\xc0\xa8\x80\x02"
    dst_ip = b"\xc0\xa8\x80\x01"
    tcp_hdr = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, ack, 0x50, flags, 8192, 0, 0)
    pseudo = src_ip + dst_ip + struct.pack("!BBH", 0, 6, 20 + len(payload))
    csum = ip_checksum(pseudo + tcp_hdr + payload)
    tcp_hdr = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, ack, 0x50, flags, 8192, csum, 0)
    ip_len = 40 + len(payload)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_len, 2, 0, 64, 6, 0, src_ip, dst_ip)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_len, 2, 0, 64, 6, ip_checksum(ip_hdr), src_ip, dst_ip)
    return ip_hdr + tcp_hdr + payload


def start_ppp(s: serial.Serial) -> bool:
    """Enter PPP mode deterministically via AT#DATLCL=1 (and ATD if needed) and complete LCP + IPCP."""
    s.reset_input_buffer()
    s.write(b"\rAT\r")
    s.flush()
    time.sleep(0.15)
    if b"OK" not in s.read(512):
        clean_exit_ppp(s)
    s.write(b"AT#DATLCL=1\r")
    s.flush()
    time.sleep(0.25)
    raw = s.read(2048)
    if b"~" not in raw:
        s.write(b"ATD\r")
        s.flush()
        time.sleep(0.25)
        raw += s.read(2048)
    send_ppp_ctrl(s, 0xC021, 1, 10, b"")
    time.sleep(0.25)
    raw += s.read(2048)
    for f in parse_frames(raw):
        if f[2:4] == b"\xc0\x21" and f[4] == 1:
            send_ppp_ctrl(s, 0xC021, 2, f[5], f[8:])
    time.sleep(0.15)
    s.read(2048)
    send_ppp_ctrl(s, 0x8021, 1, 11, b"\x03\x06\xc0\xa8\x80\x02")
    time.sleep(0.3)
    for f in parse_frames(s.read(2048)):
        if f[2:4] == b"\x80\x21" and f[4] == 1:
            send_ppp_ctrl(s, 0x8021, 2, f[5], f[8:])
    time.sleep(0.15)
    s.read(2048)
    return True


def clean_exit_ppp(s: serial.Serial):
    """Exit PPP back to AT command mode without orphaning the USB serial parser."""
    time.sleep(1.1)
    s.write(b"+++")
    s.flush()
    time.sleep(1.1)
    s.write(b"ATH\r")
    s.flush()
    time.sleep(0.15)
    s.write(b"AT#DATLCL=0\r")
    s.flush()
    time.sleep(0.15)
    return s.read(512)

