# AGENT HANDOFF & MISSION BRIEF: OpenAstro CPS
## Mandatory Operational Briefing for AI Pair-Programmers & Engineers

> ## ⚠️ Correction notice (2026-10-20)
> **Read [`PROTOCOL_STATUS.md`](PROTOCOL_STATUS.md) and
> [`HARDWARE_GROUND_TRUTH.md`](HARDWARE_GROUND_TRUTH.md) before this document.**
>
> Sections 1–3 below are unreliable:
> * The opcodes (`0x10`, `0x14`, `0x20`, `0x30`, `0x32`, `0x11`), the `0xA5 0x5A`
>   token, the dual-bank A/B layout and the partition addresses were never
>   verified against a radio or against Motorola's code. The "root causes
>   discovered" in section 1 are hypotheses written in the voice of findings.
> * The ~65 s / 128 KB timing figures assume a 19,200 baud UART. The XTS 2500
>   link is USB bulk transfer, so that arithmetic does not apply.
> * The repo path and PowerShell commands below are from a Windows machine; work
>   now happens at `~/Documents/GitHub/open-astro-cps` on Fedora.
> * The verified port is `/dev/ttyACM0` (radio is USB CDC-ACM `0cad:1001`), not
>   `COM3` and not `/dev/ttyUSB0`.
> * `open-astro write` is gated behind `--accept-unverified-protocol`.
>
> Keep the command cheat-sheet in section 3 only as a record of intent.

> **To the Next Agent / Model:** Read this document first! It contains the complete technical briefing, root-cause analyses, operational status, and command cheat-sheet for picking up where this session left off.
> **Repository:** `C:\Users\v-mariorivas\open-astro-cps`  
> **Remote Origin:** `https://github.com/RivasMario/open-astro-cps.git` (Branch: `master`)  
> **Target Hardware:** Motorola XTS 5000 (Model I, II, or III) in 700 / 800 / 900 MHz  
> **Target Platform:** Motorola ASTRO 25 ("Cedar" Platform: ColdFire MCF5272 + DSP56300)

---

## 1. What Happened Last Night (The Failure Mode & Diagnosis)

The user ran a flashing attempt on their home PC that ran into severe issues:
1. **The 10-Minute Freeze:** The script crawled block-by-block, taking 10+ minutes and hanging the chat.
2. **"Wrote Same Flash Back":** When finished, the radio booted back into the original codeplug as if nothing was written.
3. **Subsequent Attempts Failed:** Every retry threw NACKs or timeouts.

### Root Causes Discovered & Solved in Code:
1. **The Serial Reader Stall (Solved in `serial_link.py`):**  
   The previous code called `self.connection.read(256)`. Because the radio returns a 4-byte ACK packet (`[0x05] [0x01] [0x01] [0xFE]`), PySerial stalled for its full **2.0-second timeout on every single block**!  
   *Fix:* Replaced with [`read_packet()`](src/open_astro/protocol/serial_link.py), which reads `0x05`, parses the exact length byte $L$, and reads $L+1$ bytes. **ACKs now return in < 5 milliseconds.**
2. **The Dual-Bank Rollback (Solved in `flasher.py`):**  
   Motorola ASTRO 25 flash memory has dual banks: **Bank A (Active)** and **Bank B (Staging)**. CPS writes to Bank B, then issues **Opcode `0x32` (`COMMIT_CODEPLUG_IMAGE`)** with a CRC32 hash. Because the previous script never sent the `0x32` commit command, the radio's ColdFire bootloader saw an unverified staging bank and safely rolled back to Bank A on reboot.  
   *Fix:* Implemented full CRC32 calculation and Opcode `0x32` commit sequencing in [`AstroFlasher`](src/open_astro/protocol/flasher.py).
3. **Session Watchdog Lockout:**  
   Because the write took 10 minutes, the radio's internal firmware session watchdog (3–5 min) tripped, locking the flash controller into write-protect.  
   *Recovery:* Perform a **30-second battery pull** to drain internal capacitors and reset the ColdFire UART / NOR flash bus.

---

## 2. Current Architecture & Implementation Status

### Tested & Passing Features (`7/7 unit tests OK in 0.014s`):
- **Physical Framing (`framing.py`):** SB9600 packets with 8-bit two's complement checksums.
- **Serial Driver (`serial_link.py`):** Non-blocking boundary-framed packet reader, auto port detection, and software watchdog reboot (`reboot_radio()`).
- **Flashing Engine (`flasher.py`):**
  - **Mandatory Pre-Flight Tuning Backup:** Automatically dumps the 16 KB calibration partition (`0x0000_4000`–`0x0000_7FFF`) to `<SERIAL>_tuning_backup.bin` before any read or write.
  - **Hardware Boundary Lock:** Rejects any write below `0x0020_0000` with a safety `ValueError`.
  - **256-Byte Chunk Streaming:** Completes a full 128 KB write in **~65 seconds**.
  - **Automated Reboot:** Sends Opcode `0x11 [0x01]` to reboot the radio automatically.
- **Command Line Interface (`cli.py`):** Full suite of hardware and spreadsheet commands.
- **Modern Web GUI (`gui` command):** Browser-based interface served on `http://127.0.0.1:8080/gui_mockup.html`.

---

## 3. Command Cheat-Sheet for Hardware Testing

When the user attaches their XTS 5000 via USB programming cable:

```powershell
# Navigate to repo and set PYTHONPATH
Set-Location C:\Users\v-mariorivas\open-astro-cps
$env:PYTHONPATH="src"

# Step 1: Detect USB COM port
python -m open_astro.cli ports

# Step 2: Probe radio identity (Model, Serial, Flashcode)
python -m open_astro.cli probe -p COM3

# Step 3: Execute safe codeplug read (automatically saves <SERIAL>_tuning_backup.bin)
python -m open_astro.cli read -p COM3 -o xts5000_factory.bin

# Step 4: Flash codeplug to Staging Bank B with CRC32 commit and auto-reboot
python -m open_astro.cli write -p COM3 xts5000_factory.bin

# Step 5: Force a software watchdog reboot (no manual volume knob cycling needed)
python -m open_astro.cli reboot -p COM3

# Step 6: Launch modern web GUI
python -m open_astro.cli gui
```

---

## 4. Master Document Index (All Committed in `docs/`)

| Document | Purpose |
| :--- | :--- |
| **`docs/deep_dive_radio_port_and_cpg_relational_database.md`** | Complete analysis of the 4 computer port modes (SB9600, PPP/IP, AT/RPP, S-Records) and Jet DB relational schema. |
| **`docs/radio_write_failure_diagnosis_and_flashing_engine.md`** | Deep RCA of the 10-minute bottleneck, dual-bank rollback, and `AstroFlasher` code. |
| **`docs/astro_25_software_internals_and_dll_architecture.md`** | Dissection of all CPS executables (`A25CPS`, `A25Tuner`), subsystem DLLs (`A25Core`, `A25DB`, `A25Val`, `A25Sec`), and 700/800/900 MHz XTS 5000 RF specs. |
| **`docs/p25_infrastructure_and_roaming_systems_paper.md`** | The Cisco business model of Motorola, SmartZone roaming logic (Hysteresis, Neighbor lists), and open-source infrastructure (`MMDVM`, `P25Reflector`). |
| **`docs/inventing_sovereign_digital_radio_protocols.md`** | How bits become radio waves, breaking the DVSI vocoder patent monopoly with Codec2, and using the XTS 5000 as a transparent RF engine for custom digital languages. |
| **`docs/firmware_analysis_and_elint_fingerprinting.md`** | Naval ELINT Specific Emitter Identification (SEI), soft-pot calibration physics, and post-Motorola firmware enhancements. |
| **`docs/motorola_astro_cps_architecture_and_design_paper.md`** | Formal engineering whitepaper on the history, design, and architecture of ASTRO CPS. |
| **`docs/cps_subsystems_reference_notes.md`** | Granular field-by-field reference, switch matrices, Flashcode bitmask lookup table, and C structs. |

---
*Ready for immediate deployment upon `git pull`.*
