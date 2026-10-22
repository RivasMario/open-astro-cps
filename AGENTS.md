# OpenAstro CPS - Agent & Hardware Engineering Guide

This document establishes persistent hardware protocols, reverse-engineering discoveries, and development standards for AI coding agents working on **OpenAstro CPS**.

---

## 1. Motorola ASTRO 25 Hardware & Serial Lifecycle

### A. Power-Cycle & Reset Behavior
* **SBEP / Binary Mode Drop**: When the radio is commanded into SBEP binary mode (`AT#SBEP`) or raw memory transfers, the ASCII AT command parser is unhooked. If the link does not exit cleanly, serial reads will return empty bytes (`b''`).
* **Hardware Recovery**: **Turning the top volume knob OFF for 2 seconds and back ON** reboots the radio MCU, restoring factory UART defaults (`19200 8N1`, answering `AT\r` with `\r\nOK\r\n`).
* **Deterministic PPP Teardown**: Never terminate PPP abruptly. Always use the Hayes escape sequence:
  ```
  1.1s pause -> '+++' -> 1.1s pause -> 'ATH\r' -> 'AT#DATLCL=0\r'
  ```
  This cleanly reattaches the AT parser without requiring a power cycle.

---

## 2. Protocol & Network Architecture (XTS 2500 / 5000 / PRC-153)

### A. PPP / IP Negotiation over OEM USB (`0CAD:1001`)
* **Handshake Sequence**:
  1. `AT#DATLCL=1\r`
  2. `ATD\r` $\rightarrow$ **Wait explicitly for `\r\nOK\r\n\r\nCONNECT\r\n`** before sending any PPP frames.
  3. **RFC 1661 LCP (`0xC021`)**:
     * Send Configure-Request (ID 1, payload empty).
     * Receive radio's Configure-Ack + radio's Configure-Request with options (ACCM, Magic Number, PFC, ACFC).
     * Send Configure-Ack back to radio with the identical options block.
  4. **IPCP (`0x8021`)**:
     * Send Configure-Request with IP option `0x03, 0x06, 192.168.128.2`.
     * Receive radio's Configure-Request with radio IP `192.168.128.1`.
     * Send Configure-Ack back to radio.

### B. Listening Endpoints on `192.168.128.1`
* **TCP Port 8010**: Interactive Radio Debugger (TELNET interface).
  * Banner: `Welcome to Radio Debugger (TCP/IP)`
  * Commands: `VER`, `HELP`, `DSP:DUMP`, `MDCCALLID:WRITE`, `ERGO:...`
* **TCP Port 8002**: Motorola ASTRO 25 Control & Programming Daemon.
  * Opcodes (16-bit): `0x8002` (Session Init), `0x8011` (Read Memory Block), `0x8012` (Write Block), `0x7373` (Sync/ACK).
  * Framing: LEB128 variable-length integer encoding (`Write7BitEncodedInt`).

---

## 3. Codeplug Binary Format (`.cpg`)

* **Container**: Microsoft Compound File Binary (OLE2 Structured Storage).
* **Root Streams**:
  * `AdkFileHeader`: Stores radio model (offset 28), serial number (offset 48), agency archive tag (offset 570), and software notice.
  * `DataStg/Strm_*`: 100–500 relational record streams storing channel parameters, zones, scan lists, and softpot tuning values.
* **Stream Cipher (`fhAdk10c.dll` / `CFhAdkEncrypt`)**:
  * Pseudo-Random Generator (Linear Congruential Generator):
    ```python
    def lcg_next(seed: int) -> int:
        return ((seed * 85) + 25) & 0xFF
    ```
  * Header bytes 5, 6, 7 compute seed: `seed = ((b5 + b6) - b7) & 0xFF`.
  * Byte `0x1B` is the escape delimiter.
