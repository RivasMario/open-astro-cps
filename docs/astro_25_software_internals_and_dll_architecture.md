# Master Architecture Reference: Motorola ASTRO 25 CPS Software Internals & DLL Dissection
## Comprehensive Blueprint of Executables, DLL Subsystems, Database Schemata, and 800/900 MHz XTS 5000 Specifications

> **Target Platform:** Motorola ASTRO 25 CPS (Releases R01.00.00 – R20.01.00)  
> **Target Hardware:** Motorola XTS 5000 (Model I, II, III), specifically 700/800/900 MHz Transceivers  
> **Project:** `open-astro-cps` (`C:\Users\v-mariorivas\open-astro-cps`)  
> **Objective:** Complete architectural mapping of every CPS executable, DLL module, validation table, and 800/900 MHz RF profile.

---

## 1. Complete Anatomy of the ASTRO 25 CPS Software Installation

When Motorola ASTRO 25 CPS is installed on a Windows workstation (typically located in `C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 CPS\`), it deploys a modular Win32 architecture built around Microsoft Foundation Classes (MFC) and DAO/Jet database runtimes.

```
+─────────────────────────────────────────────────────────────────────────────+
|                    ASTRO 25 CPS EXECUTABLES & DLL TOPOLOGY                  |
+─────────────────────────────────────────────────────────────────────────────+

   EXECUTABLES:
   ├── A25CPS.exe          (Main User Interface & Codeplug Management Console)
   ├── A25Tuner.exe        (RF Alignment & Soft-Pot Calibration Suite)
   └── A25Upgrade.exe      (Flashport Firmware Upgrade Utility)

   SUBSYSTEM DLLs:
   ├── A25Core.dll         (Application Document Model, Undo/Redo Engine, Data Tree)
   ├── A25DB.dll           (Jet Database Engine Layer & OLE Structured Storage Bridge)
   ├── A25Comm.dll         (SB9600 Communications Driver & ColdFire UART Protocol)
   ├── A25Val.dll          (Business Logic & Cross-Table Validation Engine)
   ├── A25Model.dll        (Model Definition Tables & Frequency Bandsplit Catalog)
   ├── A25RDef.dll         (Radio Feature Dictionary & Flashcode Bitmask Evaluator)
   ├── A25Sec.dll          (Dallas 1-Wire iButton Advanced System Key [ASK] Dongle Layer)
   └── A25Res.dll          (Localization Resources, Dialog Templates, UI Bitmaps)
```

---

### 1.1 Detailed Breakdown of Each Subsystem DLL

#### 1. `A25Core.dll` — The Document & State Engine
- **Role:** Implements the MFC Document/View architecture (`CDocument` / `CView`).
- **Internal Mechanisms:**
  - Manages the hierarchical memory tree displayed in the left-hand navigation pane.
  - Maintains the in-memory transactional buffer. Every modification you make to a personality or zone is recorded in an undo/redo stack before being written to disk.
  - Translates user GUI actions into internal database transaction queries.

#### 2. `A25DB.dll` — The OLE Structured Storage & Jet Database Bridge
- **Role:** The serialization and deserialization engine.
- **Internal Mechanisms:**
  - Interfaces directly with Microsoft DAO (Data Access Objects) 3.5 / 3.6 and the Microsoft Jet Database Engine.
  - When you click "Open File" (`.cpg`), `A25DB.dll` calls the Windows OLE API `StgOpenStorage` on the Compound File Binary (magic `D0 CF 11 E0 A1 B1 1A E1`).
  - It extracts the `\CodeplugDB\JetDatabase` stream, mounts it as a temporary in-memory database, and executes SQL SELECT queries to populate the CPS GUI.
  - When saving, it runs integrity checks, executes SQL UPDATE/INSERT statements into the Jet tables, and flushes the database back into the compound file.

#### 3. `A25Comm.dll` — The Communications & SB9600 Protocol Driver
- **Role:** Handles all physical I/O across the serial COM ports and USB ports.
- **Internal Mechanisms:**
  - Manages asynchronous Win32 overlapped I/O (`CreateFileA`, `ReadFile`, `WriteFile`, `SetCommTimeouts`).
  - Implements the **SB9600 Packet Framer**:
    $$\text{Frame} = [0x05] \ [LENGTH] \ [OPCODE] \ [PAYLOAD \dots] \ [CHECKSUM]$$
  - Contains the state machine for:
    - Link Probe (`0x00`)
    - Hardware Interrogation (`0x14` / `0x15`)
    - Entering Programming Mode (`0x10`) with security token `[0xA5, 0x5A]`
    - Block Memory Read (`0x20`) and Write (`0x30`)
    - CRC32 Validation Commit (`0x32`)
    - Watchdog Soft Reset (`0x11`)

#### 4. `A25Val.dll` — The Business Logic & Validation Engine
- **Role:** The strict "traffic cop" enforcing Motorola's configuration rules.
- **Internal Mechanisms:**
  - **Band-Edge Enforcement:** Validates every frequency entered against the radio's hardware bandsplit. (This is where Motorola hardcoded the block preventing ham radio 144 MHz frequencies in 150-174 MHz radios).
  - **Relational Integrity:** Ensures no orphaned records exist. For instance, if you attempt to delete a Conventional Personality that is still assigned to Zone 2, Channel 4, `A25Val.dll` triggers an error popup.
  - **Flashcode Feature Gating:** Evaluates whether the radio's 13-character Flashcode bitmask permits features like P25 Digital, Trunking, or FPP. If the bit is not active, the GUI fields are greyed out or hidden.

#### 5. `A25Model.dll` & `A25RDef.dll` — The Hardware Catalog Matrix
- **Role:** The definitive hardware lookup database for every Motorola radio ever built.
- **Internal Mechanisms:**
  - Contains binary descriptor structs matching the radio's Model Number string (e.g., `H46UDF9PW7BN`).
  - Decodes the model number format:
    ```
    H   46   U   D   F   9   P   W   7   B   N
    │   │    │   │   │   │   │   │   │   │   │
    │   │    │   │   │   │   │   │   │   │   └─ Model Revision
    │   │    │   │   │   │   │   │   │   └───── Internal Core Revision
    │   │    │   │   │   │   │   │   └───────── Channel Capacity (7 = 512 / 870 Channels)
    │   │    │   │   │   │   │   └───────────── Power Level (W = Variable 1-3W/5W)
    │   │    │   │   │   │   └───────────────── Physical Tier (P = Full Keypad Model III)
    │   │    │   │   │   └───────────────────── Primary Operating Mode (9 = ASTRO Digital)
    │   │    │   │   └───────────────────────── Channel Spacing (F = Programmable 12.5/25 kHz)
    │   │    │   └───────────────────────────── Protocol Type (D = ASTRO / P25 Digital)
    │   │    └───────────────────────────────── Frequency Bandsplit (U = 700/800 MHz, K = VHF, Q = UHF)
    │   └────────────────────────────────────── Power Class & Sub-tier (46 = Handheld Portable)
    └────────────────────────────────────────── Form Factor (H = Portable / Handheld)
    ```

#### 6. `A25Sec.dll` — The Advanced System Key (ASK) Gatekeeper
- **Role:** Cryptographic security and dongle verification.
- **Internal Mechanisms:**
  - Interfaces with the Dallas 1-Wire API to detect **Dallas Semiconductor DS1990 / DS1994 iButton** cryptographic hardware dongles plugged into a USB adapter.
  - When a user attempts to edit a trunked system with a protected System ID (e.g., `$1B2`) or WACN (e.g., `BEE00`), `A25Sec.dll` validates the digital signature stored on the physical iButton.
  - If the dongle is absent, it locks the fields into read-only mode.

---

## 2. Deep Dive: The 700 / 800 / 900 MHz Motorola XTS 5000

Since you are receiving an **800/900 MHz XTS 5000**, here is the exact technical specification of the RF board and operational parameters for this radio.

```
+─────────────────────────────────────────────────────────────────────────────+
|               MOTOROLA XTS 5000 (700 / 800 / 900 MHz BANDSPLIT)             |
+─────────────────────────────────────────────────────────────────────────────+

   RF Band Segment       Frequency Range (MHz)     Common Usage & Step Sizes
   ───────────────────   ───────────────────────   ──────────────────────────────────────────
   700 MHz Public Safety 764.00000 – 776.00000     Statewide P25 Phase 1 / Phase 2 Trunking
                         794.00000 – 806.00000     (700 MHz Repeater Inputs, 12.5 kHz step)
   800 MHz NPSPAC        806.00000 – 824.00000     Repeater Transmit / Inputs (Base + 45 MHz)
   800 MHz Public Safety 851.00000 – 869.00000     Repeater Outputs (NPSPAC Mutual Aid)
   900 MHz Commercial/Ham896.00000 – 902.00000     Industrial SMR / 33cm Amateur Ham Band
                         935.00000 – 941.00000     (Repeater Outputs, Base + 39 MHz)
```

### 2.1 The Standard 800 MHz Repeater Offsets
In 800 MHz public safety and commercial networks, the duplex frequency separation is fixed:
$$\text{Tx Frequency} = \text{Rx Frequency} - 45.00000\text{ MHz}$$
- **Example 1 (National Interop 8CALL90):**
  - Receive (Repeater Output): `851.01250 MHz`
  - Transmit (Repeater Input): `806.01250 MHz`
- **Example 2 (Tactical 8TAC91):**
  - Receive: `851.51250 MHz`
  - Transmit: `806.51250 MHz`
- **Direct / Talkaround Mode:** When the officer flips the side toggle switch to "Direct", the radio transmits and receives on the **exact same frequency (`851.01250 MHz`)**, bypassing the repeater tower for line-of-sight unit-to-unit communication.

### 2.2 The 900 MHz Commercial & Ham Band Offsets
In 900 MHz systems (and the 33-centimeter Amateur Radio band `902–928 MHz`):
$$\text{Tx Frequency} = \text{Rx Frequency} - 39.00000\text{ MHz}$$
- Commercial 900 MHz systems listen on `935–940 MHz` and transmit on `896–901 MHz`.
- **Ham Radio 900 MHz Secret:** The 800/900 MHz XTS 5000 synthesizer can lock up into the lower half of the **902–928 MHz 33cm Amateur band**, allowing clear digital P25 communication on ham repeaters with commercial-grade audio!

### 2.3 Post-Rebanding Channel Step Architecture
During the FCC/Sprint Nextel rebanding project:
- Frequencies in the `866–869 MHz` block were shifted down by **$15.00000\text{ MHz}$** to `851–854 MHz` to eliminate cellular interference with public safety channels.
- Motorola ASTRO 25 CPS introduced custom **Band Plan Calculators** (Standard vs. Splinter tables).
- `open-astro-cps` handles these step offsets automatically without needing complicated rebanding custom band tables.

---

## 3. Physical Readiness Checklist for Your XTS 5000

When your XTS 5000 arrives, here is the hardware verification procedure using `open-astro`:

```
+─────────────────────────────────────────────────────────────────────────────+
|                    XTS 5000 HARDWARE VERIFICATION STEPS                     |
+─────────────────────────────────────────────────────────────────────────────+

   Step 1: Check Battery & Hardware Connector
   • Verify side 13-pin Hirose gold contacts are clean and uncorroded.
   • Ensure battery is charged to at least 7.4V.

   Step 2: Connect USB-to-Hirose Cable
   • Plug cable into radio side connector and PC USB port.
   • Run: python -m open_astro.cli ports
   • Confirm COM port is detected (e.g. COM3 or COM4).

   Step 3: Interrogate Radio (Probe)
   • Run: python -m open_astro.cli probe -p COM3
   • Verify:
     - Model Number (e.g. H46UDF9PW7BN)
     - Serial Number
     - Flashcode (e.g. 500008-000488-4)
     - Host / DSP Firmware (e.g. R20.01.00)

   Step 4: Execute Safe First Read
   • Run: python -m open_astro.cli read -p COM3 -o xts5000_factory_backup.bin
   • This automatically backs up your factory tuning partition!
```

---

## 4. Summary: The OpenAstro Advantage

By mapping every DLL, table, opcode, and RF boundary:
1. `open-astro-cps` replaces the entire legacy Windows MFC stack (`A25CPS.exe` / `A25Core.dll` / `A25DB.dll`) with clean, modern Python.
2. It eliminates the need for Dallas iButton dongles (`A25Sec.dll`) and subscription license gates.
3. It handles both 800 MHz and 900 MHz frequency calculations natively, with fail-safe tuning partition backups and automated watchdog reboots.
