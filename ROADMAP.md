# OpenAstro CPS &mdash; Master Project Roadmap & DevOps Board

> **For Agents (Antigravity `agy`, Claude Code `claude`, Gemini CLI `gemini`):**  
> This file is the single source of truth for project priorities, fleet hardware status, and development backlog. When resuming work or switching agent sessions, read this file first.

---

## 📻 Hardware Fleet Inventory & Status

| Radio ID | Unit Name | Serial | Model | Band | Flashcode | UCM Socket | Status |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Radio 1** | "Facebook" | `205CFR2930` | `H46UCF9PW6AN` (Mod III) | 700/800 MHz | `000008-002410-2` | Empty (`R000000`) | **ONLINE.** 3-Zone fleet flashed. Ch 3 `ADP SECURE` active. |
| **Radio 2** | "Kent PD" | `205CMB2249` | `H46UCF9PW6BN` (Mod II) | 700/800 MHz | `000008-002410-2` | Empty (`R000000`) | **ONLINE.** 3-Zone fleet flashed. Ch 3 `ADP SECURE` active (Matched to R1). |
| **Radio 3** | "Chris's" | `407CHT0214` | `H46KDF9PW6BN` (Mod II) | VHF (136-174) | `140001-000000-3` | Empty (`R000000`) | **ONLINE.** 16-Ch PNW VHF fleet flashed (2M, MURS, Marine, WX). |
| **Radio 4** | "Redmond PD" | `721CLZ0655` | `H18UCF9PW6AN` (Mod III) | 700/800 MHz | `400008-002000-0` (Option A `400008-006000-1` staged) | Empty (`R000000`) | **ONLINE.** Flashed with ADP security subsystem (Key 1 armed), 13-Zone/194-Ch Redmond PD & King County fleet + working Z-scan list preserved. POST clean. |

---

## 📋 DevOps Kanban Board

```
+---------------------------------------------------------------------------------------+
|                                    DEVOPS BOARD                                       |
+--------------------+--------------------+--------------------+------------------------+
|      BACKLOG       |       TODO         |    IN PROGRESS     |  DONE (VERIFIED ON HW) |
+--------------------+--------------------+--------------------+------------------------+
| - ADP Security Audit  | - Match Radio 2    | - Button Mapping   | - Live RCMP Read/Write |
|   (Cryptanalysis Verification)|   Ch 3 to ADP      |   Pcap Capture &   | - Radio 1 & 2 Fleets   |
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
- [x] **Task 1.2:** Implement `open-astro buttons` CLI command allowing one-line mapping (`--set orange=monitor --set side2=scan`). Fully implemented in `src/open_astro/parsers/button_edit.py` and `cli.py`; 13/13 tests pass.
- [ ] **Task 1.3:** Map top concentric toggle switch (`Ø` / `O`) for hardware Secure/Clear switching on conventional channels.

### Epic 2: FLASHcode Upgrade & Software ADP Activation [TODO]
- [x] Prove mathematically that DSP firmware (`R16.00.01` / `R19.50.01`) contains native ADP RC4-40 engine.
- [x] Locate FLASHcode storage in codeplug: Partition `0x81`, object `0x1006:0`.
- [x] Map bit position for `Q667` (ADP Software Encryption): Nibble 8, bit 4 (`000008-006410-3`).
- [x] **Task 2.1:** Verify Mod-10 checksum. SOLVED/VERIFIED-BIN — PatPort.exe `conCalculateFlashcode` @ `0xa0b631` = standard Luhn mod-10 over the 12 nibble values (even-from-left doubled). Q667 upgrade → `000008-006410-3`. See `docs/FLASHCODE_AND_EEPROM_MAP.md` §7.1.
- [x] **Task 2.2:** `open-astro flashcode-upgrade` CLI built (`--add-adp` / `--add N:B` / `--remove` / `--kitchen-sink` / `--set`). Offline: flips bits, computes the verified check digit, emits a `81:1006:0` replay-write flag with hardware-gated + 0x81-lockout warnings. Does NOT transmit (0x81 needs UnlockSecurity first). Tests in `tests/test_flashcode.py`.
- [x] **Task 2.3:** Match Radio 2 (`205CMB2249`) Zone A with Channel 3 `ADP SECURE` to pair with Radio 1. [VERIFIED ON HARDWARE]

### Epic 3: SDR Over-The-Air Decryption & Audit [TODO]
- [x] **Task 3.1:** Write `open-astro export-sdr` command to export current codeplug frequencies, NACs, and Talkgroups directly to **DSD-FME** (channel/group CSVs) and **SDRTrunk** (playlist XML). Implemented in `src/open_astro/exporters/sdr_export.py` and `cli.py`; 5/5 tests pass.
- [ ] **Task 3.2:** Configure live RTL-SDR / HackRF monitoring harness on 851.5125 MHz.
- [ ] **Task 3.3:** Test live voice decryption using DSD-FME with known 40-bit key (`-K A1B2C3D4E5`).
- [ ] **Task 3.4 (Stretch Goal):** Implement 40-bit key 40-bit key recovery verification in SDR capture of captured P25 voice bursts.

### Epic 4: The OpenAstro "Mega App" [IN PROGRESS]
*Goal: Consolidate Portable CPS, Mobile CPS, Portable Depot, Mobile Depot, ASK Software Key Support, and Tuner Protection into one modern, cross-platform tool (CLI + Web UI).*

- [x] Cross-platform pure Python RCMP transport (Windows RAS / Linux `pppd` / serial PPP).
- [x] Hard safety boundary: Partition `0x82` write refusal firewall to protect RF soft-pots/calibration.
- [x] Codeplug parser & decoder (`open_astro.parsers.cpg_parser` & `cpg_decode`).
- [x] **Task 4.5:** Ground-truth field schema decoding (`schema/field_layouts.json`). Decodes 35-byte 0x0FFB records inside 0x0FFD tables (NACs, frequencies, squelch/CTCSS/DPL, simplex flag) via `PersonalityRecord`; 19/19 tests pass.
- [x] **Task 4.0:** Standalone Virtual Radio RCMP Server (`tools/virtual_radio.py`). Serves partition 0x80/0x81 over Port 8002 TCP, enforces 0x82 firewall; verified with `tests/test_virtual_radio.py`.
- [ ] **Task 4.1:** Consolidate Portable (`H46`) and Mobile (`H47` / XTL) schemas into a unified codeplug model.
- [ ] **Task 4.2:** Implement codeplug password recovery (read/clear password hash from `0x0047` / `0x0002` stream).
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
