# Motorola ASTRO 25 Radio Protocols & Flashing Ground Truth (Fedora / Linux Reference)

This document contains the complete, reverse-engineered technical specifications for communicating with, reading, and programming Motorola ASTRO 25 radios (XTS 1500, XTS 2500, XTS 5000, MT 1500, PM 1500, XTL 2500, XTL 5000) using 100% clean-room pure Python without Motorola CPS, Depot, or Windows dependencies.

---

## 1. Physical Transport & Device Detection on Fedora Linux

### Native USB Radios (XTS 1500 / 2500 / MT 1500)
- The radio side-connector contains a native Cypress USB controller (`0CAD:1001` - Motorola CGISS).
- When connected via OEM cable (RKN4105 / RKN4106 / ribless USB), Linux enumerates the radio as a **USB CDC-ACM Modem**:
  ```
  idVendor  0x0CAD  Motorola CGISS
  idProduct 0x1001  MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO
  ```
- Kernel driver: `cdc_acm` exposes `/dev/ttyACM0` (permissions: `root:dialout 0660`).
- Setup on Fedora:
  ```bash
  sudo usermod -aG dialout $USER
  # or copy udev rule:
  sudo cp scripts/99-openastro.rules /etc/udev/rules.d/
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```
- Serial Parameters: `19200` baud, `8N1`, `DTR=True`, `RTS=True`.

---

## 2. Point-to-Point Protocol (PPP) & IPCP Link Setup

The radio runs a VxWorks / pSOS RTOS with an embedded TCP/IP stack. Flash transfer is performed over IP, not raw serial.

### Step 1: Hayes AT Modem Handshake
1. Ping radio modem:
   ```
   TX: \rAT\r
   RX: \r\nOK\r\n
   ```
2. Request Local Data Mode:
   ```
   TX: AT#DATLCL=1\r
   RX: \r\nOK\r\n
   ```
3. Dial data connection:
   ```
   TX: ATD\r
   RX: \r\nCONNECT\r\n
   ```
4. *Clean Exit Guard Time*: If aborting, wait 1.1s silent guard time, send `+++`, wait 1.1s, send `ATH\r`, and `AT#DATLCL=0\r`.

### Step 2: RFC 1661 / RFC 1662 PPP Negotiation
- Framing: HDLC byte-stuffing with `0x7E` flag delimiters.
  - Escape character: `0x7D`.
  - Bytes `< 0x20`, `0x7E`, and `0x7D` are escaped with `0x7D (b ^ 0x20)`.
  - Frame Check Sequence: RFC 1661 FCS-16 (CRC-CCITT across unescaped payload).
- **LCP (Protocol `0xC021`)**:
  - Host sends Configure-Request (`Code=1, ID=1`).
  - Radio responds with Conf-Ack and sends its own Conf-Req.
  - Host acks Radio Conf-Req (`Code=2`).
- **IPCP (Protocol `0x8021`)**:
  - Host sends Configure-Request with IP Address option (`0x03, 0x06, 192, 168, 128, 2`).
  - Radio acks host IP and establishes:
    - Host IP: `192.168.128.2`
    - Radio IP: `192.168.128.1`

---

## 3. TCP Port 8002 & Native RCMP Flashing Protocol

The radio listens on two TCP ports:
- **Port 8002**: Motorola ASTRO 25 RCMP Flasher & Configuration Engine.
- **Port 8010**: Radio Debugger / Telemetry CLI (`VER`, `DUMP`, `ERGO`, `TSBK`).

Packets are encapsulated in standard IPv4 TCP frames (`src_port=40000..60000`, `dst_port=8002`) over PPP Protocol `0x0021`.

### RCMP Frame Structure
- Host request:
  ```
  [Length: 2 bytes BE] [Opcode: 2 bytes BE] [Payload: Length - 2 bytes]
  ```
- Radio response:
  ```
  [Length: 2 bytes BE] [Opcode: 2 bytes BE (0x8000 | Opcode)] [Status: 1 byte (0x00=OK)] [Payload...]
  ```

### Complete Opcode Table
| Opcode | Name | Direction | Payload | Description |
|---|---|---|---|---|
| `0x000C` | `OP_UNLOCK` | Host -> Radio | `b""` | Unlocks CPS session. Radio returns `Status 0x00`. |
| `0x0011` | `OP_QUERY_SERIAL` | Host -> Radio | `b""` | Radio returns ASCII serial number (e.g. `205CMB2249\x00`). |
| `0x0012` | `OP_QUERY_UUID` | Host -> Radio | `b""` | **CRITICAL**. Radio returns 16-byte internal authorization UUID (`resp[5:21]`). |
| `0x0106` | `OP_ENTER_MODE` | Host -> Radio | TLV: `01 [Mode:1B] 00 [Timeout:2B]` | Mode 4 = Write Mode, Mode 6 = Program Mode. Timeout in seconds (e.g. 600s). |
| `0x0100` | `OP_READ_ISH` | Host -> Radio | TLV ISH Read header | Read ISH record chunk (max 880 bytes). |
| `0x0101` | `OP_WRITE_ISH` | Host -> Radio | TLV ISH Write header + data | Writes ISH record chunk into partition `0x80` (max 880 bytes per chunk). |
| `0x000D` | `OP_LOCK` | Host -> Radio | **16-byte UUID token** | **CRITICAL COMMIT OPCODE**. Flushes RAM transactions to non-volatile EEPROM and reboots. |

### The `OP_LOCK` (0x000D) Authorization Breakthrough
Disassembled from `NextGen10.dll` at `0x10017D8C` and `0x1000C1EE`:
```x86asm
10017D8C: sub esp, 0x10          ; Allocate 16 bytes for UUID
10017D8F: lea esi, [ebp + 0x14]  ; Pointer to 16-byte UUID from Opcode 0x0012
10017D97: movsd ... (x4)         ; Copy 16 bytes to payload
10017D9E: push 0xd               ; OP_LOCK
10017DA2: call SendRcmpMessage
```
> [!IMPORTANT]
> If `OP_LOCK` is sent with an empty payload `b""`, the radio treats it as an unauthorized abort/cancel! It reboots without writing RAM changes to flash, reverting to the previous factory state (`VC KNT OUT OF RANGE`).
> When sent with the 16-byte UUID queried via Opcode `0x0012`, the radio returns `Status 0x00` and permanently commits the codeplug to non-volatile EEPROM!

---

## 4. Cryptographic Ground Truth (100% Pure Python)

### Master Session Key
Disassembled from `fhAdk10c.dll` at `0x10012018`:
```
Key = b"A8Z6J9QP5"
```

### Windows CryptoAPI Key Derivation Reversed
In Windows `Microsoft Base Cryptographic Provider v1.0`:
`CryptDeriveKey(CALG_RC4, CALG_MD5)` produces a 40-bit key with an 11-byte zero salt:
```python
import hashlib
# 5 bytes of MD5 + 11 zero bytes = exactly 16 bytes:
MASTER_RC4_KEY = hashlib.md5(b"A8Z6J9QP5").digest()[:5] + b"\x00" * 11
# Result: b"\x29\x26\x65\x82\x0D\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
```

### Pure Python RC4 Implementation
```python
def rc4_crypt(key: bytes, data: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = bytearray()
    for b in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i] + S[j]) % 256])
    return bytes(out)
```
This enables decrypting and encrypting all `Strm_*` relational database streams on Fedora Linux with 100% byte fidelity without Wine or Windows DLLs.

---

## 5. Relational CRC-16 Checksum Algorithm

Reverse-engineered from `cgIsh10c.dll` at `0x10007870` (`?cgIshCalculateChecksum@@YAHABVCByteArray@@AAG@Z`):
- **Algorithm**: CRC-16-CCITT
  - Polynomial: `0x1021` ($x^{16} + x^{12} + x^5 + 1$)
  - Initial value: `0x0000`
  - Input reflected: No
  - Result reflected: No
  - XOR output: `0x0000`
- **Scope**: Bytes `6` through `len - 2` (`decrypted[6:-2]`).
  - Skips 6-byte header `[Tag:2B][Index:2B][Length:2B]`.
  - Excludes the trailing 2-byte CRC.
- **Checksum location**: Last 2 bytes in big-endian (`decrypted[-2:]`).

```python
crc_table = []
for i in range(256):
    curr = i << 8
    for _ in range(8):
        curr = ((curr << 1) ^ 0x1021) & 0xFFFF if (curr & 0x8000) else (curr << 1) & 0xFFFF
    crc_table.append(curr)

def calc_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        idx = ((crc >> 8) ^ b) & 0xFF
        crc = ((crc << 8) ^ crc_table[idx]) & 0xFFFF
    return crc
```

---

## 6. Codeplug Relational Stream Layout

| Stream ID | Tag | Length | Role | Contents & Offsets |
|---|---|---|---|---|
| `Strm_0` | `0x1005` | 5002 B | Master OLE2 Directory | 500 entries $\times$ 10 bytes: `[Part:4B][CRC:2B][ID:2B][Type:2B]`. Radio rejects writing Item 0 (host archive only). |
| `Strm_2` | `0x000a` | 166 B | Radio Identity | Offset 8 = Serial Number (ASCII), Offset 19 = Model Number (ASCII). |
| `Strm_22` | `0x0ffd` | 364 B | Conventional Personality 1 | 10 channel records $\times$ 35 bytes each. Offset 12 = Ch 1, Offset 47 = Ch 2. |
| `Strm_36` | `0x0ffd` | 364 B | Mutual Aid Personality | Conventional 800 MHz channels (8CALL90, 8TAC91..94). |
| `Strm_41` | `0x0ffc` | 23 B | Zone 1 Definition | Points to Conventional Personality index `0000` (`Strm_22`). |
| `Strm_51` | `0x000d` | 186 B | Master Zone Names | 17 bytes per zone name. Offset 14 = Zone 1 name (`"SIMPLEX \x00..."`). |
| `Strm_52` | `0x0ffe` | 20 B | Zone 1 Assignment | Links Zone 1 to Channel Name stream `Strm_53`. |
| `Strm_53` | `0x0fff` | 286 B | Zone 1 Channel Names | 16 channels $\times$ 17 bytes each. Offset 12 = Ch 1 (`"P25 TALK\x00..."`), Offset 29 = Ch 2 (`"ANALOG\x00..."`). |

### 35-Byte Conventional Channel Sub-Record Structure
```
[Tag: 2B (0x0FFB)] [Index: 2B (0x0000)] [Flags: 2B (0x642A / 0x322F)]
[Rx NAC: 2B (0x0293)] [Tx NAC: 2B (0x0293)] [Unmute NAC: 2B (0x0293)]
[Rx Freq: 4B BE] [Tx Freq: 4B BE] [Tx Direct Freq: 4B BE]
[Mode Flags: 4B (0x1A1A1A80 = P25 Digital / 0x00000080 = Analog FM)]
[Padding: 7B (0x00000000000001)]
```

### Frequency Encoding
$$\text{StoredValue} = \frac{\text{Frequency in Hz}}{5}$$
- `851.51250 MHz` = $851,512,500 / 5 = 170,302,500 = \texttt{0x0A269C24}$
- `853.01250 MHz` = $853,012,500 / 5 = 170,602,500 = \texttt{0x0A2B3014}$

---

## 7. How to Flash from Fedora Linux

1. Connect the Motorola XTS 2500 via USB.
2. Verify port detection:
   ```bash
   ls -la /dev/ttyACM*
   # Should show: /dev/ttyACM0 (root:dialout)
   ```
3. Run the cleanroom programmer:
   ```bash
   python cleanroom_flasher/flash_radio1_simplex.py /dev/ttyACM0
   ```
4. The flasher will:
   - Connect over PPP and IPCP in < 1.5s.
   - Query the 16-byte UUID token via Opcode `0x0012`.
   - Write streams 1..500 into flash.
   - Commit via `OP_LOCK` with the UUID token.
   - Radio automatically reboots into **`SIMPLEX` / `P25 TALK`**!
