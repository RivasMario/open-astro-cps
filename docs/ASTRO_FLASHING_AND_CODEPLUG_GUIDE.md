# Astro 25 Flashing & Code‑Plug Guide

## Overview
This document explains, in a **human‑readable** and **AI‑friendly** way, how the Open Astro 25 flashing and code‑plug workflow works. It covers:
1. The **radio protocol** (RCMP) – session handling, the secret handshake, flash‑code writes, and code‑plug reads.
2. The **virtual radio server** used for safe testing.
3. The **capture pipeline** that produces JSONL and PCAP files.
4. The **helper scripts** that automate flashing, code‑plug extraction and diffing.
5. How to **extend** the workflow or integrate it into other tools.

---

## 1️⃣ Radio Protocol Basics (RCMP)
| Layer | Description |
|-------|-------------|
| **Session** | Opcode `0x0106` (SESSION) opens a TCP‑wrapped PPP link. The radio replies with `0x8106` (SESSION_ACK). |
| **Identity** | Opcodes `0x0012` (MODEL), `0x0011` (SERIAL), `0x000F` (DEPOSIT) retrieve static radio information. |
| **Secret Handshake** | Opcode `0x0107` with tag `0x2011` requests a **32‑byte seed**. The radio returns the seed; the client must reply with the seed **scrambled by the NextGen10 LFSR** (`unlock_response`). The radio acknowledges with `0x8107`. This must succeed **before any write to partition 0x81**. |
| **Flash‑Code Write** | Opcode `0x0100` (WRITE) to **partition 0x81** (flashcode). Objects `0x1004` and `0x1006` contain the flashcode strings (e.g. `540408-00078C-6` for XTS 2500). The radio ACKs each write with `0x8100`. |
| **Code‑Plug Read** | Opcode `0x0100` to **partition 0x80** (code‑plug). Object IDs start at `0x000A` (decimal 10) and go up to `0x3FFF`. The radio streams each object with a `READ_ACK` (`0x8100`). |
| **Session End** | Opcode `0x0106` with flag `0x01` terminates the session. |

**Key rule:** *Writes to partition 0x81 are rejected unless the UnlockSecurity handshake succeeds.*

---

## 2️⃣ Virtual Radio Server (`tools/virtual_radio.py`)
The virtual radio emulates the real Astro 25 firmware and implements the same RCMP state machine. It supports:
- **Lock‑security** (`--lock-security`) – forces the handshake.
- **Challenge‑security** (`--challenge-security`) – validates the LFSR response.
- **Capture flags** `--capture-jsonl` and `--capture-pcapped` – automatically write the traffic to `captures/live_virtual_radio.jsonl` and `captures/live_virtual_radio.pcap`.
- **Partition firewall** – partition 0x82 is **strictly blocked**; any write results in an error.

Running the server:
```bash
python tools/virtual_radio.py \
    --host 127.0.0.1 --port 8002 \
    --lock-security --challenge-security \
    --capture-jsonl --capture-pcap
```
It stays listening until killed (Ctrl‑C). It can be launched as a background daemon from the helper scripts.

---

## 3️⃣ Capture Pipeline
All scripts funnel RCMP traffic through the virtual radio with capture enabled. Two file formats are produced:
- **JSONL** – one JSON object per packet, easy to parse programmatically.
- **PCAP** – standard Wireshark format, useful for visual inspection.

The filenames follow a clear convention:
```
captures/<description>_<timestamp>.<ext>
```
Examples:
- `captures/xts2500_kitchen_sink.jsonl`
- `captures/codeplug_read_codeplug_20261028_153212.pcap`

---

## 4️⃣ Helper Scripts (what we already have)
| Script | Purpose |
|--------|---------|
| `tools/flash_all_radios.py` | Starts the virtual radio, flashes **both** XTS 2500 and XTS 5000 to the *kitchen‑sink* flashcode, captures the traffic, and stops the server. |
| `tools/sim_codeplug.py` | Performs a full **code‑plug read** (partition 0x80) against the virtual radio and stores the capture. |
| `tools/diff_captures.py` | Normalises two JSONL capture files (drops timestamps, sorts keys) and prints a unified diff – ideal for verifying that a simulated run matches a historic capture. |
| `docker/web_dashboard.py` | Minimal web UI (`http://127.0.0.1:8006/`) with two buttons: *Simulate CPS Identity + Read* and *Simulate Unlock + Write*. A new endpoint `/api/flash-all` was added to invoke `flash_all_radios.py` via HTTP. |

All scripts are **pure‑Python**, require only the standard library, and work on Windows, Linux, and macOS (provided Python 3.12+ is installed).

---

## 5️⃣ Full End‑to‑End Workflow (step‑by‑step)
1. **Start the virtual radio with capture** (handled automatically by the scripts).
2. **Flash the radio** – run `python tools/flash_all_radios.py`. Captures are saved as `captures/xts2500_kitchen_sink.*` and `captures/xts5000_kitchen_sink.*`.
3. **Read the code‑plug** – run `python tools/sim_codeplug.py`. Captures are saved as `captures/codeplug_read_*.jsonl/.pcap`.
4. **Verify** – compare any capture to the original reference (`captures/cps_20261023_083952_decoded.json`) using:
   ```bash
   python tools/diff_captures.py captures/xts5000_kitchen_sink.jsonl captures/cps_20261023_083952_decoded.json
   ```
   The diff should be empty (timestamps are stripped automatically).
5. **Optional UI** – open `http://127.0.0.1:8006/` and click **Flash All** (via the `/api/flash-all` endpoint) or the other buttons.

---

## 6️⃣ Extending / Integrating
- **Real hardware** – replace `127.0.0.1:8002` with the IP of a physical radio (or a serial‑to‑TCP bridge). Keep the handshake logic untouched.
- **Custom flashcode** – edit the flash scripts (`tools/flash_radio_adp.py` / `flash_radio4_adp.py`) to modify the payload strings. The protocol handling stays the same.
- **Automation** – the new unified CLI (`open_astro.py`, see next section) can be called from CI pipelines to verify that any code change does not break the handshake or the code‑plug format.

---

## 7️⃣ Next Step – Unified Open‑Astro CLI (`open_astro.py`)
A lightweight command‑line tool that brings the three helper scripts together under one interface:
```bash
python open_astro.py flash   # flash both radios (captures saved automatically)
python open_astro.py read    # read the full code‑plug (captures saved automatically)
python open_astro.py diff <capture1> <capture2>  # run the diff utility
```
The CLI will also expose flags to point at a real radio, choose a specific model, or force a custom flashcode.

The implementation follows below.

---

## 📄 Document generated for humans & AIs
*File:* `docs/ASTRO_FLASHING_AND_CODEPLUG_GUIDE.md`
*Location:* `C:/Users/v-mariorivas/open-astro-cps/docs/ASTRO_FLASHING_AND_CODEPLUG_GUIDE.md`

---

*End of documentation.*