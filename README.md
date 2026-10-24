# OpenAstro CPS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Fedora%20%2F%20Linux%20%7C%20macOS-lightgrey.svg)]()

> 🧭 **Working on this project (human or AI)? Start here:**
> **[docs/HANDOFF_RCMP_LIVE.md](docs/HANDOFF_RCMP_LIVE.md)** (current state, how-to,
> open work) and the **[docs index](docs/README.md)** (which docs are current,
> reference, historical, or unverified).

> ### Project status (2026-10-23)
> **Verified against real radios (XTS 2500: 407CHT0214, 205CFR2930, 205CMB2249):**
> * Live codeplug **read** over the USB cable with no dial-up/RAS setup --
>   `open-astro rcmp-dump --serial COMx` -- byte-equal to the radios' own backups.
> * Offline **`.cpg` decode** (`read-cpg`, typed zones/channels/frequencies/
>   CTCSS/NAC/bandsplit), including the `.cpg` object directory.
> * The RCMP protocol (records, opcodes, CRC) and the CPS codeplug schema
>   (partitions + access rights, all 169 block types), taken from the real CPS
>   binaries and cross-checked against live captures -- see
>   [docs/RCMP_WIRE_PROTOCOL.md](docs/RCMP_WIRE_PROTOCOL.md) and
>   [docs/CPS_ISH_SCHEMA.md](docs/CPS_ISH_SCHEMA.md).
>
> **Not finished:** codeplug writing/editing is not a supported feature. A
> research write was proven once on a test radio; there is no `write` command or
> channel editor, and the write-related code stays gated. Safety rule throughout:
> partition `0x82` (tuning/soft-pot calibration) is never written.
>
> Some older `docs/` were written without reading real Motorola code; two are
> confirmed fabricated and live in `docs/_unverified/`. The
> [docs index](docs/README.md) labels everything.

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

Start with the [**docs index**](docs/README.md). The current core set:

* [**Handoff: live RCMP read/write status**](docs/HANDOFF_RCMP_LIVE.md) -- state, how-to, open work
* [**RCMP wire protocol**](docs/RCMP_WIRE_PROTOCOL.md) -- records, opcodes, CRC, session shape
* [**CPS ISH schema**](docs/CPS_ISH_SCHEMA.md) -- partitions, access rights, block map, `.cpg` directory, what the CPS DLLs do
* [**`.cpg` file format**](docs/CPG_FILE_FORMAT.md) -- OLE container, RC4, per-object CRC
* [**Provenance audit**](docs/PROVENANCE_AUDIT.md) -- which claims are verified vs. contradicted
* [**Fedora Linux setup & udev rules**](docs/linux_fedora_setup.md)

---

## ⚖️ License & Legal

This project is licensed under the [MIT License](LICENSE).

*Disclaimer: Motorola, ASTRO, XTS, and XTL are registered trademarks of Motorola Solutions, Inc. This project is an independent, clean-room open-source effort for protocol analysis, interoperability, and education.*
