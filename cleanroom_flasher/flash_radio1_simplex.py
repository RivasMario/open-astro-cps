"""
ASTRO 25 Clean-Room Codeplug Writer for Radio 1 (XTS 2500 Model II, SN 205CMB2249).
Directly patches Radio 1's native 501-stream layout with P25 TALK and ANALOG simplex,
computes exact relational CRC-16 integrity, and commits via authenticated OP_LOCK (0x000D) with 16-byte UUID token.
"""
import ctypes
from ctypes import wintypes
import struct
import time
import sys

from open_astro.parsers.cpg_parser import CpgArchive
from open_astro.protocol.ppp_flasher import AstroPppFlasher, serialize_rcmp_mode, serialize_rcmp_ish_write

# CryptoAPI RC4/MD5 Master Decryptor/Encryptor
advapi32 = ctypes.windll.advapi32
PROV_RSA_FULL = 1
CRYPT_VERIFYCONTEXT = 0xF0000000
CALG_MD5 = 0x8003
CALG_RC4 = 0x6801

hProv = wintypes.HANDLE()
advapi32.CryptAcquireContextA(ctypes.byref(hProv), None, b'Microsoft Base Cryptographic Provider v1.0', PROV_RSA_FULL, CRYPT_VERIFYCONTEXT)

def decrypt_stream(raw: bytes) -> bytes:
    hHash = wintypes.HANDLE()
    advapi32.CryptCreateHash(hProv, CALG_MD5, 0, 0, ctypes.byref(hHash))
    advapi32.CryptHashData(hHash, b'A8Z6J9QP5', 9, 0)
    hKey = wintypes.HANDLE()
    advapi32.CryptDeriveKey(hProv, CALG_RC4, hHash, 0, ctypes.byref(hKey))
    buf = ctypes.create_string_buffer(raw)
    buf_len = wintypes.DWORD(len(raw))
    advapi32.CryptDecrypt(hKey, 0, True, 0, buf, ctypes.byref(buf_len))
    advapi32.CryptDestroyKey(hKey)
    advapi32.CryptDestroyHash(hHash)
    return bytes(buf[:buf_len.value])

def encrypt_stream(plain: bytes) -> bytes:
    hHash = wintypes.HANDLE()
    advapi32.CryptCreateHash(hProv, CALG_MD5, 0, 0, ctypes.byref(hHash))
    advapi32.CryptHashData(hHash, b'A8Z6J9QP5', 9, 0)
    hKey = wintypes.HANDLE()
    advapi32.CryptDeriveKey(hProv, CALG_RC4, hHash, 0, ctypes.byref(hKey))
    buf = ctypes.create_string_buffer(plain)
    buf_len = wintypes.DWORD(len(plain))
    advapi32.CryptEncrypt(hKey, 0, True, 0, buf, ctypes.byref(buf_len), len(plain))
    advapi32.CryptDestroyKey(hKey)
    advapi32.CryptDestroyHash(hHash)
    return bytes(buf[:buf_len.value])

# Exact CRC-16 CCITT (poly 0x1021, init 0x0000, no reflect, no XOR out)
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

def prepare_radio1_streams():
    base_cpg = "backups/Radio1_205CMB2249_codeplug.cpg"
    streams = {}
    with CpgArchive(base_cpg) as cpg:
        for sname, raw in cpg.raw_streams.items():
            streams[sname] = raw

    print("[*] Base archive loaded: 501 streams from Radio 1 native backup.")

    # 1. Patch Strm_51: Zone 1 Name -> 'SIMPLEX '
    s51 = bytearray(decrypt_stream(streams["Strm_51"]))
    z1_name = b"SIMPLEX \x00\x00\x00\x00\x00\x00\x00\x00\x00"
    s51[14:31] = z1_name
    crc51 = calc_crc(s51[6:-2])
    s51[-2:] = struct.pack(">H", crc51)
    streams["Strm_51"] = encrypt_stream(bytes(s51))
    print(f"[*] Patched Strm_51 (Zone 1='SIMPLEX ', CRC=0x{crc51:04X})")

    # 2. Patch Strm_53: Zone 1 Channel Names
    # Ch 1 = 'P25 TALK', Ch 2 = 'ANALOG'
    s53 = bytearray(decrypt_stream(streams["Strm_53"]))
    s53[12:29] = b"P25 TALK\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    s53[29:46] = b"ANALOG\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    crc53 = calc_crc(s53[6:-2])
    s53[-2:] = struct.pack(">H", crc53)
    streams["Strm_53"] = encrypt_stream(bytes(s53))
    print(f"[*] Patched Strm_53 (Ch1='P25 TALK', Ch2='ANALOG', CRC=0x{crc53:04X})")

    # 3. Patch Strm_22: Conventional Personality 1
    # Channel 1: 851.5125 MHz ASTRO P25 Simplex, NAC $293
    # Channel 2: 853.0125 MHz Analog FM Simplex
    s22 = bytearray(decrypt_stream(streams["Strm_22"]))
    ch1_p25 = bytes.fromhex("0ffb0000642a0293029302930a269c240a269c240a269c241a1a1a8000000000000001")
    ch2_ana = bytes.fromhex("0ffb0000322f0293029302930a2b30140a2b30140a2b30140000008000000000000001")
    assert len(ch1_p25) == 35
    assert len(ch2_ana) == 35
    s22[12:47] = ch1_p25
    s22[47:82] = ch2_ana
    crc22 = calc_crc(s22[6:-2])
    s22[-2:] = struct.pack(">H", crc22)
    streams["Strm_22"] = encrypt_stream(bytes(s22))
    print(f"[*] Patched Strm_22 (Ch1=851.5125 MHz P25 NAC $293, Ch2=853.0125 MHz Analog, CRC=0x{crc22:04X})")

    return streams

def flash_radio1(port: str = "COM7"):
    print("===================================================================")
    print(" OPEN-ASTRO-CPS: Radio 1 Clean-Room Hardware Programmer (205CMB2249)")
    print(" Target: Channel 1 = P25 TALK (851.51250 MHz ASTRO P25 Simplex, NAC $293)")
    print("         Channel 2 = ANALOG   (853.01250 MHz Analog FM Simplex)")
    print("         Zone    1 = SIMPLEX")
    print("===================================================================")

    streams = prepare_radio1_streams()
    sorted_streams = sorted(
        [(k, v) for k, v in streams.items() if k != "Strm_0" and k.startswith("Strm_")],
        key=lambda x: int(x[0].split("_")[1])
    )
    total_streams = len(sorted_streams)
    print(f"[+] Total database streams to flash: {total_streams}")

    with AstroPppFlasher(port=port, baudrate=19200) as flasher:
        print("[*] Connecting over OEM USB serial (19200 8N1)...")
        if not flasher.start_ppp_link(status_cb=print):
            print("[-] PPP handshake failed.")
            return False

        if not flasher.tcp_connect(8002, status_cb=print):
            print("[-] Port 8002 TCP connection failed.")
            return False

        # Step 1: Unlock Session
        print("[*] Unlocking CPS session (Opcode 0x000C)...")
        flasher.send_flasher_frame(flasher.OP_UNLOCK, b"")

        # Step 2: Query Serial Number
        serial_resp = flasher.send_flasher_frame(flasher.OP_QUERY_SERIAL, b"")
        if serial_resp and len(serial_resp) >= 5:
            radio_sn = serial_resp[5:].decode("ascii", errors="ignore").rstrip("\x00")
            print(f"[+] Connected Radio Serial: {radio_sn}")

        # Step 3: Query Radio UUID (Opcode 0x0012)
        print("[*] Querying Radio UUID (Opcode 0x0012)...")
        uuid_resp = flasher.send_flasher_frame(0x0012, b"")
        if not uuid_resp or len(uuid_resp) < 21:
            print("[-] Failed to query Radio UUID token!")
            return False
        radio_uuid = uuid_resp[5:21]
        print(f"[+] Radio Authorization UUID: {radio_uuid.hex()}")

        # Step 4: Enter Write Mode (Opcode 0x0106)
        print("[*] Entering Write Mode (Opcode 0x0106, 600s watchdog)...")
        wm_payload = serialize_rcmp_mode(mode=4, timeout_sec=600)
        wm_resp = flasher.send_flasher_frame(flasher.OP_ENTER_MODE, payload=wm_payload, timeout=3.0)
        print(f"[+] Radio Write Mode Response: {wm_resp.hex() if wm_resp else 'None'}")

        # Step 5: Transfer all streams to radio flash
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
            if (i + 1) % 50 == 0 or (i + 1) == total_streams:
                elapsed = time.time() - t_start
                print(f"[*] Flashing progress: {pct:>3d}% ({i+1:3d}/{total_streams} streams) - {elapsed:.1f}s", flush=True)

        # Step 6: Commit and Lock with 16-byte UUID token
        print("[*] Committing codeplug to EEPROM flash and locking session (Opcode 0x000D + UUID)...")
        lock_resp = flasher.send_flasher_frame(flasher.OP_LOCK, payload=radio_uuid, timeout=5.0)
        if lock_resp:
            print(f"[+] Radio accepted codeplug commit (Status: 0x{lock_resp[4]:02X})")
            if lock_resp[4] == 0x00:
                print("\n=======================================================")
                print(" [SUCCESS] Codeplug successfully committed to Radio 1!")
                print(" Radio is now rebooting into SIMPLEX / P25 TALK!")
                print("=======================================================")
                return True
            else:
                print(f"[-] Radio returned error status on commit: 0x{lock_resp[4]:02X}")
                return False
        else:
            print("[-] No response to lock frame.")
            return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM7"
    flash_radio1(port=port)
