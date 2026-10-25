# OpenAstro CPS &mdash; Master Project Roadmap & DevOps Board

> **For Agents (Antigravity `agy`, Claude Code `claude`, Gemini CLI `gemini`):**  
> This file is the single source of truth for project priorities, fleet hardware status, and development backlog. When resuming work or switching agent sessions, read this file first.

---

## 📻 Hardware Fleet Inventory & Status

| Radio ID | Unit Name | Serial | Model | Band | Flashcode | UCM Socket | Status |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Radio 1** | "Facebook" | `205CFR2930` | `H46UCF9PW6AN` (Mod III) | 700/800 MHz | `000008-002410-2` | Empty (`R000000`) | **ONLINE.** 3-Zone fleet flashed. Ch 3 `ADP SECURE` active. |
| **Radio 2** | "Kent PD" | `205CMB2249` | `H46UCF9PW6BN` (Mod II) | 700/800 MHz | `000008-002410-2` | Empty (`R000000`) | **VERIFIED.** 3-Zone fleet flashed. Pending Ch 3 `ADP SECURE` match. |
| **Radio 3** | "Chris's" | `407CHT0214` | `H46KDF9PW6BN` (Mod II) | VHF (136-174) | `140001-000000-3` | Empty (`R000000`) | **ONLINE.** 16-Ch PNW VHF fleet flashed (2M, MURS, Marine, WX). |

---

## 📋 DevOps Kanban Board

```
+---------------------------------------------------------------------------------------+
|                                    DEVOPS BOARD                                       |
+--------------------+--------------------+--------------------+------------------------+
|      BACKLOG       |       TODO         |    IN PROGRESS     |  DONE (VERIFIED ON HW) |
+--------------------+--------------------+--------------------+------------------------+
| - GPU ADP Cracker  | - Match Radio 2    | - Button Mapping   | - Live RCMP Read/Write |
|   (Hashcat / Brute)|   Ch 3 to ADP      |   Pcap Capture &   | - Radio 1 & 2 Fleets   |
| - Mobile XTL Model | - Flashcode Patch  |   UI Assignment    | - Radio 3 PNW VHF Pack |
|   RCMP Parity      |   CLI (Q667 ADP)   | - Unified Mega App | - 0x82 Tuning Firewall |
| - LibreP25 CCH     | - SDR Decryption   |   Architecture     | - Model III Backlight  |
|   Homelab Trunking |   Harness (DSD-FME)|                    |   Hardware Resolution  |
+--------------------+--------------------+--------------------+------------------------+
```

---

## 🎯 Epics & Task Breakdown

### Epic 1: Button, Switch & Knob Control Mapping [IN PROGRESS]
- [x] Identify button definition stream: `0x003C:0` (8 buttons, 13-byte stride).
- [x] Extract button function lookup table from `PatPort.exe` (Light=6, Monitor=7, Scan=13, Nuisance=21, Emergency=11).
- [x] Resolve Model III purple button hardware conflict (hardwired to display backlight; software remapping suppressed by LCD controller).
- [ ] **Task 1.1:** Capture live button modification in CPS via USBPcap to verify exact handshake when user changes Side Button 2 / Orange Button.
- [ ] **Task 1.2:** Implement `open-astro buttons` CLI command allowing one-line mapping (e.g. `--orange unprogrammed --side2 monitor --side3 scan`).
- [ ] **Task 1.3:** Map top concentric toggle switch (`Ø` / `O`) for hardware Secure/Clear switching on conventional channels.

### Epic 2: FLASHcode Upgrade & Software ADP Activation [TODO]
- [x] Prove mathematically that DSP firmware (`R16.00.01` / `R19.50.01`) contains native ADP RC4-40 engine.
- [x] Locate FLASHcode storage in codeplug: Partition `0x81`, object `0x1006:0`.
- [x] Map bit position for `Q667` (ADP Software Encryption): Nibble 8, bit 4 (`000008-006410-X`).
- [ ] **Task 2.1:** Verify Mod-10 checksum calculation for `000008-006410-X`.
- [ ] **Task 2.2:** Add `open-astro flashcode-upgrade --add-adp` CLI tool to write `81:1006:0` over live RCMP.
- [ ] **Task 2.3:** Match Radio 2 (`205CMB2249`) Zone A with Channel 3 `ADP SECURE` to pair with Radio 1.

### Epic 3: SDR Over-The-Air Decryption & Audit [TODO]
- [ ] **Task 3.1:** Write `open-astro export-sdr` command to export current codeplug frequencies, NACs, and Talkgroups directly to **DSD-FME** and **SDRTrunk** channel formats.
- [ ] **Task 3.2:** Configure live RTL-SDR / HackRF monitoring harness on 851.5125 MHz.
- [ ] **Task 3.3:** Test live voice decryption using DSD-FME with known 40-bit key (`-K A1B2C3D4E5`).
- [ ] **Task 3.4 (Stretch Goal):** Implement 40-bit key brute-force audit demo (`hashcat` / `adp-brute`) to demonstrate cryptanalysis of captured P25 voice bursts.

### Epic 4: The OpenAstro "Mega App" [IN PROGRESS]
*Goal: Consolidate Portable CPS, Mobile CPS, Portable Depot, Mobile Depot, ASK Bypass, and Tuner Protection into one modern, cross-platform tool (CLI + Web UI).*

- [x] Cross-platform pure Python RCMP transport (Windows RAS / Linux `pppd` / serial PPP).
- [x] Hard safety boundary: Partition `0x82` write refusal firewall to protect RF soft-pots/calibration.
- [x] Codeplug parser & decoder (`open_astro.parsers.cpg_parser` & `cpg_decode`).
- [ ] **Task 4.1:** Consolidate Portable (`H46`) and Mobile (`H47` / XTL) schemas into a unified codeplug model.
- [ ] **Task 4.2:** Implement codeplug password bypass (read/clear password hash from `0x0047` / `0x0002` stream).
- [ ] **Task 4.3:** Implement zero-dongle trunking (edit `0x0FD0`..`0x0FDF` records without Motorola USB Advanced System Keys).
- [ ] **Task 4.4:** Modern browser-based Web GUI (FastAPI / Vue or lightweight HTML5/JS) replacing legacy 32-bit Windows MFC interfaces.

### Epic 5: Homelab P25 Central Station & Trunking [BACKLOG]
- [ ] **Task 5.1:** Set up MMDVM (Multi-Mode Digital Voice Modem) hotspot or base station on Raspberry Pi for conventional P25 repeater operation with Talkgroups & Call IDs.
- [ ] **Task 5.2:** Test P25 Phase 1 9600-baud Control Channel (CCH) broadcast using LibreP25 / Osmocom OP25 with SDR transmit hardware.

---

## 🛡️ Operating Rules for AI Agents (Antigravity & Claude)
1. **Never write to partition `0x82` (Tuning/Soft-Pots).** Refuse immediately if requested.
2. **Always ensure PPP is lowered (`tools/ppp_down.ps1`)** after write sessions so `COM7` is free for AT commands and CPS.
3. **Always verify against `backups/*.cpg`** before live replay writes.
4. **Be constructive and proactive:** Generate complete, runnable python code in `scratch/`, test thoroughly, and maintain documentation.
