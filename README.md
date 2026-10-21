# OpenAstro CPS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Fedora%20%2F%20Linux%20%7C%20macOS-lightgrey.svg)]()

> ### Project status (2026-10-20)
> **Working and verified, against real hardware:** the codeplug data model,
> JSON/CSV conversion, the USB transport layer (port detection, permissions,
> device identification), and **`open-astro probe`**, which reads a real
> radio's identity today (model, serial, security status) via the AT command
> interface its own USB descriptor advertises — a real, measured-safe,
> read-only query, not a guess. See
> [**docs/AT_INTERFACE_DISCOVERY.md**](docs/AT_INTERFACE_DISCOVERY.md).
>
> **Real, but not yet sufficient for codeplug read/write:** static analysis of
> the actual Motorola CPS installer (`PatPort.exe`) recovered real command
> names and byte payloads (`MEMACS`, `RELEASE`, `EPREQ`, `TSTMOD`, ...),
> independently cross-confirmed against a leaked official Motorola protocol
> manual and an unrelated open-source SB9600 CRC implementation. A live
> `usbmon` capture of the real software running under Wine recorded its exact
> real connection sequence (`AT&V` → `AT#DATLCL=1` → `AT+IPR=...`) — and
> caught it failing at the same `AT+IPR=` step, every baud rate tried,
> reproducibly, for both the real software and this project's own test code.
> **Running the original 2002-era Windows CPS under Wine on this Fedora
> laptop is a dead end** — broken rendering, repeated crashes, and this same
> communication wall the real software hits too. See
> [**docs/CPS_BINARY_ANALYSIS.md**](docs/CPS_BINARY_ANALYSIS.md) sections 7-8
> for the full trail (opcode table, real CRC, captured sequence, crash
> analysis).
>
> **Still not implemented:** reading or writing the codeplug itself. Writing
> to a radio is gated off (`--accept-unverified-protocol`) until the
> transport this is resolved — see
> [**docs/PROTOCOL_STATUS.md**](docs/PROTOCOL_STATUS.md) and
> [**docs/HARDWARE_GROUND_TRUTH.md**](docs/HARDWARE_GROUND_TRUTH.md).
>
> **A number of `docs/` files predate this investigation and were written
> without reading any real Motorola code** — they present a plausible but
> fabricated protocol (invented opcodes, a `0x05` start byte with no basis,
> a Microsoft Jet database that isn't there). They're marked below; read
> `CPS_BINARY_ANALYSIS.md` first for what's actually confirmed.

**OpenAstro CPS** is an open-source codeplug engine, format converter, and serial programming toolkit for **Motorola ASTRO 25** radios:
* **Motorola XTS 2500** (Model I, Model II, Model III)
* **Motorola PRC-153 IISR** (Integrated Intra-Squad Radio)
* **Motorola XTS 5000**
* **Motorola XTS 1500 / MT1500 / PR1500**
* **Motorola XTL 5000 / XTL 2500 Mobile Radios**

---

## 🎯 Motivation

Proprietary radio programming software (CPS) has historically been:
* Locked to legacy 32-bit Windows XP/7 operating systems (Motorola CPS **never** ran on Linux).
* Gated behind expired commercial licenses, Advanced System Keys (ASK), and region locks.
* Storing configurations in opaque, proprietary binary archives (`.cpg`).

**OpenAstro** liberates these radios by providing:
1. **100% Cross-Platform**: Runs natively on **Fedora Linux**, Ubuntu, Arch, Windows 11, and macOS without virtual machines or Wine.
2. **Human-Readable Configurations**: Full codeplugs stored in structured **JSON**, **YAML**, or **CSV spreadsheets**.
3. **Spreadsheet Workflow**: Edit channels in Excel, LibreOffice Calc, or Google Sheets and import directly into your radio.
4. **Software Encryption (Motorola ADP)**: Native support for configuring 40-bit RC4 digital privacy keys without external hardware.
5. **Safety First (`rx_only: true`)**: Hardware transmitter power amplifier lockout to guarantee zero accidental interference on public safety channels.
6. **Direct USB / Serial Link**: The XTS 1500 / 2500 / MT 1500 is itself a USB
   CDC-ACM device (`0cad:1001`) and appears as `/dev/ttyACM0` with no FTDI cable
   involved; XTS 5000 and mobiles use a USB-UART bridge (`/dev/ttyUSB0`). Both
   are detected automatically by USB VID/PID. The command protocol on top of
   this link is still unverified (see status note above).

---

## 🧱 Architecture

```
                 +-----------------------------------+
                 | LibreOffice Calc / Excel / Web UI |
                 +-----------------+-----------------+
                                   |
                                   v
                 +-----------------------------------+
                 | OpenAstro Data Model (JSON / YAML)|
                 +-----------------+-----------------+
                                   |
                                   v
                 +-----------------------------------+
                 | Command Protocol  [UNVERIFIED]    |
                 +-----------------+-----------------+
                                   |
                                   v
                 +-----------------------------------+
                 | /dev/ttyACM0  (radio's own USB)   |
                 | /dev/ttyUSB0  (FTDI cable)  COMx  |
                 +-----------------+-----------------+
                                   |
                                   v
                 +-----------------------------------+
                 | Motorola XTS 2500 / PRC-153 Radio |
                 +-----------------------------------+
```

---

## 🚀 Quickstart

### Installation

#### On Windows:
```powershell
git clone https://github.com/RivasMario/open-astro-cps.git
cd open-astro-cps
pip install -e .
```

#### On Fedora Linux:
```bash
# See docs/linux_fedora_setup.md for full instructions & udev rules
sudo dnf install -y python3 python3-pip git
sudo usermod -aG dialout $USER
git clone https://github.com/RivasMario/open-astro-cps.git
cd open-astro-cps
pip install -e .
```

---

## 📋 Usage Examples

### 1. View 800 MHz King County Fleet Plan
```bash
open-astro info examples/king_county_800mhz_fleet.json
```
Output:
```
==========================================
 Radio Model  : Motorola XTS 2500 Model II
 Bandsplit    : 700/800 MHz (764-870 MHz)
 Serial Number: OPENASTRO_SURPLUS
 Total Zones  : 3
 Total Chans  : 9
 Crypto Keys  : 1 defined
   -> Key 1 (TEAM_ADP_1): ADP [Hash: A1B2****]
==========================================

[Zone 1: TEAM SECURE] (3 channels) - Transmit Enabled
  Ch  1: TEAM CLEAR     | Rx: 851.51250 | Tx: 851.51250 | ASTRO P25 NAC:$293 TG:1
  Ch  2: TEAM ENCRYPT   | Rx: 852.01250 | Tx: 852.01250 | ASTRO P25 NAC:$293 TG:1 [ENC:TEAM_ADP_1]
  Ch  3: TEAM ANALOG    | Rx: 853.01250 | Tx: 853.01250 | Analog PL:156.7/156.7Hz

[Zone 2: 800 INTEROP] (3 channels) - National Mutual Aid
  Ch  1: 8CALL90        | Rx: 851.01250 | Tx: 806.01250 | Analog PL:156.7/156.7Hz
  Ch  2: 8TAC91         | Rx: 851.51250 | Tx: 806.51250 | Analog PL:156.7/156.7Hz
  Ch  3: 8TAC92         | Rx: 852.01250 | Tx: 807.01250 | Analog PL:156.7/156.7Hz

[Zone 3: PS MONITOR] (3 channels) - Passive Reception Only
  Ch  1: PSERN CTRL 1   | Rx: 851.88750 | Tx: 851.88750 | ASTRO P25 [RX-ONLY LOCK]
  Ch  2: PSERN CTRL 2   | Rx: 852.86250 | Tx: 852.86250 | ASTRO P25 [RX-ONLY LOCK]
  Ch  3: PSERN CTRL 3   | Rx: 853.82500 | Tx: 853.82500 | ASTRO P25 [RX-ONLY LOCK]
```

### 2. Edit in LibreOffice Calc / Excel
```bash
# Export to CSV
open-astro to-csv examples/king_county_800mhz_fleet.json channels.csv

# ... edit channels in your spreadsheet editor ...

# Import back to codeplug JSON
open-astro from-csv channels.csv updated_fleet.json
```

### 3. Detect Connected Programming Cables
```bash
open-astro ports
```
```
[+] Detected serial ports:
  -> /dev/ttyACM0 (MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO - Motorola Communication Interface) [RADIO: Motorola XTS 1500 / XTS 2500 / MT 1500]

[+] Auto-detect would use: /dev/ttyACM0
    Native USB radio: XTS 1500 / XTS 2500 / MT 1500 (VID:PID 0CAD:1001, CDC-ACM)
```
Legacy motherboard ports (`/dev/ttyS*`) are listed but never auto-selected.
If the port is not accessible, install the udev rule from `scripts/`.

### 4. Probe a Real Radio (works today, verified against hardware)
```bash
open-astro probe
```
```
[*] Probing radio on port /dev/ttyACM0...
[+] Radio responded OK to AT -- link established.
[+] Radio Identity (AT&V):
    Firmware: Motorola System Release 6.0 Radio
    RADIO: XTS 2500
    MODEL: H46UCF9PW6AN
    SERIAL: 205CFR2930
    SECURE: R000000
    PORT: SIDE CONNECTOR AS USB
    ...
```
This uses the radio's own AT command interface (see
[**docs/AT_INTERFACE_DISCOVERY.md**](docs/AT_INTERFACE_DISCOVERY.md)) — a
real, measured-safe, read-only query, not a guess. Codeplug read/write still
isn't implemented for real; see the project status note above.

---

## 📚 Documentation

* [**AT Interface Discovery — the one real, working transport**](docs/AT_INTERFACE_DISCOVERY.md): how `probe` actually talks to a real radio today.
* [**CPS Binary Analysis — real DLL names, real COM interface, real opcode names**](docs/CPS_BINARY_ANALYSIS.md): what extracting and reading the actual Motorola installer turned up.
* [**Protocol Status — read before trusting any opcode**](docs/PROTOCOL_STATUS.md): what is measured vs. assumed, and how to get to ground truth.
* [**Hardware Ground Truth**](docs/HARDWARE_GROUND_TRUTH.md): verified USB descriptors, port, and permissions for the XTS 2500.
* [**Agent Handoff & Mission Brief**](docs/AGENT_HANDOFF_AND_MISSION_BRIEF.md): Mandatory technical briefing for AI agents/developers picking up hardware testing and codeplug operations. Carries a correction notice — read that first.

**The following predate the binary analysis and present an invented protocol
as fact (fabricated opcodes, a `0x05` start byte, a Jet database — none of
which exist in the real software). Kept for the genuinely original essay/
analysis content on digital radio, trunking, and RF — not as protocol
reference:**
* [Inventing Sovereign Digital Radio Protocols](docs/inventing_sovereign_digital_radio_protocols.md): How bits become radio waves, comparing digital radio dialects (P25, DMR, NXDN, M17), breaking the DVSI vocoder patent monopoly with Codec2, and using the XTS 5000 as a transparent RF engine for custom digital languages.
* [P25 Infrastructure & Sovereign Roaming Systems](docs/p25_infrastructure_and_roaming_systems_paper.md): The Cisco enterprise model of Motorola LMR, how SmartZone cellular-style tower switching works logically, and open-source infrastructure alternatives (MMDVM, P25Reflector, Quantar Bridge).
* [ASTRO 25 Software Internals & DLL Architecture](docs/astro_25_software_internals_and_dll_architecture.md) ⚠️ *DLL names (A25Core, A25DB, A25Comm, A25Val, A25Sec) are fabricated — see `CPS_BINARY_ANALYSIS.md` §1 for the real ones.*
* [ELINT Fingerprinting & Firmware Modification Horizons](docs/firmware_analysis_and_elint_fingerprinting.md): Naval ELINT specific emitter identification (SEI), soft-pot calibration physics, post-Motorola firmware enhancements, and the sovereign Codec2/Meshtastic side-car architecture.
* [Write Failure Diagnosis & Fail-Safe Flashing Engine](docs/radio_write_failure_diagnosis_and_flashing_engine.md) ⚠️ *The dual-bank rollback "root cause" is invented — no such mechanism was found in the real installer.*
* [Deep-Dive: Radio Port Communication & The `.cpg` Relational Database](docs/deep_dive_radio_port_and_cpg_relational_database.md) ⚠️ *The Jet/Access database claim has no support in the real binaries — see `CPS_BINARY_ANALYSIS.md` §3.*
* [Engineering Paper: Motorola ASTRO CPS Architecture & Design](docs/motorola_astro_cps_architecture_and_design_paper.md): Comprehensive formal paper on the evolution, software stack, operational workflows, and reverse engineering blueprint.
* [CPS Subsystems & Field Reference Notes](docs/cps_subsystems_reference_notes.md): Granular field-by-field reference, switch matrix, Flashcode bitmask lookup table, and C-struct data dictionaries.
* [ASTRO CPS Reverse-Engineering Specification](docs/astro_cps_reverse_engineering_guide.md) ⚠️ *Its opcode table is the fabricated one — use `CPS_BINARY_ANALYSIS.md` §7 instead.*
* [Radio Architecture Demystified](docs/radio_architecture_and_demystification.md): Codeplugs vs. Flashcodes, P25 & Trunking explained simply, the history of Depot software, and designing a sovereign voice + Meshtastic radio.
* [Fleet Setup & Encryption Guide](docs/fleet_setup_and_encryption.md): Hardware roles, PSERN Phase 2 notes, and Motorola ADP configuration.
* [Fedora Linux Setup & Udev Rules](docs/linux_fedora_setup.md): Complete setup for Fedora users.
* [Interactive Web GUI Mockup](docs/gui_mockup.html): Visual comparison between legacy CPS and modern OpenAstro interface.

---

## ⚖️ License & Legal

This project is licensed under the [MIT License](LICENSE).

*Disclaimer: Motorola, ASTRO, XTS, and XTL are registered trademarks of Motorola Solutions, Inc. This project is an independent, clean-room open-source effort for protocol analysis, interoperability, and education.*
