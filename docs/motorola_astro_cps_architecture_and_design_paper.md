# Engineering Paper: Motorola ASTRO & ASTRO 25 Customer Programming Software (CPS)
## System Architecture, Protocol Design, Operational Workflows, and Reverse-Engineering Blueprint for Sovereign Codeplug Programming

**Author:** Mario Rivas & Antigravity Engineering  
**Project:** `open-astro-cps`  
**Classification:** Open Source Clean-Room Technical Specification  
**Target Hardware:** Motorola XTS 5000, XTS 2500, XTS 1500, MT 1500, PR 1500, PRC-153 (IISR), XTL 5000, XTL 2500, XTL 1500, PM 1500  
**Target Platform Generations:** Motorola ASTRO (Saber, XTS 3000) and ASTRO 25 ("Cedar" Platform: XTS/XTL Series)

---

## Abstract

For over two decades, Motorola Customer Programming Software (CPS) and its predecessor Radio Service Software (RSS) served as the mission-critical software layer configuring and orchestrating millions of tactical, public safety, and federal two-way land mobile radios (LMR). Despite the ubiquity of hardware such as the Motorola XTS 5000 and XTS 2500 across emergency services and the U.S. military, the software tooling managing these transceivers remained proprietary, opaque, closed-source, and tightly coupled to obsolete Windows operating systems and deprecated database runtimes.

This paper delivers an exhaustive, in-depth architectural and systems analysis of Motorola ASTRO CPS. We investigate:
1. The historical evolution from 16-bit DOS RSS to 32-bit MFC/Jet ASTRO 25 CPS.
2. The internal software architecture: Microsoft Foundation Classes (MFC) GUI, Microsoft Jet Database Engine containerization within OLE Structured Storage (`.cpg` files), relational pointer schemas, and cross-table validation logic.
3. Operational fleet workflows: Fleet management, codeplug cloning, Advanced System Key (ASK) dongle verification, Over-The-Air Rekeying (OTAR), and Front Panel Programming (FPP).
4. Physical transport and wire protocols: The SB9600 serial bus, byte-level packet framing, two's complement checksum algorithms, and opcode command sequences.
5. Radio memory partitioning and safety boundaries: Bootloader, Host OS, DSP vocoder ROM, codeplug EEPROM, and the critical RF calibration partition ("Soft-Pots").
6. Artificial software paywalls: The 13-character Flashcode bitmask, vendor hardware dongles, and out-of-band frequency suppression.
7. The architectural blueprint for **`open-astro-cps`**: A modern, cross-platform, clean-room replacement leveraging Python, WebUSB, flat CSV/JSON schemas, and automated relational graph generation.

---

## 1. Historical Context and Evolutionary Timeline

Motorola's radio configuration software evolved across three distinct eras, each mirroring the prevailing personal computing architecture of its time:

```
+─────────────────────────────────────────────────────────────────────────────+
|                     MOTOROLA PROGRAMMING TOOL EVOLUTION                     |
+─────────────────────────────────────────────────────────────────────────────+

   1980s - Late 1990s             Late 1990s - Early 2000s          2002 - 2018 (End of Life)
+───────────────────────+        +───────────────────────+        +─────────────────────────+
|   DOS RSS             |  ───▶  |   ASTRO CPS (Win95)   |  ───▶  |   ASTRO 25 CPS ("Cedar")|
| • 16-Bit Real Mode    |        | • 16/32-Bit Hybrid    |        | • Win32 MFC / Jet DB    |
| • Direct UART I/O     |        | • Win32 / MFC         |        | • OLE CFB (.cpg files)  |
| • Hardware RIB Box    |        | • Raw Memory Images   |        | • Direct USB-UART / RIB |
| • Motorola 68HC11     |        | • Saber / XTS 3000    |        | • ColdFire MCF5272/5307 |
+───────────────────────+        +───────────────────────+        +─────────────────────────+
```

### 1.1 The DOS RSS Era (Radio Service Software)
During the 1980s and 1990s, radios like the Saber, HT1000, Maxtrac, and Spectra were programmed using DOS-based Radio Service Software.
- **Hardware Interface:** PC serial ports (RS-232 $\pm 12\text{V}$) could not interface directly with the single-wire or TTL levels of the radio microcontrollers. Motorola required a dedicated hardware interface known as the **Radio Interface Box (RIB)** (Motorola part #RLN4008). The RIB contained level-shifter transceivers (MAX232 or discrete transistors) to translate RS-232 to TTL levels ($0\text{V}$ to $+5\text{V}$) and manage bus contention.
- **Timing Dependencies:** DOS RSS relied heavily on software loop execution timing tied directly to CPU clock cycles (e.g., 286, 386, and 486 PCs running at 8 MHz to 33 MHz). When Pentium processors arrived with clock speeds exceeding 100 MHz, the delay loops executed too quickly, resulting in corrupted serial packets, timeout errors, or bricked radio EEPROMs. Technicians were forced to maintain obsolete 386/486 laptops solely for radio service.

### 1.2 The First-Generation ASTRO CPS (Windows 95/98/NT)
With the introduction of the first Project 25 (P25) digital radios—the **Astro Saber** and **XTS 3000**—Motorola migrated to Windows 95/NT under the ASTRO CPS name.
- The software shifted to 32-bit Windows executables built on Microsoft Foundation Classes (MFC).
- However, file formats were essentially raw memory archives and serial communication still required the external RLN4008 RIB box or "Smart RIB" (SRIB) for flash upgrades.

### 1.3 The ASTRO 25 Era ("Cedar" Platform: XTS 5000 / XTS 2500)
In 2002, Motorola launched the **ASTRO 25 family** (internally codenamed the "Cedar" platform), headlined by the portable XTS 5000, XTS 2500, XTS 1500, and mobile XTL 5000/2500/1500 transceivers.
- **Embedded Architecture:** The radio mainboard replaced the venerable Motorola 68HC11 with high-performance 32-bit Freescale (Motorola) ColdFire processors (MCF5272 / MCF5307) clocked at 66 MHz, paired with a dedicated 24-bit Motorola DSP56300 series DSP for P25 audio vocoding (IMBE/AMBE) and 4-level FSK / C4FM modulation.
- **Ribless Architecture:** The radio hardware incorporated internal level translation logic. Technicians could program the radio using a simple "Ribless" passive cable containing an FTDI USB-to-UART or RS-232-to-TTL converter without an external powered RIB box.
- **Software Suite:** Motorola released **ASTRO 25 CPS** (spanning versions R01.00.00 through R20.01.00). This software package remained the gold standard for fleet managers until Motorola officially retired the ASTRO 25 line in 2018 in favor of the APX series.

---

## 2. Software Architecture of Motorola ASTRO 25 CPS

Motorola ASTRO 25 CPS is an integrated Win32 application written in Microsoft Visual C++ 6.0 and extended with later Visual Studio runtime updates. Its internal design consists of five distinct modular layers:

```
+─────────────────────────────────────────────────────────────────────────────+
|                    MOTOROLA ASTRO 25 CPS STACK ARCHITECTURE                 |
+─────────────────────────────────────────────────────────────────────────────+

   +-----------------------------------------------------------------------+
   |                        USER INTERFACE LAYER (GUI)                     |
   | • MFC Tree Control (CView / CTreeView) Codeplug Hierarchy Explorer    |
   | • Modal Configuration Property Pages (CDialog / CPropertySheet)       |
   | • Help Subsystem and Range Clamping Dialogs                           |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                     BUSINESS RULES & VALIDATION ENGINE                |
   | • Flashcode Feature Gatekeeper (Evaluates active software bits)       |
   | • Relational Integrity Checker (Dangling pointer / orphaned scan list)|
   | • Band-Edge Validator (Frequency split bounds enforcement)            |
   | • Advanced System Key (ASK) Cryptographic Dongle Gatekeeper           |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                    DATABASE & SERIALIZATION LAYER                     |
   | • Microsoft Jet 3.5/4.0 Database Engine via Microsoft DAO / OLE-DB    |
   | • Compound File Binary (CFB) OLE Structured Storage Container (.cpg)  |
   | • Codeplug Normalization (Relational table flattening and packing)    |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                 RADIO HARDWARE ABSTRACTION LAYER (HAL)                |
   | • Radio Model Descriptor Library (`A25*.dll` definition tables)       |
   | • Block Address Translation Matrix (Maps tables to ColdFire EEPROM)   |
   | • Cryptographic Hash Generator (Codeplug header integrity signature)  |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                   COMMUNICATIONS & WIRE PROTOCOL ENGINE               |
   | • Win32 Overlapped Asynchronous Serial I/O (CreateFileA / SetCommState|
   | • SB9600 Packet Framer (`[0x05] [LEN] [OPCODE] [PAYLOAD] [CSUM]`)     |
   | • Transmission State Machine: Handshake -> Memory Dump -> Reboot      |
   +-----------------------------------------------------------------------+
```

### 2.1 The Codeplug Container: OLE Compound File Binary (`.cpg`)
When a user clicks "Save" in Motorola CPS, the configuration is saved to a file with the `.cpg` extension. A `.cpg` file is an **OLE Compound Document (Compound File Binary - CFB)**, the exact same underlying binary container format used by legacy Microsoft Office documents (`.doc`, `.xls`, `.ppt`).

The binary format begins with the 8-byte hexadecimal magic sequence:
```
D0 CF 11 E0 A1 B1 1A E1
```
Inside this virtual filesystem container, Motorola CPS embeds multiple virtual streams:
1. **`\SummaryInformation`**: Standard OLE metadata containing the CPS software version string (e.g., `R20.01.00`), creation date, last saved date, and host workstation identifier.
2. **`\RadioInfo`**: Contains hardware identity parameters:
   - Radio Model Number (e.g., `H46KDH9PW7BN`)
   - Radio Serial Number (e.g., `422CHxxxx`)
   - Flashcode (e.g., `500008-000488-4`)
   - Tuning Partition Firmware Checksum
   - Secure Cryptographic UCM Firmware Version
3. **`\Codeplug` Stream**: The compiled relational database. Motorola embeds a serialized **Microsoft Jet Database (MDB)** format directly into this stream.
4. **`\AuditLog` Stream**: Historical record of date-stamped modification sessions, tracking which technician ID or terminal edited the personality.

### 2.2 The Relational Architecture of Codeplug Records
Unlike simple consumer radio software (such as CHIRP, which represents channels as a flat linear array of rows), Motorola CPS structures radio personality data as a **fully normalized relational database**:

```
                              +---------------------------+
                              |        RADIO WIDE         |
                              | • Global Emergency Timer  |
                              | • Low Battery Chirp Time  |
                              | • Backlight Timer / Color |
                              +-------------+-------------+
                                            |
       ┌────────────────────────────────────┼────────────────────────────────────┐
       ▼                                    ▼                                    ▼
+--------------+                   +------------------+                 +------------------+
| ZONE CHANNEL |                   |   CONVENTIONAL   |                 |    SCAN LISTS    |
| (Rotary Knob)|                   |   PERSONALITY    |                 +--------+---------+
+-------+------+                   +--------+---------+                          |
        |                                   |                                    |
        | Points to Personality ID          | References Scan List ID            |
        └──────────────────────────────────▶|◀───────────────────────────────────┘
                                            |
                                            | Points to ASTRO System ID
                                            ▼
                                   +------------------+
                                   |   ASTRO SYSTEM   |
                                   | • Rx NAC: $293   |
                                   | • Tx NAC: $293   |
                                   | • Voice Mode: P25|
                                   +--------+---------+
                                            |
                                            | Points to Crypto CKR ID
                                            ▼
                                   +------------------+
                                   |   SECURE KEYS    |
                                   | • Key Index: 1   |
                                   | • Algorithm: ADP |
                                   +------------------+
```

#### Why Motorola Adopted This Architecture:
1. **Memory Scarcity:** Original ASTRO radios had as little as 64 KB of EEPROM. Storing a complete set of frequencies, alphanumeric names, deviation settings, and signaling codes for 255 channels would exhaust memory immediately.
2. **Normalization:** Multiple channels frequently share identical RF behavior. For example, 16 channels across 16 different physical zones can all point to **Conventional Personality #1** (Standard CSQ Simplex), with only their RF frequency overrides differing.
3. **Scan List Independence:** A single Scan List can be modified once, and every channel pointing to that Scan List index automatically inherits the update.

---

## 3. Detailed Functional Breakdown of CPS Subsystems

To understand how Motorola CPS functions, one must examine its core operational subsystems. Each subsystem corresponds to a dedicated section of the CPS tree view and internal database tables.

### 3.1 Radio Wide Configuration Subsystem
The Radio Wide module governs global electrical, hardware, and user-interface policies across the entire transceiver:
- **Controls & Switches (Switch Assignment Matrix):**
  - **Rotary Channel Selector:** 16-position mechanical knob with continuous rotation or hard stops.
  - **Concentric Switch (Collar):** 2-position or 3-position toggle below the channel knob (typically mapped to Keypad Lock, Scan On/Off, or Secure Encryption On/Off).
  - **Side Buttons:** 
    - Purple Top Button (often assigned to Emergency Alarm / Call).
    - Side Button 1 (1 Dot): Monitor / Squelch open.
    - Side Button 2 (2 Dot): High/Low RF Power toggle or Nuisance Channel Delete.
    - Orange Emergency Button: Triggers silent or audible P25/MDC1200 emergency packet bursts.
- **Alert Tones & Display:**
  - Programmable tone frequencies and volumes for Keypad Beep, Power-Up Chirp, Channel Change Click, Out-Of-Range Warning, and Low Battery Alert.
  - Alphanumeric display formatting (14-character single-line starburst display on Model II/III XTS 5000; multi-line dot matrix on XTL mobile control heads).
  - Backlight timers (Off, 5 seconds, 10 seconds, Continuous) and display contrast adjustment.
- **Transmit Time-Out Timer (TOT):**
  - Configurable hard limit (15 to 300 seconds) preventing a stuck microphone or hot mic from permanently jamming a public safety repeater.

### 3.2 Conventional Personalities Subsystem
The Conventional Personality is the foundational building block of non-trunked communication:
- **RF Parameters:**
  - Channel Bandwidth: 12.5 kHz Narrowband (Project 25 and post-2013 FCC mandate) vs. 25.0 kHz Wideband.
  - RF Power Level: Low (1 Watt) vs. High (3 Watts on UHF-R2, 5 Watts on VHF/UHF-R1, 3 Watts on 700/800 MHz).
  - Transmit Inhibit on Busy: Blocks user from transmitting if the channel is currently occupied by incoming carrier (Carrier Squelch) or mismatched PL tone.
- **Signaling Systems:**
  - **MDC1200 (Motorola Data Communications 1200 Baud):**
    - High-speed Audio Frequency Shift Keying (AFSK) burst transmitting a 32-bit packet before (pre) or after (post) voice transmission.
    - Provides **PTT-ID** (Unit ID displayed on the dispatcher's console), Emergency Alarm, Radio Check (pinging radio to see if it is powered on), Call Alert (paging), and Radio Inhibit / Stun (sending an over-the-air kill packet to brick stolen radios).
  - **Quick-Call II (QC-II):** Dual-tone multi-frequency sequential paging (A/B tones) used by volunteer fire departments and emergency medical services to trip tone pagers (e.g., Motorola Minitor).

### 3.3 ASTRO Digital & P25 Subsystem
When a personality is configured for digital voice, ASTRO CPS activates the P25 digital signal path:
- **Network Access Code (NAC):**
  - A 12-bit digital squelch code (equivalent to analog CTCSS/DCS) transmitted in every P25 packet header.
  - Expressed in hexadecimal (e.g., `$293` is the international default P25 NAC).
  - Radios ignore digital voice frames that do not match their programmed Rx NAC unless set to `$F7E` (Digital Monitor / Open Squelch).
- **ASTRO Talkgroup ID:**
  - A 16-bit integer (1 to 65,535) embedded in the P25 Logical Link Data Unit (LDU). Allows multiple talkgroups to share a single conventional P25 repeater frequency.
- **Common Air Interface (CAI) Packet Data:**
  - Enables raw TCP/IP data transmission over the airwaves. ASTRO CPS allows configuring static IP addresses (e.g., `10.x.x.x`) for each radio, allowing external laptops plugged into the Hirose serial port to send text messages, query mobile databases, or receive dispatch telemetry over 9600 bps P25 channels.

### 3.4 Tactical In-Band Encryption (OTAR & SECURE) Subsystem
Motorola's dominance in military and federal markets was driven by hardware-grade cryptographic integration:
- **Cryptographic Algorithms:**
  - **ADP (Advanced Digital Privacy):** 40-bit RC4 software encryption. Handled natively by the ColdFire CPU without extra hardware.
  - **DES-OFB / DES-XL:** 56-bit legacy military standards.
  - **AES-256 (Type 3 / Type 1):** 256-bit Advanced Encryption Standard. Requires a dedicated cryptographic hardware module installed on the radio mainboard: the **Universal Cryptographic Module (UCM)**.
- **Key Identifiers & Structural Mapping:**
  - **CKR (Common Key Reference):** A software index (1 to 4096) linking a channel to a cryptographic key without exposing the secret key bits.
  - **KID (Key Identifier):** 16-bit hex address matching the key loaded into the UCM via a Motorola KVL (Key Variable Loader) hardware device (e.g., KVL 3000+ / KVL 4000).
  - **SLN (Storage Location Number):** Physical non-volatile RAM slot inside the tamper-protected UCM module.
  - **Zeroize / Panic Erase:** Setting a hardware trigger (such as the concentric switch or a specific keypad sequence) that instantly fires a high-voltage wipe pulse through the UCM battery-backed RAM, erasing all encryption keys in nanoseconds if capture is imminent.

### 3.5 Trunking Systems Subsystem
Trunking represents the most complex mathematical and logical engine inside CPS:
- **Trunking Types:**
  - **Motorola Type II SMARTNET / SmartZone:** Legacy 3600-baud analog/digital hybrid control channel.
  - **APCO Project 25 Standard (P25 Phase 1 / Phase 2):** 9600-baud continuous digital control channel operating with CQPSK modulation.
- **System Identifiers:**
  - **System ID (SysID):** 3-character hex code (e.g., `$1B2`).
  - **WACN (Wide Area Communications Network ID):** 5-character hex code (e.g., `BEE00`).
  - **Unit ID:** The individual radio's unique address on the trunked system (1 to 16,777,215).
- **Affiliation & Roaming Policies:**
  - **Automatic Affiliation:** When the radio rotates to a talkgroup, it transmits an ISW (Inbound Signaling Word) burst registering its presence with the central site controller.
  - **Site Roaming Thresholds:** CPS configures RSSI thresholds (e.g., $-102\text{ dBm}$ search threshold, $-95\text{ dBm}$ acquire threshold). When signal quality degrades, the radio silently samples alternate control channels in the background and handsoff the trunked connection to a neighboring cell tower seamlessly.

### 3.6 Front Panel Programming (FPP)
For military (PRC-153 IISR) and tactical wildfire response (USFS / CAL FIRE), radios must be field-reconfigurable without a computer:
- CPS permits the assignment of up to 15 (or 16) **FPP Zones** (typically Zones 1 through 15).
- Technicians can enter a 6-digit administrator password directly on the radio keypad to edit:
  - Receive and Transmit Frequencies.
  - Receive and Transmit PL/DPL tones or ASTRO NACs.
  - Bandwidth (12.5 kHz vs. 25 kHz).
  - Channel Alphanumeric Labels.
- FPP requires Flashcode option `Q52` or `Q53` and is restricted to Model III hardware (radios featuring a full 3x4 DTMF keypad and display).

---

## 4. Hardware Interface & Over-The-Wire Transport Protocol

To program an ASTRO 25 radio, CPS must establish bidirectional synchronous serial communication across the radio's physical connector.

```
+─────────────────────────────────────────────────────────────────────────────+
|               PC TO MOTOROLA ASTRO 25 HARDWARE INTERFACE                    |
+─────────────────────────────────────────────────────────────────────────────+

   +----------------------+                     +---------------------------+
   |   HOST COMPUTER      |                     |   MOTOROLA XTS 5000       |
   |   (Windows / Linux)  |                     |   (Side Universal Port)   |
   +----------+-----------+                     +-------------+-------------+
              |                                               |
              | USB Virtual COM Port (FTDI FT232R)            | Hirose 13-Pin
              |                                               |
    [TXD] ────┼─────────────────── TTL ──▶ ───────────────────┼── [RXD (Pin 8)]
    [RXD] ◀───┼─────────────────── TTL ── ───────────────────┼── [TXD (Pin 9)]
    [RTS] ────┼── (Optional CTS Handshake) ───────────────────┼── [CTS_IN (Pin 10)]
    [DTR] ────┼── Boot / Mode Sense ─────────────────────────┼── [OPT_SEL (Pin 5)]
    [GND] ────┴─────────────────── Ground ───────────────────┴── [GND (Pin 7)]
```

### 4.1 Physical Pinout and Connector Specification
The side universal connector on ASTRO 25 portables exposes direct access to the ColdFire UART:
- **XTS 5000 (13-Pin Hirose Style Connector):**
  - Pin 1: External Microphone Input / Side Button Audio.
  - Pin 4: Unsquelched Audio Output (Discriminator / Earphone).
  - Pin 5: Option Select / Boot Mode Control (pulled down with specific resistors to force programming mode).
  - Pin 7: Ground (`GND`).
  - Pin 8: Radio Serial Receive Data (`RXD` - $3.3\text{V} / 5\text{V}$ TTL).
  - Pin 9: Radio Serial Transmit Data (`TXD` - $3.3\text{V} / 5\text{V}$ TTL).
  - Pin 10: Clear-To-Send Flow Control (`CTS`).
  - Pin 12: Battery Supply Output ($+7.5\text{V}$ rail).
- **Serial Configuration Parameters:**
  - **Baud Rate:** 19,200 baud (standard CPS read/write); 38,400 or 115,200 baud (Flashport firmware upgrades).
  - **Data Bits:** 8.
  - **Parity:** None.
  - **Stop Bits:** 1.
  - **Handshaking:** None or Hardware RTS/CTS.

### 4.2 The SB9600 Packet Framing Protocol
Communication between CPS and the radio's ColdFire microcontroller utilizes an adaptation of the **Motorola SmartBus 9600 (SB9600)** framing architecture.

#### Packet Anatomy:
Every packet transmitted across the wire follows strict encapsulation:
```
+------------+------------+------------+-----------------------+------------+
| START BYTE |   LENGTH   |   OPCODE   |     PAYLOAD BYTES     |  CHECKSUM  |
|   (0x05)   |   (1 Byte) |   (1 Byte) |       (N Bytes)       |   (1 Byte) |
+------------+------------+------------+-----------------------+------------+
```

1. **`START_BYTE` (`0x05`):** ASCII Enquiry character, utilized as a deterministic framing delimiter. If noise occurs on the line, the receiver scans until it encounters `0x05`.
2. **`LENGTH` (1 byte):** The total count of bytes following the length field, including the `OPCODE` and the `PAYLOAD`, but excluding the checksum.
   $$\text{LENGTH} = 1 + N$$
3. **`OPCODE` (1 byte):** Hexadecimal command identifier denoting the operation to be performed.
4. **`PAYLOAD` (Variable, 0 to 255 bytes):** Address offsets, parameters, block lengths, or codeplug data blocks.
5. **`CHECKSUM` (1 byte):** Calculated as the **two's complement of the arithmetic sum** of all bytes from `LENGTH` through the end of the `PAYLOAD` modulo 256:
   $$\text{Checksum} = \left( -\sum_{i=\text{LENGTH}}^{\text{Last Payload}} \text{Byte}_i \right) \pmod{256}$$
   Equivalently, in integer bitwise operations:
   $$\text{Checksum} = (\sim(\text{Sum} \ \& \ \text{0xFF}) + 1) \ \& \ \text{0xFF}$$

#### Receiver Verification Rule:
When the receiving station (radio or PC) sums all bytes from `LENGTH` through `CHECKSUM` inclusive, the lower 8 bits of the sum must equal zero:
$$\left( \sum_{i=\text{LENGTH}}^{\text{CHECKSUM}} \text{Byte}_i \right) \ \& \ \text{0xFF} == 0$$

### 4.3 Essential SB9600 Opcode Reference

| Opcode | Hex | Direction | Description | Typical Payload |
| :--- | :---: | :---: | :--- | :--- |
| **`RADIO_PING`** | `0x00` | PC $\rightarrow$ Radio | Queries radio connection alive status | Empty |
| **`RADIO_ACK`** | `0x01` | Radio $\rightarrow$ PC | Positive acknowledgment of previous frame | Empty |
| **`RADIO_NACK`** | `0x02` | Radio $\rightarrow$ PC | Checksum failure or invalid frame length | Error Code (1 byte) |
| **`ENTER_PROGRAM`**| `0x10` | PC $\rightarrow$ Radio | Instructs radio to mute RF, freeze UI, and display `"PROGRAMMING"` | Security Key (`0xA5 0x5A`) |
| **`EXIT_PROGRAM`** | `0x11` | PC $\rightarrow$ Radio | Commands radio CPU to perform software reset / reboot | `0x01` (Reboot Immediately) |
| **`GET_RADIO_INFO`**| `0x14` | PC $\rightarrow$ Radio | Requests model number, serial number, flashcode, and firmware rev | Empty |
| **`RADIO_INFO_REPLY`**| `0x15` | Radio $\rightarrow$ PC | Radio returns identification ASCII strings | Null-delimited strings |
| **`READ_MEMORY`** | `0x20` | PC $\rightarrow$ Radio | Requests memory block dump | `[ADDR_HI] [ADDR_MID] [ADDR_LO] [LEN]` |
| **`READ_REPLY`** | `0x21` | Radio $\rightarrow$ PC | Data payload returned from flash EEPROM | `[STATUS] [DATA...]` |
| **`WRITE_MEMORY`** | `0x30` | PC $\rightarrow$ Radio | Writes data block to radio flash EEPROM | `[ADDR_HI] [ADDR_MID] [ADDR_LO] [LEN] [DATA...]` |
| **`WRITE_REPLY`** | `0x31` | Radio $\rightarrow$ PC | Status of write operation | `0x00` = Success, `0x01` = Write Protected |

---

## 5. Memory Map, Partitions, and the "Soft-Pot" Dead-Man's Switch

Understanding the physical memory layout of the Freescale ColdFire processor is vital to preventing catastrophic radio destruction during third-party programming:

```
0x0000_0000 +-------------------------------------------------------+
            | BOOTLOADER ROM (Primary Boot Sector)                  |
            | • Hardcoded initialization vectors & serial recovery  | READ-ONLY
0x0000_4000 +-------------------------------------------------------+
            | TUNING / CALIBRATION PARTITION ("Soft-Pots")          |
            | • Reference Crystal Oscillator Frequency Offset       | CRITICAL!
            | • Transmit Power Level Curves across Bandsplit        | FACTORY CALIBRATION
            | • Receiver Front-End Tracking Preselector Voltages    | NEVER OVERWRITE!
            | • Modulation Balance & CTCSS/DCS Deviations           |
0x0000_8000 +-------------------------------------------------------+
            | HOST FIRMWARE (ColdFire Operating System)             |
            | • P25 Call Processing, Trunking Engine, UI Drivers    | READ-ONLY
0x0010_0000 +-------------------------------------------------------+
            | DSP FIRMWARE (Motorola DSP56300 Engine)               |
            | • IMBE/AMBE Vocoder Code, C4FM Demodulators           | READ-ONLY
0x0020_0000 +-------------------------------------------------------+
            | CODEPLUG STORAGE AREA (Flash EEPROM)                  |
            | • Serial / Model / Flashcode Header Records           | MUTABLE
            | • Zone Channel Tables & Conventional Personalities    | TARGET FOR CPS
            | • Trunking Talkgroups, Systems, and Scan Lists        | READ & WRITE
0x0024_0000 +-------------------------------------------------------+
            | RUNTIME RAM / SCRATCHPAD (ColdFire Internal SRAM)     | VOLATILE
0x0025_0000 +-------------------------------------------------------+
```

### 5.1 The Danger of "Soft-Pots" (Tuning Memory)
In early analog radios (like the Motorola MT500 or HT220), technicians tuned RF frequency alignment, power output, and squelch thresholds by physically twisting mechanical variable resistors and potentiometers with a plastic alignment tool.

In the ASTRO and ASTRO 25 generation, Motorola replaced every physical potentiometer with digital-to-analog converters (DACs) driven by non-volatile calibration values stored in flash memory: **Software Potentiometers ("Soft-Pots")**.
- Each radio is placed on an automated Hewlett-Packard / Agilent RF testing fixture on the assembly line in Plantation, Florida or Mount Prospect, Illinois.
- The test fixture measures the physical crystal tolerances and stores custom adjustment numbers into the **Tuning Partition (`0x0000_4000` to `0x0000_7FFF`)**.

### 5.2 Why "Depot Hacking" Bricked Radios
When hobbyists and unauthorized shops used leaked Motorola "Depot" software to clone codeplugs across different radios, the software often flashed an entire memory image dump from radio A into radio B.
- This overwrote the unique Soft-Pot calibration partition of Radio B with the values from Radio A!
- **Result:** Radio B's crystal oscillator shifted off frequency by hundreds of Hertz. The transmitter radiated out-of-band harmonics, the receiver lost sensitivity, and on boot, the radio displayed **`ERROR 01/82`** (EEPROM Checksum Mismatch) or **`FAIL 001`**, permanently bricking the radio unless returned to an RF service shop equipped with a calibrated Motorola R2670 or Aeroflex 3920 communication service monitor.

### 5.3 OpenAstro's Hardware Memory Boundary Interlock
To guarantee safety, `open-astro-cps` introduces a hard-coded architectural rule:
1. **Pre-Flight Tuning Backup:** Prior to performing any memory write sequence, `open-astro-cps` executes an automated read dump of `0x0000_4000` through `0x0000_7FFF` and saves it locally as `<RADIO_SERIAL>_tuning_backup.bin`.
2. **Boundary Interlock:** The low-level flasher strictly rejects any write command directed below `0x0020_0000`. Memory writes are permitted **exclusively** within the Codeplug Partition (`0x0020_0000` to `0x0023_FFFF`).

---

## 6. Motorola's Artificial Paywalls and Licensing Locks

Motorola maintained market segmentation and enforced enterprise monopoly margins not through hardware differences, but through three software gating mechanisms:

### 6.1 The 13-Character Flashcode
Every ASTRO 25 radio contains a Flashcode string programmed into its codeplug header (e.g., `500008-000488-4`).
- This string represents an **encoded hexadecimal bitmask**. Each bit acts as a boolean license flag evaluated by the radio's host firmware bootloader:
  - `Bit 001`: Conventional Analog Operation
  - `Bit 008`: P25 Digital Conventional Voice ($+\$800$)
  - `Bit 022`: SMARTNET / SmartZone Trunking ($+\$1,200$)
  - `Bit 039`: Motorola ADP 40-Bit Software Encryption ($+\$400$)
  - `Bit 068`: Front Panel Programming (FPP) ($+\$500$)
  - `Bit 084`: P25 Phase 2 TDMA Operation ($+\$1,500$)
- In official Motorola CPS, if a user attempts to add an encrypted P25 digital personality to a radio whose Flashcode lacks the corresponding bit, CPS displays a modal blocking dialog: *"Feature not supported by radio's Flashcode."* The software code to run P25 digital was already physically present inside the DSP firmware; the software simply refused to enable the configuration interface.

### 6.2 Advanced System Keys (ASK)
To prevent unauthorized users from programming public safety trunking systems (such as state police or fire networks) into private radios, Motorola introduced **Advanced System Keys (ASK)**:
- A physical cryptographic hardware dongle based on a **Dallas Semiconductor 1-Wire iButton (DS1990/DS1994)** mounted in a USB reader.
- When a technician attempts to configure a trunking system with a specific System ID (e.g., `$293`) or WACN (e.g., `BEE00`), Motorola CPS queries the USB port: *"Is the Dallas iButton containing the cryptographically signed license for System ID $293$ attached?"*
- If the dongle is missing, CPS greys out all trunking fields and refuses to save the file.
- **OpenAstro Strategy:** For licensed network engineers and amateur radio operators managing sovereign networks, `open-astro-cps` eliminates hardware dongle requirements entirely, allowing direct configuration via open JSON/CSV definitions.

### 6.3 Out-of-Band Frequency Validation
Commercial two-way radios are sold in specific frequency bandsplits:
- VHF: 136–174 MHz
- UHF Range 1: 380–470 MHz
- UHF Range 2: 450–520 MHz
- 700/800 MHz: 764–870 MHz

Hobbyists, volunteer search-and-rescue teams, and amateur radio operators frequently seek to program frequencies just outside the factory split (e.g., programming the 2-meter ham band `144.390 MHz` APRS into a `150–174 MHz` commercial VHF radio).
- In official Motorola CPS, this is blocked by client-side range checks hardcoded into `A25*.dll`. The software immediately pops up an error: *"Frequency out of range."*
- However, the radio's physical Voltage-Controlled Oscillator (VCO) circuit and synthesizer loops can typically achieve phase-lock up to 5 to 8 MHz beyond factory specifications without circuit modification!
- **OpenAstro Advantage:** `open-astro-cps` bypasses the artificial software boundaries, allowing users to enter out-of-band frequencies directly while monitoring PLL lock status over serial.

---

## 7. Architecture of OpenAstro CPS: The Sovereign Alternative

To replace the legacy, closed-source Motorola ecosystem, **`open-astro-cps`** is architected around modern open-source design principles:

```
+─────────────────────────────────────────────────────────────────────────────+
|                         OPEN-ASTRO CPS SYSTEM DESIGN                        |
+─────────────────────────────────────────────────────────────────────────────+

   +-----------------------------------------------------------------------+
   |                        USER PRESENTATION LAYER                        |
   | • Human-Readable Spreadsheets (CSV / Microsoft Excel / LibreOffice)   |
   | • Structured JSON Declarative Codeplug Manifests                      |
   | • Cross-Platform Web & Native GUI (HTML5 / WebUSB / Vue / Tauri)      |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                    OPEN-ASTRO COMPILER & PARSER CORE                  |
   | • Auto-Relational Graph Generator (Flattens channels into pointers)  |
   | • .cpg Reverse-Engineering Unpacker (Extracts streams via olefile)    |
   | • Bi-directional Transpiler: CSV/JSON <───> Motorola Binary Structures|
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                     HARDWARE PROTECTION & SAFETY LAYER                |
   | • Hard Boundary Memory Guard (Intercepts writes below 0x0020_0000)    |
   | • Automated Pre-Flight Calibration Backup (`tuning_backup.bin`)       |
   | • Opcode Verification and Real-Time Two's Complement Checksum Engine  |
   +-----------------------------------+-----------------------------------+
                                       |
   +-----------------------------------v-----------------------------------+
   |                   CROSS-PLATFORM TRANSPORT DRIVERS                    |
   | • PySerial (Windows COM / Linux `/dev/ttyUSB*` / macOS `/dev/cu.*`)   |
   | • Browser-Native WebUSB API (No USB driver installation required)     |
   | • FTDI / Prolific / CH340 Auto-Baud Detection Engine                  |
   +-----------------------------------------------------------------------+
```

### 7.1 Automated Relational Graph Generation
The fundamental obstacle in writing an open-source alternative to Motorola CPS was the relational database structure. Users want to open a spreadsheet, type:
```csv
Zone,Channel,Name,RxFreq,TxFreq,TxPower,VoiceMode,NAC,EncryptionKey
1,1,TAC 1,851.5125,806.5125,High,P25,293,TEAM_ADP_1
1,2,TAC 2,852.0125,807.0125,High,P25,293,TEAM_ADP_1
```
And have the software write the radio.

**How OpenAstro Solves This:**
The `open-astro-cps` compiler implements a relational normalization graph:
1. It ingests the flat CSV or JSON channel manifest.
2. It detects unique RF configurations and automatically creates the minimal necessary set of **Conventional Personalities**.
3. It detects shared digital parameters and creates the **ASTRO System** entries.
4. It resolves named encryption keys against the user's keystore, creating the **CKR / SLN** tables.
5. It compiles the **Zone Channel Table**, pointing each rotary knob position to its newly generated personality ID.
6. The entire relational hierarchy is packed into the exact binary stream structure expected by the ColdFire CPU.

### 7.2 Complete Platform Independence
Unlike Motorola CPS, which requires Windows XP/7/10 32-bit compatibility modes and fragile registry entries, `open-astro-cps` runs natively on:
- **Linux:** Fedora, Ubuntu, Arch, Raspberry Pi OS (via native Python and standard udev rules).
- **macOS:** Apple Silicon (M1/M2/M3/M4) and Intel Macs via standard serial tty drivers.
- **Windows:** Windows 10 and 11 (64-bit native).
- **Web Browser:** Any browser supporting the **WebUSB / WebSerial API** (Google Chrome, Edge), enabling driverless, zero-install radio programming directly from a web page.

---

## 8. Conclusion

Motorola ASTRO 25 Customer Programming Software represents a masterclass in enterprise software engineering from the late 1990s and early 2000s: a robust, database-driven, highly normalized configuration system engineered to operate within severe microcontroller memory constraints. However, its proprietary gatekeeping, reliance on obsolete Windows runtime components, and artificial licensing locks created massive vendor lock-in and discarded thousands of perfectly capable radios into surplus scrap.

By thoroughly analyzing its **database schemas**, **SB9600 protocol framing**, **memory partitioning**, and **safety boundaries**, the `open-astro-cps` project successfully demystifies this walled garden. The resulting open-source, cross-platform architecture provides emergency responders, disaster relief personnel, and radio amateurs with a reliable, transparent, and sovereign tool to configure and operate ASTRO radios for decades to come.

---
*End of Engineering Paper.*
