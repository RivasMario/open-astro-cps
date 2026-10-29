# Engineering Log: Motorola ASTRO 25 Software ADP (Q667) Reverse Engineering & Autonomous Deployment

**Date:** 2026-10-24  
**Project:** `open-astro-cps`  
**Target Hardware:**  
- **Radio 1:** Motorola XTS2500 Model II 700/800 MHz (Facebook fleet, Serial `205CFR2930`, Model `H46UCF9PW6AN`)
- **Radio 2:** Motorola XTS2500 Model II 700/800 MHz (Kent PD fleet, Serial `205CMB2249`, Model `H46UCF9PW6BN`)

---

## Executive Summary

1. **Factory FLASHcode Bypassed & Upgraded:**  
   Both radios were upgraded from factory basic analog/digital FLASHcodes (`000008-002410-2`) to the full digital encryption suite **`500008-00048C-7`**. This activates native 40-bit RC4 software ADP encryption (`Q667`), ASTRO Digital CAI (`Q806`), SmartZone OmniLink (`Q173`), and Front Panel Programming (`Q53`) without requiring an internal hardware UCM crypto daughtercard.
2. **Motorola Depot MDF Bug Diagnosed & Patched:**  
   Identified a vendor bug where Motorola copy-pasted mobile code `G857` 202 times into portable MDF tables (`patphopt*.mdf`), causing Depot to throw *"G858 not supported by model"* and crash codeplug generation. Patched all MDF tables in `Program Files (x86)`.
3. **Hardware Collar Switch Hardware Bug Solved:**  
   Discovered why the `Ø` lock icon was either suppressed or forced across all channels: Switch 60 (the rotary concentric collar switch) was mapped to `Secure/Clear Mode` (`0x18`/`0x19`). Because Model II portables lack a physical collar switch, the floating hardware pin forced the radio into Clear or Secure mode. Decoupled Switch 60 to `Unprogrammed` (`0x23`), restoring clean channel autonomy.
4. **Channel Strapping Architecture Demystified:**  
   Reverse-engineered the exact 35-byte channel strapping record at offset 24–28 of object `0x0FFD:0`:
   - `0x00000000` (`0x00` trailer): **Strapped Clear** (encryption strictly disabled; no lock icon).
   - `0x00000140` (`0x40` trailer): **Strapped Secure** (ADP encryption forced; `Ø` lock icon displayed).
   - `0x00000080` (`0x80` trailer): **Selectable** (follows physical switch state).
5. **Matched 3-Channel Fleet Pack Deployed & Verified:**  
   Both radios flashed and verified over native RCMP protocol on port 8002:
   - Channel 1: `OPEN ASTRO` (851.5125 MHz, Clear P25, no lock icon)
   - Channel 2: `TEAM ANALOG` (853.0125 MHz, Clear Analog FM, no lock icon)
   - Channel 3: `ADP SECURE` (851.5125 MHz, Secure ADP P25, `Ø` Lock Icon active, Key 1 = `A1B2C3D4E5`)
6. **Partition 0x82 Firewall Enforced:**  
   Zero write operations were permitted to touch partition `0x82` (RF factory calibration), guaranteeing zero RF misalignment or transmitter bricking.
7. **Clean Tooling Created:**  
   Packaged the full pipeline into `tools/flash_radio_adp.py` for 1-command dry-run validation and hardware flashing.

---

## Detailed Technical Findings

### 1. MDF Table Patching
Motorola's `PatPortDepot.exe` relies on binary MDF files to populate dropdowns. When attempting to create an ADP codeplug for Model `H46UCF9PW6BN`, Depot halted with *"G858 not supported by model"*. Inspection of `patphopt.mdf`, `patphopt_a.mdf`, `patphopt_b.mdf`, and `patphopt_c.mdf` revealed 202 occurrences of `G857` (a mobile ASTRO option) erroneously embedded into portable model rows. Replacing all occurrences of `G857` with 4 spaces (`0x20202020`) eliminated the popup and restored full codeplug generation.

### 2. RCMP Replay & Object Injection Engine
Live writing was executed via userspace PPP over Windows modem (`OpenAstroRadio`) on `COM7` communicating to the radio's internal Linux TCP stack at `192.168.128.1:8002`.
Each session was compiled using `rcmp_replay_write`:
- Base transaction framing: `010600` (Begin) &rarr; `0101` writes &rarr; `01078000` (Partition Checksum) &rarr; `010601` (Commit & Reboot).
- Total records per write: 195 records (158 write objects). Every single write object was verified to re-encode byte-exact against CCITT CRC-16.

### 3. The 12 Missing Secure Subsystem Objects
Comparing the working Depot gold-master codeplug (`205CMB2249_ADP.cpg`) against legacy CPS captures revealed that standard CPS codeplugs omitted 12 critical objects required for encryption:
- `0x0034:0`: Radio-wide Master Enable (16 bytes, ending in `0003`).
- `0x0035:0` & `0x0036:0`: Secure Voice parameters.
- `0x0037:0` & `0x0038:0`: Common Key Reference (CKR) multikey table (CKR1–CKR8).
- `0x005D:0`: 40-bit Software Key Table (Key 1 = `A1B2C3D4E5`).
- `0x004E:0`, `0x0F9F:0`, `0x0FA0:0`: Secure list references.
- `0x0FE8:0` through `0x0FEB:0`: Secure zone call structures.

Injecting these 12 objects alongside the unprogrammed switch table fully armed the radio's native encryption engine.

---

## Verification & Status

| Radio Unit | Serial | Model | FLASHcode | Ch 1 (Clear) | Ch 2 (Clear) | Ch 3 (ADP) | `Ø` Icon |
|---|---|---|---|---|---|---|---|
| **Radio 1** | `205CFR2930` | `H46UCF9PW6AN` | `500008-00048C-7` | OK | OK | OK | Verified |
| **Radio 2** | `205CMB2249` | `H46UCF9PW6BN` | `500008-00048C-7` | OK | OK | OK | Verified |

Both units are 100% matched and ready for over-the-air communication.
