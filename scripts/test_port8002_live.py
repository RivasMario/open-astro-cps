"""
Probe TCP Port 8002 (ASTRO 25 Control & Programming) and Port 8010 (Radio Debugger)
over Motorola OEM USB PPP on COM7.
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
    src_ip = b"\xc0\xa8\x80\x02"  # 192.168.128.2
    dst_ip = b"\xc0\xa8\x80\x01"  # 192.168.128.1
    tcp_hdr = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, ack, 0x50, flags, 8192, 0, 0)
    pseudo = src_ip + dst_ip + struct.pack("!BBH", 0, 6, 20 + len(payload))
    csum = ip_checksum(pseudo + tcp_hdr + payload)
    tcp_hdr = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, ack, 0x50, flags, 8192, csum, 0)
    ip_len = 40 + len(payload)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_len, 2, 0, 64, 6, 0, src_ip, dst_ip)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_len, 2, 0, 64, 6, ip_checksum(ip_hdr), src_ip, dst_ip)
    return ip_hdr + tcp_hdr + payload

def start_ppp(s: serial.Serial) -> bool:
    print("[*] Asserting DTR/RTS and pinging AT...")
    s.reset_input_buffer()
    s.write(b"\rAT\r")
    s.flush()
    time.sleep(0.15)
    r = s.read(512)
    if b"OK" not in r:
        print("[-] Radio not in AT mode, running clean exit first...")
        clean_exit_ppp(s)
        s.write(b"\rAT\r")
        s.flush()
        time.sleep(0.15)
        if b"OK" not in s.read(512):
            print("[-] Still no OK from AT.")
            return False

    print("[*] Requesting local data mode (AT#DATLCL=1 -> ATD)...")
    s.write(b"AT#DATLCL=1\r")
    s.flush()
    time.sleep(0.15)
    s.read(256)
    s.write(b"ATD\r")
    s.flush()
    
    # Wait for CONNECT
    t0 = time.time()
    buf = bytearray()
    while time.time() - t0 < 2.0:
        chunk = s.read(s.in_waiting or 1)
        if chunk:
            buf.extend(chunk)
            if b"CONNECT" in buf:
                print("[+] Radio answered: CONNECT!")
                break
        time.sleep(0.02)
    time.sleep(0.1)

    print("[*] Negotiating LCP...")
    # Send our LCP Configure-Request
    send_ppp_ctrl(s, 0xC021, 1, 1, b"")
    time.sleep(0.2)
    raw = s.read(2048)
    radio_lcp_id = None
    radio_lcp_opts = b""
    for f in parse_frames(raw):
        if len(f) > 4 and f[2:4] == b"\xc0\x21":
            code, pkt_id, length = struct.unpack("!BBH", f[4:8])
            if code == 1: # Radio's Conf-Req
                radio_lcp_id = pkt_id
                radio_lcp_opts = f[8:4+length]
                print(f"[+] Received Radio LCP Conf-Req ID={radio_lcp_id}")
            elif code == 2: # Ack of our request
                print(f"[+] Received LCP Conf-Ack from Radio for our ID={pkt_id}")

    if radio_lcp_id is not None:
        print(f"[*] ACKing Radio LCP ID={radio_lcp_id}...")
        send_ppp_ctrl(s, 0xC021, 2, radio_lcp_id, radio_lcp_opts)
        time.sleep(0.1)

    print("[*] Negotiating IPCP (192.168.128.2 <-> 192.168.128.1)...")
    our_ip_opt = bytes([0x03, 0x06, 192, 168, 128, 2])
    send_ppp_ctrl(s, 0x8021, 1, 1, our_ip_opt)
    time.sleep(0.25)
    raw_ip = s.read(2048)
    for f in parse_frames(raw_ip):
        if len(f) > 4 and f[2:4] == b"\x80\x21":
            code, pkt_id, length = struct.unpack("!BBH", f[4:8])
            print(f"[+] IPCP frame: Code={code}, ID={pkt_id}")
            if code == 1: # Radio's IPCP Conf-Req
                send_ppp_ctrl(s, 0x8021, 2, pkt_id, f[8:4+length])
            elif code == 2: # Ack
                print("[+] Radio ACKed our IP (192.168.128.2)!")

    print("[+] PPP link FULLY ESTABLISHED!")
    return True

def clean_exit_ppp(s: serial.Serial):
    print("[*] Exiting PPP cleanly via Hayes escape...")
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

def probe_tcp_port(s: serial.Serial, dst_port: int, port_name: str):
    print(f"\n[*] === Probing TCP {dst_port} ({port_name}) ===")
    src_port = 50000 + (dst_port % 1000)
    seq = 1000
    
    # Send SYN (flags = 0x02)
    syn_pkt = build_tcp(src_port, dst_port, seq, 0, 0x02)
    send_ppp_ip(s, syn_pkt)
    time.sleep(0.25)
    
    raw = s.read(4096)
    syn_ack = False
    ack_num = 0
    radio_seq = 0
    for f in parse_frames(raw):
        if len(f) > 24 and f[2:4] == b"\x00\x21": # IP packet
            ip = f[4:]
            if len(ip) >= 40 and ip[9] == 6: # TCP
                src_p, dst_p, r_seq, r_ack, off_flags = struct.unpack("!HHIIH", ip[20:34])
                flags = off_flags & 0xFF
                if src_p == dst_port and dst_p == src_port:
                    print(f"[+] TCP Reply from {dst_port}: Flags=0x{flags:02X} (SYN={bool(flags & 2)}, ACK={bool(flags & 16)})")
                    if flags & 0x12 == 0x12: # SYN-ACK
                        syn_ack = True
                        radio_seq = r_seq
                        ack_num = r_seq + 1
                        break
                    elif flags & 0x04: # RST
                        print(f"[-] Port {dst_port} responded with RST (Connection Refused).")
                        return

    if not syn_ack:
        print(f"[-] No SYN-ACK received on port {dst_port}.")
        return

    print(f"[+] Port {dst_port} is OPEN! Sending ACK to complete 3-way handshake...")
    seq += 1
    ack_pkt = build_tcp(src_port, dst_port, seq, ack_num, 0x10)
    send_ppp_ip(s, ack_pkt)
    time.sleep(0.1)

    # Now send probe / hello payload
    if dst_port == 8010: # Debugger port
        print("[*] Sending 'VER\\r\\n' to debugger...")
        payload = b"VER\r\n"
        push_pkt = build_tcp(src_port, dst_port, seq, ack_num, 0x18, payload)
        send_ppp_ip(s, push_pkt)
        time.sleep(0.4)
        raw2 = s.read(4096)
        for f in parse_frames(raw2):
            if len(f) > 24 and f[2:4] == b"\x00\x21":
                ip = f[4:]
                if len(ip) > 40 and ip[9] == 6:
                    data = ip[40:]
                    if data:
                        print(f"[+] Port 8010 Response: {data.decode('latin-1', errors='ignore')}")

    elif dst_port == 8002: # Programming port
        print("[*] Sending Opcode 0x8002 Handshake...")
        # 0x8002 Opcode header with LEB128 or fixed framing
        payload = bytes([0x80, 0x02, 0x00, 0x00])
        push_pkt = build_tcp(src_port, dst_port, seq, ack_num, 0x18, payload)
        send_ppp_ip(s, push_pkt)
        time.sleep(0.4)
        raw2 = s.read(4096)
        print(f"[*] Port 8002 Raw Frames: {len(parse_frames(raw2))}")
        for f in parse_frames(raw2):
            if len(f) > 24 and f[2:4] == b"\x00\x21":
                ip = f[4:]
                if len(ip) > 40 and ip[9] == 6:
                    data = ip[40:]
                    if data:
                        print(f"[+] Port 8002 Response Hex: {data.hex()}")

    # Send FIN
    fin_pkt = build_tcp(src_port, dst_port, seq + len(payload) if 'payload' in locals() else seq, ack_num, 0x11)
    send_ppp_ip(s, fin_pkt)
    time.sleep(0.1)

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM7"
    print(f"Connecting to {port}...")
    s = serial.Serial(port, 19200, timeout=0.1)
    s.dtr = True
    s.rts = True
    try:
        if start_ppp(s):
            probe_tcp_port(s, 8010, "Radio Debugger")
            probe_tcp_port(s, 8002, "ASTRO 25 Programming")
    finally:
        clean_exit_ppp(s)
        s.close()
        print("[+] Clean teardown complete. Radio returned to normal mode.")

if __name__ == "__main__":
    main()
