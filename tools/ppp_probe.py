"""Standalone reproducer for the real PPP/LCP/IPCP handshake with the radio.

Confirmed working against a Motorola XTS 2500 (native-USB ASTRO25 CDC-ACM
interface) on 2026-10-20: AT -> ATD (CONNECT) -> real RFC 1661/1662 LCP
negotiation -> real IPCP negotiation, assigning 192.168.128.2 (us) /
192.168.128.1 (radio). See docs/AT_INTERFACE_DISCOVERY.md for the full
writeup and docs/PROTOCOL_STATUS.md for current project status.

This script only proves the handshake works and prints the radio's raw LCP/
IPCP frames. It does not bring up a kernel ppp0 interface -- for that, run
pppd directly against the serial device (needs root, run in a real
interactive terminal, not a non-tty automation shell):

    sudo pppd /dev/ttyACM0 9600 192.168.128.2:192.168.128.1 noauth local \
        nodetach debug dump nocrtscts lock connect 'chat -v "" ATD CONNECT'

Once ppp0 is up, the radio answers ICMP ping (confirmed, ~13ms RTT). A full
TCP connect scan (nmap -sT -p1-65535) of 192.168.128.1 came back entirely
filtered -- no TCP service. A UDP scan was started but not completed this
session (the pppd link died mid-scan, possibly from flooding the slow
single serial channel with a full 65535-port scan at once -- the radio
itself stayed on the USB bus throughout, so this was a link issue, not a
hardware fault). Next step: rerun pppd, then scan UDP with a narrower range
and slower rate, e.g.:

    sudo nmap -Pn -sU -p1-1024,8000-8100,20000-20100 --max-retries 1 -T2 \
        192.168.128.1
"""
import serial
import struct
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"


def fcs16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def stuff(data):
    out = bytearray()
    for b in data:
        if b in (0x7E, 0x7D) or b < 0x20:
            out += bytes([0x7D, b ^ 0x20])
        else:
            out.append(b)
    return bytes(out)


def unstuff(data):
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0x7D:
            i += 1
            out.append(data[i] ^ 0x20)
        else:
            out.append(b)
        i += 1
    return bytes(out)


def ppp_frame(protocol, payload):
    body = bytes([0xFF, 0x03]) + struct.pack(">H", protocol) + payload
    fcs = fcs16(body)
    return b"\x7e" + stuff(body + struct.pack("<H", fcs)) + b"\x7e"


def parse_frames(raw):
    out = []
    for p in raw.split(b"\x7e"):
        if not p:
            continue
        u = unstuff(p)
        if len(u) < 6:
            out.append(("short", u))
            continue
        proto = struct.unpack(">H", u[2:4])[0]
        body = u[4:-2]
        fcs_ok = struct.unpack("<H", u[-2:])[0] == fcs16(u[:-2])
        out.append((proto, body, fcs_ok))
    return out


def main():
    ser = serial.Serial(PORT, 9600, timeout=1)
    time.sleep(0.3)
    ser.reset_input_buffer()

    def send(label, data, settle=1.5):
        ser.write(data)
        time.sleep(settle)
        resp = ser.read(4096)
        print(f"{label} sent: {data.hex()} -> resp: {resp!r}")
        return resp

    send("AT", b"AT\r\n", 0.5)
    send("ATD", b"ATD\r\n", 1.0)

    # LCP: empty Configure-Request, generic Configure-Ack (id=1 happens to
    # match the radio's own Configure-Request id in practice -- this is NOT
    # spec-correct, a real ack must mirror the peer's options, but the
    # radio's stack accepted it and moved on to IPCP anyway).
    lcp_req = bytes([0x01, 0x01]) + struct.pack(">H", 4)
    send("LCP ConfReq", ppp_frame(0xC021, lcp_req), 1.5)
    lcp_ack = bytes([0x02, 0x01]) + struct.pack(">H", 4)
    r = send("LCP ConfAck", ppp_frame(0xC021, lcp_ack), 1.5)
    for f in parse_frames(r):
        print("  ->", f)

    # IPCP: ack the radio's Configure-Request verbatim (it asks for IP
    # 192.168.128.1 + VJ header compression), then send our own
    # Configure-Request asking for 192.168.128.2.
    ipcp_ack_body = (
        bytes([0x02, 0x01]) + struct.pack(">H", 0x0010)
        + bytes.fromhex("0306c0a8800102060 02d0501".replace(" ", ""))
    )
    r2 = send("IPCP ConfAck(theirs)", ppp_frame(0x8021, ipcp_ack_body), 1.5)
    for f in parse_frames(r2):
        print("  ->", f)

    our_ipcp_req = (
        bytes([0x01, 0x02]) + struct.pack(">H", 0x0006)
        + bytes([0x03, 6]) + bytes([192, 168, 128, 2])
    )
    r3 = send("IPCP ConfReq(ours)", ppp_frame(0x8021, our_ipcp_req), 1.5)
    for f in parse_frames(r3):
        print("  ->", f)

    r4 = send("extra read", b"", 1.5)
    for f in parse_frames(r4):
        print("  ->", f)

    ser.close()


if __name__ == "__main__":
    main()
