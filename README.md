# OpenAstro CPS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**OpenAstro CPS** is an open-source codeplug engine, format converter, and serial programming toolkit for **Motorola ASTRO 25** radios:
* **Motorola XTS 2500 / PRC-153 IISR** (Integrated Intra-Squad Radio)
* **Motorola XTS 5000**
* **Motorola XTS 1500 / MT1500 / PR1500**
* **Motorola XTL 5000 / XTL 2500**

---

## 🎯 Motivation

Proprietary radio programming software (CPS) has historically been:
* Locked to archaic 32-bit Windows XP/7 operating systems.
* Gated behind expired commercial licenses, Advanced System Keys (ASK), and region locks.
* Storing configurations in opaque, proprietary binary archives (`.cpg`).

**OpenAstro** liberates these radios by providing:
1. **Human-Readable Configurations**: Full codeplugs stored in structured **JSON**, **YAML**, or **CSV spreadsheets**.
2. **Spreadsheet Workflow**: Edit channels in Excel, Numbers, or Google Sheets and import directly into your radio.
3. **RepeaterBook Compatibility**: Easily pull local ham and GMRS repeater frequencies into clean zones.
4. **Direct Serial Flashing**: Talk to the radio over standard USB programming cables (FTDI UART) using open-source packet framing.
5. **Cross-Platform**: Runs natively on modern Windows 11, macOS, and Linux without VMs.

---

## 🧱 Architecture

```
                 +-----------------------------------+
                 | Modern Web UI / CLI / Excel Sheets|
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
                 | USB Programming Cable (FTDI UART) |
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

```bash
# Clone the repository
git clone https://github.com/RivasMario/open-astro-cps.git
cd open-astro-cps

# Install in editable mode
pip install -e .
```

### 1. Generate a Fresh Codeplug Template
Generate a sample 2-zone template for a UHF PRC-153 / XTS 2500 (covers 70cm Ham Radio & GMRS):
```bash
open-astro new -o my_radio.json --model "Motorola XTS 2500 / PRC-153" --bandsplit "UHF 380-470 MHz"
```

### 2. View Channel Plan Summary
```bash
open-astro info my_radio.json
```
Output:
```
==========================================
 Radio Model  : Motorola XTS 2500 / PRC-153
 Bandsplit    : UHF Range 1 (380-470 MHz)
 Serial Number: SURPLUS_PRC153
 Flashcode    : 500008-000488-4
 Total Zones  : 2
 Total Chans  : 5
==========================================

[Zone 1: HAM 70CM] (3 channels)
  Ch  1: CALL 446.0     | Rx: 446.00000 | Tx: 446.00000 | Analog
  Ch  2: RPT 444.1      | Rx: 449.10000 | Tx: 444.10000 | Analog PL:107.2/107.2Hz
  Ch  3: P25 SIMPLEX    | Rx: 441.00000 | Tx: 441.00000 | ASTRO P25 NAC:$293 TG:1

[Zone 2: GMRS CHANS] (2 channels)
  Ch  1: GMRS 15        | Rx: 462.55000 | Tx: 462.55000 | Analog PL:67.0/67.0Hz
  Ch  2: GMRS RPT 15    | Rx: 462.55000 | Tx: 467.55000 | Analog PL:141.3/141.3Hz
```

### 3. Edit in Excel / Google Sheets
Convert your codeplug to a CSV spreadsheet, edit it, and convert it back:
```bash
# Export to CSV
open-astro to-csv my_radio.json channels.csv

# ... edit channels.csv in Excel ...

# Re-import back to JSON
open-astro from-csv channels.csv updated_radio.json
```

### 4. Detect Connected Programming Cables
```bash
open-astro ports
```

---

## 📊 Codeplug Data Schema

Channels support both **Analog FM** (CTCSS/DPL) and **Digital APCO Project 25 (P25 Phase 1)**:

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | String (up to 14 chars) | Channel label shown on the top/front display |
| `rx_frequency` | Float (MHz) | Receive frequency |
| `tx_frequency` | Float (MHz) | Transmit frequency (handles simplex & offsets) |
| `voice_type` | String | `"Analog"`, `"ASTRO P25"`, or `"Mixed Mode"` |
| `rx_pl_tone` / `tx_pl_tone` | Float (Hz) | CTCSS sub-audible tone (e.g. `107.2`) |
| `rx_dpl_code` / `tx_dpl_code` | Integer | Digital coded squelch (e.g. `023`, `074`) |
| `rx_nac` / `tx_nac` | Hex String | P25 Network Access Code (`$293` default unmuted) |
| `talkgroup_id` | Integer | P25 Digital Talkgroup ID |
| `power_level` | String | `"High"` (5W) or `"Low"` (1W) |
| `secure_strapping` | String | `"Clear"`, `"Secure"`, or `"Selectable"` |

---

## 🗺️ Roadmap

- [x] Python ASTRO 25 data models & table schema mapping
- [x] JSON parser & round-trip serializer
- [x] CSV / Excel importer and exporter
- [x] SB9600 packet framing & checksum engine
- [ ] Direct serial radio memory read (`0x14` opcode block dumping)
- [ ] Direct serial radio memory flash (`0x15` opcode block writing)
- [ ] Binary `.cpg` decompiler / compiler
- [ ] Web-based graphical channel manager (React + Tailwind)

---

## ⚖️ License & Legal

This project is licensed under the [MIT License](LICENSE).

*Disclaimer: Motorola, ASTRO, XTS, and XTL are registered trademarks of Motorola Solutions, Inc. This project is an independent, clean-room open-source effort for protocol analysis, interoperability, and education.*
