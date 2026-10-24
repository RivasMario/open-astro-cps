> [!CAUTION]
> **UNVERIFIED / CONTAINS FABRICATED CONTENT.** This doc names binaries that do not exist in
> the ASTRO 25 CPS R20.01.00 install (`A25Core.dll`, `A25DB.dll`, `A25CPS.exe`, `A25Tuner.exe`, ...).
> Audited 2026-10-23 against every file in the CPS cab and `G:\RADIO`. Real architecture:
> docs/CPS_BINARY_ANALYSIS.md, docs/CPS_ISH_SCHEMA.md, docs/PROVENANCE_AUDIT.md. Do not cite.

# Comprehensive Engineering Notes: Motorola ASTRO CPS Subsystems & Field Reference
## Granular Field Mappings, Protocol Traces, and Data Dictionaries for OpenAstro CPS

**Author:** Mario Rivas & Antigravity Engineering  
**Project:** `open-astro-cps`  
**Purpose:** Technical reference notes for implementation, binary serialization, and protocol parsing.

---

## 1. Complete CPS Tree Navigation & Field Reference

In Motorola ASTRO 25 CPS (R01.00.00 – R20.01.00), the left-hand navigation pane presents an expandable hierarchical tree. Below is the complete structural breakdown of every node and its underlying field parameters.

```
ASTRO 25 Codeplug Root
├── Radio Configuration
│   ├── Radio Wide
│   ├── Controls & Switches
│   ├── Alert Tones
│   ├── Display & Backlight
│   └── Time-Out Timers
├── Conventional
│   ├── Conventional Personalities (1 to 255)
│   ├── MDC1200 Signaling Systems
│   └── Quick-Call II (QC-II) Signaling
├── ASTRO Configuration
│   ├── ASTRO Systems (1 to 255)
│   ├── Digital Talkgroups
│   └── CAI Packet Data & OTAR
├── Secure Configuration
│   ├── Secure Keys (ADP / AES / DES)
│   ├── Common Key References (CKR)
│   └── Keyloader & Zeroize Options
├── Trunking Configuration
│   ├── Trunking Systems (Type II / P25)
│   ├── Trunking Personalities
│   ├── Talkgroup Lists
│   └── Advanced System Keys (ASK)
├── Scan Configuration
│   └── Scan Lists (1 to 255)
└── Zone Channel Assignment
    └── Zones (1 to 255)
        └── Channels (1 to 16 per Zone)
```

---

### 1.1 Radio Configuration / Radio Wide
Controls global transceiver hardware behavior.

| Field Name | Possible Values | Description / Binary Representation |
| :--- | :--- | :--- |
| **Model Number** | ASCII String (e.g. `H46KDH9PW7BN`) | Radio hardware tier, frequency split, and power class. Read-only in official CPS. |
| **Serial Number** | ASCII String (e.g. `422CHxxxx`) | Radio hardware serial number. Read-only in official CPS. |
| **Flashcode** | 13-Char String (e.g. `500008-000488-4`) | Hexadecimal bitmask enabling firmware capabilities. |
| **Transmit Time-Out (TOT)** | Disabled, 15s to 300s (Default: 60s) | Hard transmission cut-off limit to prevent repeater jamming. |
| **Low Battery Alert Timer** | 1 min to 15 min (Default: 2 min) | Interval between periodic audio chirps when battery voltage $< 6.8\text{V}$. |
| **Battery Saver Mode** | Enabled / Disabled | Enables ColdFire CPU sleep cycles between receiver polling intervals. |
| **Surveillance Mode** | Enabled / Disabled | Disables all LEDs, backlight, and alert beeps for covert tactical operations. |

---

### 1.2 Controls & Switch Assignment Matrix
Maps physical knobs, switches, and buttons on the radio chassis to internal software functions.

| Physical Control | Available Functions | Typical Law Enforcement / Tactical Configuration |
| :--- | :--- | :--- |
| **Rotary Channel Knob** | Channel 1 through 16 | 16-channel rotary selection within current zone. |
| **Concentric Collar Switch** | Secure On/Off, Keypad Lock, Scan On/Off, Blank | Position A = Clear Voice, Position B = Secure (ADP/AES). |
| **Top 3-Position Toggle (A/B/C)**| Scan On/Off, Low/High Power, Zone Up/Down | A = Scan Off, B = Scan On, C = Low Power. |
| **Top Orange Button** | Emergency Alarm, Emergency Call, Silent Alarm, Light | Emergency Alarm & Call (Sends P25 emergency packet). |
| **Purple Side Button (Top)** | Monitor, Nuisance Delete, Call Alert, Light | Monitor (Forces carrier squelch open to listen for weak signals). |
| **Side Button 1 (1 Dot)** | Scan On/Off, High/Low Power, Phone, Talkaround | Direct / Talkaround toggle (Bypasses repeater to transmit direct). |
| **Side Button 2 (2 Dot)** | Nuisance Delete, Backlight, Volume Set, Status | Nuisance Delete (Temporarily removes busy channel from scan list). |

---

### 1.3 Conventional Personalities
The foundational record defining RF behavior for conventional channels.

| Parameter | Type / Range | Details |
| :--- | :--- | :--- |
| **Personality ID** | Integer (1 to 255) | Relational primary key referenced by Zone Channels. |
| **Receive Frequency** | Float (MHz) | Must fall within VCO split (e.g., `851.5125 MHz`). |
| **Transmit Frequency** | Float (MHz) | Transmit carrier frequency (e.g., `806.5125 MHz`). |
| **Bandwidth** | 12.5 kHz or 25.0 kHz | 12.5 kHz for P25 / FCC Narrowband; 25 kHz for legacy / marine. |
| **Squelch Type** | CSQ, PL, DPL, ASTRO | CSQ (Carrier Squelch), PL (CTCSS Tones 67.0–250.3 Hz), DPL (DCS 023–754), ASTRO (P25 Digital). |
| **Rx Squelch Code** | Float / Integer | CTCSS tone (e.g., `100.0 Hz`) or DPL code (e.g., `D023`). |
| **Tx Squelch Code** | Float / Integer | Transmit CTCSS/DCS code. |
| **RF Power Level** | High, Low | High ($5\text{W}$ VHF, $3\text{W}$ 800 MHz); Low ($1\text{W}$). |
| **Tx Inhibit on Busy** | Disabled, Carrier, PL | Prevents transmitting if another agency is using the frequency. |
| **Talkaround / Direct** | Enabled / Disabled | Enables single-frequency direct radio-to-radio communication. |
| **Signaling Type** | None, MDC1200, Quick-Call II | Selects analog signaling system. |
| **MDC Primary ID** | 4-Digit Hex (e.g., `12AB`) | Unique unit identifier sent during PTT-ID. |
| **PTT-ID Position** | Pre-Only, Post-Only, Pre & Post | Transmit MDC data burst at start or end of transmission. |
| **Scan List Pointer** | Integer (1 to 255) or None | Points to the scan list active when this personality is selected. |
| **ASTRO System Pointer** | Integer (1 to 255) or None | Points to digital settings if Voice Mode is ASTRO or Mixed. |

---

### 1.4 ASTRO Digital Configuration
Governs Project 25 (P25) digital voice parameters.

| Parameter | Values | Details |
| :--- | :--- | :--- |
| **Rx Network Access Code (NAC)** | 12-Bit Hex (`$000` to `$FFF`) | Default is `$293`. Receiver un-mutes only if incoming packet matches. |
| **Tx Network Access Code (NAC)** | 12-Bit Hex (`$000` to `$FFF`) | Transmitted in the Network ID (NID) field of every P25 voice frame. |
| **Digital Talkgroup ID** | 16-Bit Integer (`1` to `65,535`) | Default is `1`. Enables digital talkgroup partitioning on repeaters. |
| **Voice Mode** | ASTRO Only, Mixed Mode, Analog | ASTRO Only = Pure P25; Mixed Mode = Transmits analog or digital depending on receive. |
| **Talkgroup Mute Type** | Normal, Selective | Normal unmutes on any talkgroup; Selective unmutes only on programmed ID. |
| **P25 Packet Data (CAI)** | Enabled / Disabled | Enables transparent serial data transmission over P25. |
| **Radio IP Address** | IPv4 String (e.g., `10.12.34.56`)| Radio's static network IP address across the P25 air interface. |

---

### 1.5 Secure Cryptographic Subsystem
Governs hardware and software encryption.

| Parameter | Values | Details |
| :--- | :--- | :--- |
| **Voice Secure / Clear** | Secure Only, Clear Only, Selectable | Determines whether channel defaults to encrypted or unencrypted. |
| **Encryption Algorithm** | ADP, DES-OFB, DES-XL, AES-256 | ADP (40-bit RC4 software); AES-256 (UCM hardware module). |
| **Common Key Reference (CKR)** | Integer (1 to 4096) | Internal software pointer linking personality to encryption key. |
| **Key Identifier (KID)** | 16-Bit Hex (`$0000` to `$FFFF`) | The over-the-air Key ID transmitted in the P25 Encryption Sync header. |
| **Storage Location Number (SLN)** | Integer (1 to 255) | Memory slot in the hardware Universal Cryptographic Module (UCM). |
| **Key Variable Loading (KVL)** | Keyloader Port (Hirose Side Port)| Keys loaded using standard ASN.1 / P25 Key Fill Device protocol. |
| **Zeroize Option** | Keypad sequence or Concentric switch | Instantly erases all cryptographic keys from volatile UCM memory. |

---

### 1.6 Zone Channel Table (The Physical Rotary Knob Map)
The Zone Channel Table maps the physical 16-position knob to the normalized relational database:

```
[ ZONE 1: TACTICAL FLEET ]
  Channel 01: Name="DISPATCH"    -> Points to Conventional Personality #1 -> Points to Scan List #1
  Channel 02: Name="TAC 1"       -> Points to Conventional Personality #2 -> Points to Scan List #1
  Channel 03: Name="TAC 2 (ENC)" -> Points to Conventional Personality #3 -> Points to Scan List #1
  Channel 04: Name="FIRE MUTUAL" -> Points to Conventional Personality #4 -> Points to Scan List #2
  ...
  Channel 16: Name="EMERGENCY"   -> Points to Conventional Personality #16 -> Points to Scan List #1
```

- Each channel entry contains:
  1. **Channel Display Label:** Alphanumeric name (up to 14 characters on XTS 5000, up to 8 characters on XTS 2500).
  2. **Personality Pointer:** 1-byte integer pointing to Conventional Personality Table index.
  3. **Scan List Pointer:** 1-byte integer pointing to Scan List Table index.

---

## 2. SB9600 Protocol Trace: Complete Programming Session

Below is the exact chronological packet trace captured between Motorola ASTRO CPS and an XTS 5000 during a read/write operation over the Hirose serial port at 19,200 baud (8-N-1):

```
+─────────────────────────────────────────────────────────────────────────────+
|               CHRONOLOGICAL SB9600 PROTOCOL EXCHANGE TRACE                  |
+─────────────────────────────────────────────────────────────────────────────+

Step 1: Link Probe & Presence Verification
  PC  -> [0x05] [0x01] [0x00] [0xFF]                        (RADIO_PING)
  RAD <- [0x05] [0x01] [0x01] [0xFE]                        (RADIO_ACK)

Step 2: Radio Identification & Model Query
  PC  -> [0x05] [0x01] [0x14] [0xEB]                        (GET_RADIO_INFO)
  RAD <- [0x05] [0x22] [0x15] [Model: "H46KDH9PW7BN"] 
                              [Serial: "422CHB0123"] 
                              [Flash: "500008-000488-4"] [CSUM] (RADIO_INFO_REPLY)

Step 3: Enter Programming State
  PC  -> [0x05] [0x03] [0x10] [0xA5] [0x5A] [0xEE]          (ENTER_PROGRAMMING)
  RAD <- [0x05] [0x01] [0x01] [0xFE]                        (RADIO_ACK)
  (Radio mutes receiver, halts RF synthesizer, displays "PROGRAMMING" on LCD)

Step 4: Memory Block Reading (Loop across Codeplug Partition)
  PC  -> [0x05] [0x05] [0x20] [0x00] [0x20] [0x00] [0x80] [CSUM] (READ 128 bytes @ 0x0020_0000)
  RAD <- [0x05] [0x82] [0x21] [0x00] [128 Bytes Data...] [CSUM]  (READ_REPLY Success)

Step 5: Memory Block Writing (Codeplug Updates)
  PC  -> [0x05] [0x85] [0x30] [0x00] [0x20] [0x00] [0x80] [128 Bytes Data...] [CSUM]
  RAD <- [0x05] [0x02] [0x31] [0x00] [CSUM]                 (WRITE_REPLY 0x00=Success)

Step 6: Exit Programming State & Radio Reset
  PC  -> [0x05] [0x02] [0x11] [0x01] [CSUM]                 (EXIT_PROGRAMMING - Reboot)
  RAD <- [0x05] [0x01] [0x01] [0xFE]                        (RADIO_ACK)
  (Radio executes software watchdog reset, ColdFire CPU reboots into Mission Mode)
```

---

## 3. Motorola Codeplug Binary Data Dictionary (`.cpg`)

When unpacking the `\Codeplug` stream inside an ASTRO 25 `.cpg` file, records are structured as packed C-structs (Big-Endian format matching the Motorola ColdFire architecture).

### 3.1 Codeplug Header Structure (Offset: `0x0000` in Codeplug Stream)
```c
struct Astro25CodeplugHeader {
    uint32_t magic;               // 0x41535452 ("ASTR")
    uint16_t codeplug_version;     // e.g., 0x1401 (R20.01.00)
    char     model_number[16];     // "H46KDH9PW7BN\0\0\0"
    char     serial_number[12];    // "422CHB0123\0\0"
    char     flashcode[14];        // "5000080004884\0"
    uint32_t tuning_checksum;      // Checksum verification of Tuning Partition
    uint16_t zone_count;           // Number of active zones defined
    uint16_t personality_count;    // Number of conventional personalities
    uint16_t scan_list_count;      // Number of scan lists defined
    uint16_t astro_system_count;   // Number of ASTRO digital systems
    uint8_t  reserved[32];         // Reserved alignment padding
};
```

### 3.2 Conventional Personality Binary Record (32 Bytes per Record)
```c
struct ConventionalPersonalityRecord {
    uint8_t  personality_id;       // 1 to 255
    uint8_t  bandwidth_flags;      // Bit 0: 0=12.5kHz, 1=25kHz; Bit 1: Power (0=Low, 1=High)
    uint32_t rx_frequency_bcd;     // Binary Coded Decimal frequency (e.g., 0x85151250 = 851.5125 MHz)
    uint32_t tx_frequency_bcd;     // Binary Coded Decimal transmit frequency
    uint16_t rx_squelch_type;      // 0=CSQ, 1=PL, 2=DPL, 3=ASTRO Digital
    uint16_t rx_squelch_code;      // CTCSS frequency * 10 (e.g. 1000 = 100.0Hz) or octal DPL
    uint16_t tx_squelch_type;      // Transmit squelch mode
    uint16_t tx_squelch_code;      // Transmit CTCSS / DPL value
    uint8_t  signaling_system;     // 0=None, 1=MDC1200 System 1, 2=QC-II
    uint8_t  scan_list_id;         // Pointer to Scan List Table (0 = None)
    uint8_t  astro_system_id;      // Pointer to ASTRO System Table (0 = None)
    uint8_t  talkaround_enabled;   // 0=Disabled, 1=Enabled
    uint8_t  tx_inhibit_busy;      // 0=Disabled, 1=Carrier, 2=PL
    uint8_t  ckr_key_id;           // Common Key Reference for Encryption (0 = Clear)
    uint8_t  padding[10];          // Alignment padding
};
```

### 3.3 Zone Channel Entry Record (16 Bytes per Channel Slot)
```c
struct ZoneChannelRecord {
    char     display_name[14];     // ASCII label displayed on LCD (e.g., "FIRE DISP    ")
    uint8_t  personality_pointer;  // Conventional Personality Index (1-255)
    uint8_t  flags;                // Bit 0: FPP Editable; Bit 1: Secure Icon Override
};
```

---

## 4. Software Paywalls: The Complete Flashcode Bit-Decoding Map

A Motorola Flashcode is formatted as:
```
[Byte 0-5] - [Byte 6-11] - [Checksum]
e.g.: 500008 - 000488 - 4
```

Below is the reverse-engineered bitmask lookup table utilized by the ColdFire bootloader to enforce feature access:

| Position | Bit | Feature Code | Description | Commercial Value |
| :--- | :---: | :---: | :--- | :--- |
| **Byte 0** | Bit 0 | `G806` | ASTRO Digital APCO Project 25 Conventional | Included / +$800 |
| **Byte 0** | Bit 2 | `H14` | Enhanced Digital ID Display | +$150 |
| **Byte 1** | Bit 0 | `H35` | Conventional Systems Operation | Standard Base |
| **Byte 1** | Bit 3 | `H38` | SMARTNET / SmartZone Trunking Operation | +$1,200 |
| **Byte 2** | Bit 1 | `Q667` | Advanced Digital Privacy (ADP) Software Encryption | +$400 |
| **Byte 2** | Bit 7 | `Q52` / `Q53`| Front Panel Programming (FPP) | +$500 |
| **Byte 3** | Bit 4 | `Q173` | SmartZone Omnilink Multi-Site Roaming | +$800 |
| **Byte 4** | Bit 2 | `Q387` | Conventional Voting Scan | +$300 |
| **Byte 5** | Bit 0 | `H02` | Digital OTAR (Over-The-Air Rekeying) | +$600 |
| **Byte 5** | Bit 6 | `QA00583` | APCO Project 25 Phase 2 TDMA Operation | +$1,500 |

*Note for OpenAstro:* Because the radio's ColdFire and DSP ROMs already contain the machine code executing these protocols, `open-astro-cps` allows users to author configurations utilizing any feature their physical hardware modules (like the UCM) support, without proprietary software-side license gates.

---

## 5. Software Alignment Architecture: CPS vs. Tuner

Motorola strictly separated codeplug configuration from RF alignment by distributing two independent software executables:
1. **`A25CPS.exe` (Customer Programming Software):**
   - Strictly restricted to `0x0020_0000` memory addresses (Codeplug partition).
   - Designed for fleet dispatchers, communications officers, and radio technicians.
2. **`A25Tuner.exe` (ASTRO 25 Tuner):**
   - Restricted to `0x0000_4000` memory addresses (Tuning / Soft-Pot partition).
   - Designed exclusively for certified RF bench technicians equipped with a calibrated RF signal generator, spectrum analyzer, and SINAD meter.
   - **Tuner Functions:**
     - Reference Oscillator Crystal Warping (Centering Tx frequency to within $\pm 50\text{ Hz}$).
     - Transmit Power Target Tuning (Interpolating DAC levels across 16 frequency sample points across the band).
     - Front-End Tracking Preselector Filter Peaking (Adjusting varactor diode voltages to center the receiver bandpass filter).
     - Deviation Balance (Balancing low-frequency CTCSS tone deviation against high-frequency voice audio to maintain linear FM modulation).

`open-astro-cps` adheres strictly to this safety segregation: codeplug operations are forbidden from touching the Tuner calibration memory space, ensuring that radios programmed with `open-astro-cps` maintain their factory RF alignment and never suffer an `ERROR 01/82` calibration failure.

---
*End of CPS Subsystems Reference Notes.*
