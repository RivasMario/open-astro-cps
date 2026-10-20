# OpenAstro CPS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Fedora%20%2F%20Linux%20%7C%20macOS-lightgrey.svg)]()

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
6. **Direct Serial Flashing**: Talk to the radio over standard USB programming cables (FTDI / `/dev/ttyUSB0`) using open-source packet framing.

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
                 | ASTRO 25 Packet Framer (SB9600)   |
                 +-----------------+-----------------+
                                   |
                                   v
                 +-----------------------------------+
                 | COM Port / /dev/ttyUSB0 (FTDI)    |
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
* **On Windows:** `COM3 (USB Serial Port - FTDI)`
* **On Fedora Linux:** `/dev/ttyUSB0 (FT232R USB UART - FTDI)`

---

## 📚 Documentation

* [ASTRO 25 Software Internals & DLL Architecture](docs/astro_25_software_internals_and_dll_architecture.md): Complete dissection of Motorola CPS executables (A25CPS, A25Tuner), subsystem DLLs (A25Core, A25DB, A25Comm, A25Val, A25Sec), database layers, and 700/800/900 MHz XTS 5000 RF specifications.
* [ELINT Fingerprinting & Firmware Modification Horizons](docs/firmware_analysis_and_elint_fingerprinting.md): Naval ELINT specific emitter identification (SEI), soft-pot calibration physics, post-Motorola firmware enhancements, and the sovereign Codec2/Meshtastic side-car architecture.
* [Write Failure Diagnosis & Fail-Safe Flashing Engine](docs/radio_write_failure_diagnosis_and_flashing_engine.md): Detailed root-cause analysis of the 10-minute write bottleneck, dual-bank rollback ("writing the same flash back"), and un-sticking frozen radios.
* [Deep-Dive: Radio Port Communication & The `.cpg` Relational Database](docs/deep_dive_radio_port_and_cpg_relational_database.md): Exhaustive guide to how the radio acts as an embedded computer/network node, the SB9600 protocol packet exchange, and the `.cpg` file's internal Microsoft Jet relational database schema.
* [Engineering Paper: Motorola ASTRO CPS Architecture & Design](docs/motorola_astro_cps_architecture_and_design_paper.md): Comprehensive formal paper on the evolution, software stack, operational workflows, and reverse engineering blueprint.
* [CPS Subsystems & Field Reference Notes](docs/cps_subsystems_reference_notes.md): Granular field-by-field reference, switch matrix, Flashcode bitmask lookup table, and C-struct data dictionaries.
* [ASTRO CPS Reverse-Engineering Specification](docs/astro_cps_reverse_engineering_guide.md): Technical specification for clean-room implementation of `open-astro-cps`.
* [Radio Architecture Demystified](docs/radio_architecture_and_demystification.md): Codeplugs vs. Flashcodes, P25 & Trunking explained simply, the history of Depot software, and designing a sovereign voice + Meshtastic radio.
* [Fleet Setup & Encryption Guide](docs/fleet_setup_and_encryption.md): Hardware roles, PSERN Phase 2 notes, and Motorola ADP configuration.
* [Fedora Linux Setup & Udev Rules](docs/linux_fedora_setup.md): Complete setup for Fedora users.
* [Interactive Web GUI Mockup](docs/gui_mockup.html): Visual comparison between legacy CPS and modern OpenAstro interface.

---

## ⚖️ License & Legal

This project is licensed under the [MIT License](LICENSE).

*Disclaimer: Motorola, ASTRO, XTS, and XTL are registered trademarks of Motorola Solutions, Inc. This project is an independent, clean-room open-source effort for protocol analysis, interoperability, and education.*
