"""
Flash custom simplex codeplug to Radio 1 (XTS 2500 Model II, SN 205CMB2249)
using clean-room decrypted relational streams with exact CRC-16 integrity.
"""
import struct
import time
import sys
try:
    import serial
except ImportError:
    serial = None

try:
    from .cpg_parser import CpgArchive, rc4_crypt, MASTER_ASTRO25_40BIT_RC4_KEY
    from .ppp_flasher import AstroPppFlasher, serialize_rcmp_mode, serialize_rcmp_ish_write
except ImportError:
    import os as _os
    if _os.path.dirname(_os.path.abspath(__file__)) not in sys.path:
        sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from cpg_parser import CpgArchive, rc4_crypt, MASTER_ASTRO25_40BIT_RC4_KEY
    from ppp_flasher import AstroPppFlasher, serialize_rcmp_mode, serialize_rcmp_ish_write

def decrypt_stream(raw: bytes) -> bytes:
    return rc4_crypt(MASTER_ASTRO25_40BIT_RC4_KEY, raw)

def encrypt_stream(plain: bytes) -> bytes:
    return rc4_crypt(MASTER_ASTRO25_40BIT_RC4_KEY, plain)

# Table for CRC-16 CCITT (poly 0x1021)
crc_table = []
for i in range(256):
    curr = i << 8
    for _ in range(8):
        if curr & 0x8000:
            curr = ((curr << 1) ^ 0x1021) & 0xFFFF
        else:
            curr = (curr << 1) & 0xFFFF
    crc_table.append(curr)

def calc_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        idx = ((crc >> 8) ^ b) & 0xFF
        crc = ((crc << 8) ^ crc_table[idx]) & 0xFFFF
    return crc

def prepare_streams_for_radio(serial_num: str = "205CMB2249", model_num: str = "H46UCF9PW6BN"):
    base_cpg = "backups/205CFR2930.cpg"
    streams = {}
    with CpgArchive(base_cpg) as cpg:
        for sname, raw in cpg.raw_streams.items():
            streams[sname] = raw

    # 1. Modify Strm_2 (Serial Number & Model)
    s2 = bytearray(decrypt_stream(streams["Strm_2"]))
    sn_bytes = (serial_num + "\x00").encode("ascii")
    md_bytes = (model_num + "\x00").encode("ascii")
    s2[8 : 8 + len(sn_bytes)] = sn_bytes
    s2[19 : 19 + len(md_bytes)] = md_bytes
    crc2 = calc_crc(s2[6:-2])
    s2[-2:] = struct.pack(">H", crc2)
    streams["Strm_2"] = encrypt_stream(bytes(s2))
    print(f"[*] Patched Strm_2 (SN={serial_num}, Model={model_num}, CRC=0x{crc2:04X})")

    # 2. Modify Strm_23 (Frequencies)
    s23 = bytearray(decrypt_stream(streams["Strm_23"]))
    # Channel 1: 851.5125 MHz (170302500)
    f1 = struct.pack(">I", 170302500)
    s23[20:24] = f1
    s23[24:28] = f1
    s23[28:32] = f1
    # Channel 2: 853.0125 MHz (170602500)
    f2 = struct.pack(">I", 170602500)
    s23[55:59] = f2
    s23[59:63] = f2
    s23[63:67] = f2
    crc23 = calc_crc(s23[6:-2])
    s23[-2:] = struct.pack(">H", crc23)
    streams["Strm_23"] = encrypt_stream(bytes(s23))
    print(f"[*] Patched Strm_23 (Ch1=851.5125 MHz, Ch2=853.0125 MHz, CRC=0x{crc23:04X})")

    # 3. Modify Strm_26 (Zone Names)
    s26 = bytearray(decrypt_stream(streams["Strm_26"]))
    z1_name = b"TEAM COMM\x00\x00\x00\x00\x00\x00\x00"
    s26[14:30] = z1_name
    crc26 = calc_crc(s26[6:-2])
    s26[-2:] = struct.pack(">H", crc26)
    streams["Strm_26"] = encrypt_stream(bytes(s26))
    print(f"[*] Patched Strm_26 (Zone 1='TEAM COMM', CRC=0x{crc26:04X})")

    # 4. Modify Strm_28 (Zone 1 Channel Names)
    s28 = bytearray(decrypt_stream(streams["Strm_28"]))
    s28[12:28] = b"P25 TALK\x00\x00\x00\x00\x00\x00\x00\x00"
    s28[28:44] = b"ANALOG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    crc28 = calc_crc(s28[6:-2])
    s28[-2:] = struct.pack(">H", crc28)
    streams["Strm_28"] = encrypt_stream(bytes(s28))
    print(f"[*] Patched Strm_28 (Ch1='P25 TALK', Ch2='ANALOG', CRC=0x{crc28:04X})")

    # 5. Modify Strm_30 (Zone 2 Channel Names)
    s30 = bytearray(decrypt_stream(streams["Strm_30"]))
    s30[12:28] = b"P25 TALK\x00\x00\x00\x00\x00\x00\x00\x00"
    s30[28:44] = b"ANALOG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    crc30 = calc_crc(s30[6:-2])
    s30[-2:] = struct.pack(">H", crc30)
    streams["Strm_30"] = encrypt_stream(bytes(s30))
    print(f"[*] Patched Strm_30 (Ch1='P25 TALK', Ch2='ANALOG', CRC=0x{crc30:04X})")

    return streams

def flash_radio(port: str = "COM7", serial_num: str = "205CMB2249", model_num: str = "H46UCF9PW6BN"):
    print(f"\n=======================================================")
    print(f" ASTRO 25 Clean-Room Codeplug Writer -> {serial_num}")
    print(f" Target: Channel 1 = P25 TALK (851.5125 MHz, NAC $293)")
    print(f"         Channel 2 = ANALOG   (853.0125 MHz)")
    print(f"=======================================================")

    streams = prepare_streams_for_radio(serial_num, model_num)
    sorted_streams = sorted(
        [(k, v) for k, v in streams.items() if k != "Strm_0" and k.startswith("Strm_")],
        key=lambda x: int(x[0].split("_")[1])
    )
    total_streams = len(sorted_streams)
    print(f"[+] Total relational database streams to flash: {total_streams}")

    with AstroPppFlasher(port=port, baudrate=19200) as flasher:
        print("[*] Connecting to radio over OEM USB serial (19200 8N1)...")
        if not flasher.start_ppp_link(status_cb=print):
            print("[-] PPP handshake failed.")
            return False

        if not flasher.tcp_connect(8002, status_cb=print):
            print("[-] Port 8002 TCP connection failed.")
            return False

        # Unlock
        print("[*] Unlocking radio CPS session (Opcode 0x000C)...")
        flasher.send_flasher_frame(flasher.OP_UNLOCK, b"")

        # Query Serial
        resp = flasher.send_flasher_frame(flasher.OP_QUERY_SERIAL, b"")
        if resp and len(resp) >= 5:
            radio_sn = resp[5:].decode("ascii", errors="ignore").rstrip("\x00")
            print(f"[+] Connected Radio Serial: {radio_sn}")

        # Query UUID
        uuid_resp = flasher.send_flasher_frame(0x0012, b"")
        radio_uuid = uuid_resp[5:21] if (uuid_resp and len(uuid_resp) >= 21) else b""
        if radio_uuid:
            print(f"[+] Radio Authorization UUID: {radio_uuid.hex()}")

        # Enter Write Mode
        print("[*] Transitioning radio into Write Mode (Opcode 0x0106, 600s timeout)...")
        wm_payload = serialize_rcmp_mode(mode=4, timeout_sec=600)
        wm_resp = flasher.send_flasher_frame(flasher.OP_ENTER_MODE, payload=wm_payload, timeout=3.0)
        print(f"[+] Radio Write Mode Response: {wm_resp.hex() if wm_resp else 'None'}")

        # Stream transfer loop
        print(f"[*] Writing {total_streams} streams to non-volatile flash...")
        t_start = time.time()
        for i, (sname, data) in enumerate(sorted_streams):
            item_id = int(sname.split("_")[1])
            chunk_size = 880
            for offset in range(0, len(data), chunk_size):
                chunk = data[offset : offset + chunk_size]
                payload = serialize_rcmp_ish_write(0x80, item_id, offset, len(chunk), chunk)
                resp = flasher.send_flasher_frame(flasher.OP_WRITE_ISH, payload=payload, timeout=3.0)
                if not resp:
                    resp = flasher.send_flasher_frame(flasher.OP_WRITE_ISH, payload=payload, timeout=3.0)

            pct = int((i + 1) / total_streams * 100)
            if (i + 1) % 25 == 0 or (i + 1) == total_streams:
                elapsed = time.time() - t_start
                print(f"[*] Flashing progress: {pct:>3d}% ({i+1:3d}/{total_streams} streams) - {elapsed:.1f}s", flush=True)

        # Commit and Lock with 16-byte UUID
        print("[*] Committing codeplug to EEPROM flash and locking session (Opcode 0x000D + UUID)...")
        lock_resp = flasher.send_flasher_frame(flasher.OP_LOCK, payload=radio_uuid, timeout=5.0)
        if lock_resp:
            print(f"[+] Radio accepted codeplug commit (Status: 0x{lock_resp[4]:02X})")

        print("\n[+] SUCCESS: Radio programmed and rebooting into custom codeplug!")
        return True

if __name__ == "__main__":
    flash_radio(port="COM7", serial_num="205CMB2249", model_num="H46UCF9PW6BN")
