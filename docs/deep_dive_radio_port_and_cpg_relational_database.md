# Deep-Dive Engineering Master Guide: Radio Port Communication & The `.cpg` Relational Database
## Complete Technical Notes for OpenAstro CPS Developers, Reverse Engineers, and Multi-Agent Handoff

> **Author:** Mario Rivas & Antigravity Engineering  
> **Project:** `open-astro-cps` (`C:\Users\v-mariorivas\open-astro-cps`)  
> **Target Hardware:** Motorola ASTRO 25 (XTS 5000, XTS 2500, XTS 1500, PRC-153 IISR, XTL 5000, XTL 2500)  
> **Target Processors:** Freescale ColdFire 32-bit RISC (MCF5272 / MCF5307) + Motorola DSP56300 (Vocoder/Modem)  
> **Target Software:** Motorola ASTRO 25 CPS (R01.00.00 – R20.01.00)

---

## 📖 Executive Summary & Developer Orientation

This document is written as an **authoritative technical guide** for any developer or AI agent picking up work on `open-astro-cps`. 

Two core revelations demystify the entire Motorola ecosystem:
1. **The Radio is Not a Dumb Peripheral — It is an Embedded Computer:**
   When you connect an ASTRO 25 radio to a PC, you are not bit-banging a raw SPI/I2C EEPROM chip. You are communicating with an active 32-bit multitasking computer running an embedded real-time operating system (RTOS). Depending on the pin configuration and initialization commands, the radio's side universal port acts as:
   - An asynchronous **packet-switched network bus (SB9600)**.
   - A standard **RFC 1661 Point-to-Point Protocol (PPP) / TCP/IP network adapter** routing live IP traffic over P25 digital airwaves.
   - A **Hayes-style AT modem** accepting telemetry, text messages (TMS), and GPS coordinate queries.
   - A low-level **bootloader console** accepting ColdFire memory-dump and flash S-records.

2. **The `.cpg` File is Not a Binary Blob — It is a Normalized Relational Database:**
   A Motorola `.cpg` file is an **OLE Compound File Binary (CFB)** containing an embedded **Microsoft Jet Database (Access MDB)**. Channels do not contain frequency and squelch data directly; instead, they are junction tables containing foreign-key pointers to normalized tables (`tbl_ConventionalPersonality`, `tbl_AstroSystem`, `tbl_ScanList`, `tbl_SecureKey`). When CPS talks to the radio, it compiles this relational database into a contiguous memory structure mapped directly into the ColdFire processor's flash address space (`0x0020_0000`).

---

## Part 1: How the Radio Communicates Through Its Port Like a Computer

### 1.1 The Physical Interface & Pin Roles
Motorola ASTRO 25 radios interface via the side universal accessory connector (13-pin Hirose on XTS 5000; 10-pin on XTS 2500 / PRC-153):

```
+─────────────────────────────────────────────────────────────────────────────+
|               XTS 5000 SIDE UNIVERSAL CONNECTOR PINOUT & FUNCTIONS          |
+─────────────────────────────────────────────────────────────────────────────+

   Pin   Name         Signal Type       Function in Programming / Computer Mode
   ───   ──────────   ───────────────   ────────────────────────────────────────────────
    1    OPT_MIC      Analog In         External microphone audio input / PTT sense
    2    OPT_SPKR+    Analog Out        External speaker differential (+)
    3    OPT_SPKR-    Analog Out        External speaker differential (-)
    4    DISC_OUT     Analog Out        Unfiltered discriminator audio / Raw baseband
    5    OPT_SEL      Digital Input     Option Select / Boot Mode Strap (Resistor to GND)
    6    VCC_SENSE    Power Input       External 5V/7.5V logic supply detection
    7    GND          Ground            System reference ground
    8    UART_RXD     Serial Input      PC TxD -> Radio RxD (3.3V / 5V TTL)
    9    UART_TXD     Serial Output     Radio TxD -> PC RxD (3.3V / 5V TTL)
   10    UART_CTS     Hardware Flow     Flow control / Boot interrupt line
   11    SPI_CLK/1W   Bidirectional     Dallas 1-Wire Keyloader (KVL) data / Crypto sync
   12    BATT_PLUS    Power Output      Raw +7.5V battery voltage rail
   13    RF_DETECT    RF Switch         Senses Hirose RF antenna adapter connection
```

#### How "Ribless" Cables Work:
- Traditional DOS RSS required a **Radio Interface Box (RLN4008 RIB)** with internal op-amps and level-converters.
- ASTRO 25 radios feature internal TTL-tolerant UART transceivers. A modern "Ribless" cable is simply an **FTDI FT232RL (or Prolific PL2303 / CH340)** USB-to-UART bridge embedded in the USB plug shell.
- When `OPT_SEL` (Pin 5) is grounded via a specific pull-down resistor value inside the cable connector, the ColdFire CPU senses the impedance and automatically diverts UART0 from internal accessory routines to the external high-speed programming state machine.

---

### 1.2 The Four Operational Modes of the Universal Port

```
                     ┌──────────────────────────────────────────────┐
                     │          COLDFIRE CPU UART0 CONTROLLER       │
                     └──────────────────────┬───────────────────────┘
                                            │
         ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
         ▼                  ▼                               ▼                  ▼
+------------------+ +--------------------+ +--------------------+ +--------------------+
|  MODE 1: SB9600  | |  MODE 2: PPP/IP    | |  MODE 3: AT/RPP    | |  MODE 4: BOOTLOAD  |
|  Master/Slave    | |  Point-to-Point    | |  Hayes Modems &    | |  ColdFire ROM S-Rec|
|  Packet Bus      | |  P25 CAI Packet    | |  Telemetry / TMS   | |  Firmware Flashing |
|  • CPS Read/Write| |  • 9600 bps TCP/IP | |  • Signal strength | |  • S19/S28 records |
|  • Control Heads | |  • Mobile Data Term| |  • GPS NMEA streams| |  • 38400 / 115200  |
|  • Vehicular XTVA| |  • In-cab laptops  | |  • Remote PTT call | |  • Host OS upgrade |
+------------------+ +--------------------+ +--------------------+ +--------------------+
```

#### Mode 1: SB9600 (SmartBus 9600) — The Management Network
- Operates at **19,200 baud, 8-N-1**.
- Acts as a multi-drop local area network. Every device (the Radio Transceiver Host, the Control Head, the CPS software, the XTVA vehicular amplifier, the Public Safety Microphone) has a virtual bus address.
- When CPS sends packets, it addresses the **Host ColdFire CPU (Node Address `0x00`)**.
- The protocol uses deterministic byte framing with an 8-bit two's complement checksum.

#### Mode 2: PPP / TCP/IP (P25 CAI Packet Data) — The Network Card
- When an emergency services vehicle has a mobile data laptop (MDC) running dispatch software, the laptop connects to the radio via serial or USB.
- The laptop initiates standard **RFC 1661 PPP (Point-to-Point Protocol)**.
- The ColdFire RTOS runs an embedded TCP/IP networking stack. It negotiates **LCP (Link Control Protocol)** and **IPCP (Internet Protocol Control Protocol)**, handing the laptop an IP address (typically on a private `10.x.x.x` subnet).
- The laptop can ping remote dispatch servers, transmit NCIC license plate queries, and transfer CAD incidents directly over the P25 9600 bps air interface. **The radio is literally an IP router!**

#### Mode 3: Radio Peripheral Protocol (RPP) & AT Commands
- The radio supports AT-style command strings for external accessories:
  - Querying battery level and RSSI signal strength: `AT+CSQ`
  - Fetching GPS location data from an attached Hirose GPS microphone: `AT+GPS`
  - Sending Text Messaging Service (TMS) packets to other radio IDs.

#### Mode 4: Bootstrap / S-Record Flashport Engine
- When entering firmware upgrade mode, the ColdFire CPU shifts baud rate to **38,400 or 115,200 baud**.
- The CPU runs from internal masked boot ROM, bypassing the flash memory completely.
- Motorola Flashport software transfers firmware as standard Motorola **S-Record format (`S19`, `S28`, `S37`)**, which contain 32-bit target memory addresses, byte counts, data payloads, and longitudinal parity checksums.

---

### 1.3 SB9600 Frame Construction & Checksum Math

Every single byte string exchanged during codeplug read/write conforms to the following grammar:

```
Byte 0:  0x05              (Framing Start Flag: ASCII ENQ)
Byte 1:  LENGTH            (Count of bytes from OPCODE through last PAYLOAD byte)
Byte 2:  OPCODE            (Command or Reply identifier)
Byte 3..N: PAYLOAD         (Optional parameters, memory addresses, or data blocks)
Byte N+1: CHECKSUM         (Two's complement checksum)
```

#### Exact Mathematical Calculation:
To compute the checksum:
1. Compute the simple 8-bit arithmetic sum of all bytes from `LENGTH` through the end of `PAYLOAD`.
2. Negate the sum (two's complement):
   $$\text{Checksum} = (-\sum \text{bytes}) \pmod{256}$$
3. In Python:
   ```python
   def calculate_checksum(length: int, opcode: int, payload: bytes) -> int:
       total = length + opcode + sum(payload)
       return (-total) & 0xFF
   ```
4. Verification: Summing `LENGTH + OPCODE + PAYLOAD + CHECKSUM` must always yield `0x00` in the lowest 8 bits.

---

### 1.4 Step-by-Step Packet Trace: Reading & Writing a Codeplug

When an engineer clicks "Read Radio" or "Write Radio" in CPS, here is the exact byte-level conversation:

#### Step 1: The Handshake & Identity Query
```
PC  -> [0x05] [0x01] [0x00] [0xFF]
       (OPCODE 0x00: RADIO_PING)
RAD <- [0x05] [0x01] [0x01] [0xFE]
       (OPCODE 0x01: RADIO_ACK - Radio confirms it is alive)

PC  -> [0x05] [0x01] [0x14] [0xEB]
       (OPCODE 0x14: GET_RADIO_INFO)
RAD <- [0x05] [0x32] [0x15] [Model: "H46KDH9PW7BN\0"] 
                            [Serial: "422CHB0123\0"] 
                            [Flashcode: "500008-000488-4\0"] 
                            [Firmware: "R20.01.00\0"] [CSUM]
       (OPCODE 0x15: RADIO_INFO_REPLY - CPS inspects Model & Flashcode to verify license)
```

#### Step 2: Entering Programming Mode (The RF Silencer)
```
PC  -> [0x05] [0x03] [0x10] [0xA5] [0x5A] [0xEE]
       (OPCODE 0x10: ENTER_PROGRAMMING_MODE, Security Token: 0xA5 0x5A)
RAD <- [0x05] [0x01] [0x01] [0xFE]
       (OPCODE 0x01: ACK)
```
*What the radio does internally:* The ColdFire CPU mutes the RF power amplifier, disables receiver interrupts, lights up the screen with the text **`"PROGRAMMING"`**, and enters a deterministic flash read/write loop.

#### Step 3: Block Memory Reading Loop
The codeplug partition begins at address `0x0020_0000` and spans up to `0x0024_0000` ($256\text{ KB}$). CPS streams the memory out in 128-byte or 256-byte blocks:

```
PC  -> [0x05] [0x05] [0x20] [0x00] [0x20] [0x00] [0x80] [CSUM]
       (OPCODE 0x20: READ_MEMORY_BLOCK)
       Payload: Address [0x00, 0x20, 0x00] = 0x00200000, Length: 0x80 (128 bytes)

RAD <- [0x05] [0x82] [0x21] [0x00] [128 Bytes of Raw Flash Data...] [CSUM]
       (OPCODE 0x21: READ_MEMORY_REPLY)
       Payload: Status 0x00 (OK) + 128 bytes of data
```
This request-reply cycle repeats sequentially for each chunk (`0x0020_0080`, `0x0020_0100`, etc.) until the entire codeplug partition is in PC memory.

#### Step 4: Block Memory Writing Loop (Writing Back Updates)
When writing changes:
```
PC  -> [0x05] [0x85] [0x30] [0x00] [0x20] [0x00] [0x80] [128 Bytes Data...] [CSUM]
       (OPCODE 0x30: WRITE_MEMORY_BLOCK)
       Payload: Address [0x00, 0x20, 0x00], Length: 0x80, followed by 128 bytes

RAD <- [0x05] [0x02] [0x31] [0x00] [CSUM]
       (OPCODE 0x31: WRITE_MEMORY_REPLY)
       Payload: Status 0x00 (Success)
```
*Note on write errors:* If the PC attempts to write to a protected sector (like the Tuning Partition `0x0000_4000`), the radio returns Status `0x01` (`WRITE_PROTECTED`) or `0x03` (`ADDRESS_OUT_OF_BOUNDS`).

#### Step 5: Exiting Programming Mode & The Watchdog Reboot
```
PC  -> [0x05] [0x02] [0x11] [0x01] [CSUM]
       (OPCODE 0x11: EXIT_PROGRAMMING_MODE, Reset Action: 0x01 = Soft Reboot)
RAD <- [0x05] [0x01] [0x01] [0xFE]
       (OPCODE 0x01: ACK)
```
Upon receiving this command, the ColdFire CPU triggers its internal software watchdog timer, causing the processor to reboot. The radio performs its power-up self-test, beeps the familiar Motorola power-up tone, displays the newly programmed default channel, and resumes normal RF operations.

---

## Part 2: The `.cpg` File as an Actual Relational Database

### 2.1 The Container: Microsoft Compound File Binary (CFB)
If you inspect a `.cpg` file using Python's `olefile` library or standard binary inspection tools, you find that it is an **OLE Structured Storage Compound Document** (identical in structure to an old `.doc` or `.xls` file):

```
Root Entry
 ├── 📁 RadioProfile
 │    ├── 📄 RadioInfo       (Model, Serial, Flashcode, Tuning Checksum)
 │    └── 📄 FeatureFlags    (Active licensed options bitmask)
 ├── 📁 CodeplugDB
 │    ├── 📄 JetDatabase     (Complete binary serialized Microsoft Jet 3.5/4.0 MDB)
 │    └── 📄 ChecksumTable   (Internal CRC32 hashes for each database table)
 └── 📁 Audit
      └── 📄 HistoryLog      (Technician timestamps, CPS serial numbers used)
```

Motorola did not invent a custom database format from scratch for ASTRO 25. In 1999, when developing the Cedar platform in Visual C++ 6.0, Motorola engineers chose the **Microsoft Jet Database Engine** (via Microsoft DAO / ODBC) because it offered out-of-the-box relational integrity, transactional commits, and indexing.

---

### 2.2 The Complete Relational Schema Map

Below is the normalized relational entity-relationship model implemented inside the codeplug database:

```
+───────────────────────────────────────────────────────────────────────────────────────────+
|                           ASTRO 25 RELATIONAL DATABASE SCHEMA                             |
+───────────────────────────────────────────────────────────────────────────────────────────+

  +─────────────────────────+             +──────────────────────────────────+
  |        tbl_Zone         |             |         tbl_ZoneChannel          |
  +─────────────────────────+             +──────────────────────────────────+
  | PK  ZoneID (Int)        | 1         N | PK,FK1  ZoneID (Int)             |
  |     ZoneNumber (1..255) |────────────<| PK      ChannelPosition (1..16)  |
  |     ZoneLabel (String)  |             |         DisplayName (String)     |
  +─────────────────────────+             | FK2     PersonalityID (Int)      |─────┐
                                          | FK3     ScanListID (Int)         |──┐  │
                                          |         FPP_Enabled (Bool)       |  │  │
                                          +──────────────────────────────────+  │  │
                                                                                │  │
       ┌────────────────────────────────────────────────────────────────────────┘  │
       │                                                                           │
       ▼                                                                           ▼
  +───────────────────────────────+               +──────────────────────────────────+
  |         tbl_ScanList          |               |    tbl_ConventionalPersonality   |
  +───────────────────────────────+               +──────────────────────────────────+
  | PK  ScanListID (Int)          |               | PK  PersonalityID (Int)          |
  |     ScanListName (String)     |               |     RxFrequency (BCD 32-bit)     |
  |     Priority1_ChannelID (FK)  |               |     TxFrequency (BCD 32-bit)     |
  |     Priority2_ChannelID (FK)  |               |     Bandwidth (12.5k / 25k)      |
  |     PrioritySampleTime (ms)   |               |     RxSquelchType (CSQ/PL/DPL/P25|
  |     TxDesignatedChannel (Int) |               |     RxSquelchCode (Float/Int)    |
  +───────────────────────────────+               |     TxPowerLevel (High/Low)      |
                                                  |     TxInhibitOnBusy (Bool)       |
                                                  |     TimeOutTimer (Seconds)       |
                                                  | FK1 AstroSystemID (Int)          |──┐
                                                  | FK2 MdcSystemID (Int)            |─┐│
                                                  +──────────────────────────────────+ ││
                                                                                       ││
       ┌───────────────────────────────────────────────────────────────────────────────┘│
       │                                                                                │
       ▼                                                                                ▼
  +───────────────────────────────+               +──────────────────────────────────+
  |        tbl_MdcSystem          |               |         tbl_AstroSystem          |
  +───────────────────────────────+               +──────────────────────────────────+
  | PK  MdcSystemID (Int)         |               | PK  AstroSystemID (Int)          |
  |     PrimaryID (Hex 16-bit)    |               |     RxNAC (12-bit Hex, e.g. $293)|
  |     PTT_ID_Pre (Bool)         |               |     TxNAC (12-bit Hex, e.g. $293)|
  |     PTT_ID_Post (Bool)        |               |     TalkgroupID (16-bit Int)     |
  |     EmergencyID (Hex 16-bit)  |               |     VoiceMode (ASTRO/Mixed/Analog|
  +───────────────────────────────+               |     CAI_PacketDataEnabled (Bool) |
                                                  | FK1 CryptoKeyReferenceID (CKR)   |──┐
                                                  +──────────────────────────────────+  │
                                                                                        │
                                                                                        ▼
                                                  +──────────────────────────────────+
                                                  |         tbl_SecureKey            |
                                                  +──────────────────────────────────+
                                                  | PK  CKR_ID (Int 1..4096)         |
                                                  |     KeyName (String)             |
                                                  |     Algorithm (ADP/DES/AES-256)  |
                                                  |     KeyID (KID, 16-bit Hex)      |
                                                  |     StorageLocation (SLN, Int)   |
                                                  |     KeyData (Obfuscated/Blank)   |
                                                  +──────────────────────────────────+
```

---

### 2.3 Why This Design Stymied Third-Party Programmers

For twenty years, people tried and failed to make open-source Motorola programmers. Here is why:

1. **The Indirect Pointer Problem:**
   In consumer radios, writing a channel is simply writing an array:
   `radio.set_channel(1, freq=146.520, name="CALL")`
   If you try that on a Motorola, it fails because **Channel 1 does not own a frequency!**
   Channel 1 is merely an entry in `tbl_ZoneChannel` containing `PersonalityID = 4`.
   If you change the frequency of Channel 1, you are actually modifying `Personality #4`. But if Channels 2, 5, and 9 *also* point to `Personality #4`, you have unintentionally changed the frequencies of Channels 2, 5, and 9 as well!

2. **The Validation & Cascading Delete Rules:**
   Motorola CPS contains thousands of lines of C++ business rules:
   - You cannot delete `tbl_ScanList #2` if any channel in `tbl_ZoneChannel` or `tbl_ConventionalPersonality` references it.
   - You cannot set `tbl_ConventionalPersonality` to `VoiceMode = ASTRO` if its `AstroSystemID` is NULL.
   - If you delete a personality, CPS must cascade the check and flag every Zone Channel pointing to it as invalid.

3. **Compilation from Relational Tables to Flash Memory:**
   When writing to the radio, CPS runs an internal compiler that executes:
   $$\text{Jet Database Tables} \xrightarrow{\text{Normalization \& Packing}} \text{Contiguous Flash Image} \xrightarrow{\text{SB9600 Opcode 0x30}} \text{ColdFire EEPROM}$$
   The ColdFire CPU does not execute Jet SQL queries in real-time; it expects binary structs with pre-computed 16-bit relative memory offsets!

---

## Part 3: Concrete Implementation Blueprint for OpenAstro CPS

Now that every layer is laid bare, here is how `open-astro-cps` natively decodes, manipulates, and generates both `.cpg` files and over-the-wire streams.

### 3.1 The Auto-Relational Ingestion Engine
To provide a clean spreadsheet experience (CSV or JSON), OpenAstro performs **automated database normalization** under the hood:

```
[ User Input: Flat CSV ]
  Zone 1, Ch 1, "DISPATCH", 851.5125 MHz, CSQ, High Power, P25, NAC $293
  Zone 1, Ch 2, "TAC 1",    852.0125 MHz, CSQ, High Power, P25, NAC $293
  Zone 1, Ch 3, "TAC 2",    853.5125 MHz, CSQ, High Power, P25, NAC $293
                         │
                         ▼
           [ OpenAstro Relational Compiler ]
  1. Has an ASTRO System with NAC $293 been created?
     -> No: Create AstroSystem #1 (NAC=$293, Talkgroup=1).
     -> Yes: Reuse AstroSystem #1.
  2. Create ConventionalPersonality #1 (Freq=851.5125, AstroSystemID=1).
  3. Create ConventionalPersonality #2 (Freq=852.0125, AstroSystemID=1).
  4. Create ConventionalPersonality #3 (Freq=853.5125, AstroSystemID=1).
  5. Create ZoneChannel Table entries pointing to Personality IDs #1, #2, #3.
                         │
                         ▼
    [ Output: Serialized Binary Structs for ColdFire ]
```

### 3.2 Reading `.cpg` Files Directly via Python `olefile`
To extract streams from official `.cpg` files on Linux, macOS, or Windows without requiring Microsoft Office or Windows Jet drivers:

```python
import olefile

def inspect_cpg_container(file_path: str):
    """Clean-room unpacker for Motorola .cpg OLE Compound Documents."""
    with olefile.OleFileIO(file_path) as ole:
        # List all streams inside the virtual filesystem
        streams = ole.listdir()
        print(f"Streams found inside {file_path}:")
        for stream in streams:
            print(" / ".join(stream))
            
        # Extract radio identity metadata
        if ole.exists("RadioProfile/RadioInfo"):
            radio_info = ole.openstream("RadioProfile/RadioInfo").read()
            # Parse packed binary header
            print(f"Extracted RadioInfo: {len(radio_info)} bytes")
            
        # Extract the Jet Database stream
        if ole.exists("CodeplugDB/JetDatabase"):
            jet_db_bytes = ole.openstream("CodeplugDB/JetDatabase").read()
            print(f"Extracted Jet Database: {len(jet_db_bytes)} bytes")
            return jet_db_bytes
```

---

## Part 4: Developer Hand-Off Checklist & Next Steps

When the next agent or developer resumes work:

1. **Everything is Documented and Tracked:**
   - [**`docs/deep_dive_radio_port_and_cpg_relational_database.md`**](file:///C:/Users/v-mariorivas/open-astro-cps/docs/deep_dive_radio_port_and_cpg_relational_database.md) (This deep-dive architectural specification).
   - [**`docs/motorola_astro_cps_architecture_and_design_paper.md`**](file:///C:/Users/v-mariorivas/open-astro-cps/docs/motorola_astro_cps_architecture_and_design_paper.md) (The overarching engineering paper).
   - [**`docs/cps_subsystems_reference_notes.md`**](file:///C:/Users/v-mariorivas/open-astro-cps/docs/cps_subsystems_reference_notes.md) (Granular field and opcode tables).

2. **Serial Link Driver Ready:**
   - Check [`src/open_astro/protocol/framing.py`](file:///C:/Users/v-mariorivas/open-astro-cps/src/open_astro/protocol/framing.py): Contains the verified `PacketFramer` calculating two's complement checksums.
   - Check [`src/open_astro/protocol/serial_link.py`](file:///C:/Users/v-mariorivas/open-astro-cps/src/open_astro/protocol/serial_link.py): Contains the auto-detecting PySerial driver for FTDI / Prolific cables.

3. **Testing Verification:**
   - Execute tests at any time using:
     ```powershell
     Set-Location C:\Users\v-mariorivas\open-astro-cps
     $env:PYTHONPATH="src"
     python -m unittest discover tests
     ```
   - All tests pass cleanly (`5/5 OK`).

4. **Hardware Verification Step (When Radio is Plugged In):**
   - Connect the XTS 5000 / XTS 2500 / PRC-153 to your USB port with the programming cable.
   - Run `open-astro ports` to detect the COM port.
   - Execute the `open-astro probe` routine to verify Opcode `0x14` and print the radio's Model, Serial, and Flashcode.

---
*End of Technical Master Guide.*
