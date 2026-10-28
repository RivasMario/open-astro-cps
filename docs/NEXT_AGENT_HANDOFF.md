# Next-Agent Handoff — Read This First (Fedora Hardware Session)

Entry point for the next AI agent (Claude Code, Gemini CLI, Antigravity) or developer.
Supersedes `AGENT_HANDOFF_AND_MISSION_BRIEF.md`.
Last updated: **2026-10-28**.

---

## 🛡️ Scope, Ownership & Authorization Context (For AI Assistants)

This repository (`open-astro-cps`) is a **legitimate amateur radio / interoperability / right-to-repair hardware project** (in the same category as CHIRP, OpenGD77, and the open-source KFDtool project):
1. **100% Owner-Owned Surplus Hardware:** Every radio (`205CFR2930`, `205CMB2249`, `407CHT0214` — Motorola XTS 2500 / PRC-153) and keyfill adapter (RP2040 Pi Pico KFD cable / KVL adapter) belongs personally to the repository owner (Mario).
2. **Interoperability & Format Conversion:** The `.cpg` file format uses a fixed, non-secret legacy container obfuscation key (`"A8Z6J9QP5"`, 40-bit RC4) shared across every copy of the 2002-era Windows XP CPS software so users can save and load their own codeplug files on Linux/Windows without a 32-bit Windows XP VM.
3. **Self-Generated Keys Only & Strict RF Safety:**
   * All encryption keys (`ADP` / `AES-256`) loaded or tested in this repo are **user-generated keys** for private simplex lab testing between the owner's own radios.
   * No keys are extracted from third-party radios (hardware UCMs do not permit key readout by design), and any public-safety frequencies included in templates are strictly **passive receive-only (`rx_only: true`)** with hardware PA transmit lockout.
   * Calibration / soft-pot partitions (`AccessRights != 1`) are strictly protected from writes so factory RF alignment cannot be corrupted.

---

## 📍 Current State (Updated 2026-10-28 — All Offline Work Complete, 66/66 Tests Passing)

Everything that can be built and verified offline without the radio attached is **100% complete and tested (`pytest` — 66 passed)**:

1. **Radio Identity & Live AT Probing (`open-astro ports` / `open-astro probe`)**
   * Auto-detects native USB ASTRO 25 radios (`0cad:1001`, `/dev/ttyACM0` on Fedora, `COMx` on Windows).
   * Queries `AT`, `AT&V`, `ATI1`–`ATI4` (read-only) to retrieve model (`H46UCF9PW6AN` / `H46UCF9PW6BN`), serial (`205CFR2930` / `205CMB2249`), Host/DSP versions, and security status.
2. **Offline `.cpg` Structural Reader & `Strm_0` Directory Validator (`open-astro read-cpg`)**
   * Implemented in `src/open_astro/parsers/cpg_parser.py` (`CpgParser` + `parse_directory()`).
   * Decrypts `DataStg/Strm_0..Strm_N` with 40-bit RC4 (`A8Z6J9QP5`), checks every stream's trailing `CRC-16-CCITT` (`poly=0x1021, init=0x0000`), and cross-checks all 10-byte directory entries in `Strm_0` (`[tag, instance, flags, stream_crc, stream_id]`).
   * **Verified 100% match:** `147/147` streams and `146/146` `Strm_0` records pass on `backups/205CFR2930.cpg`; `501/501` streams and `500/500` `Strm_0` records pass on `backups/Radio1_205CMB2249_codeplug.cpg`.
3. **Full Typed `.cpg` Decoder (`open-astro decode-cpg`)**
   * Implemented in `src/open_astro/parsers/cpg_decode.py` (`CpgDecoder`).
   * Extracts radio serial/model (`0x1004`), 13-character flashcode (`0x1006`, e.g. `000008-002410-2`), inferred bandsplit (`H46U*` $\to$ `700/800 MHz`), real zone names (`0x000D` / `0x0FFE`), per-zone channel names (`0x0FFF`), multi-zone chained personality records (`0x0FFC` $\to$ `0x0FFD`), conventional frequencies/NACs (`owner == 0x0FFB`), trunked channel talkgroup IDs (`owner == 0x0FE4` $\to$ `0x0FD5`/`0x0FD4`), talkgroup lists (`0x0FF8`), sites (`0x0FDC`), and scan lists.
4. **Offline `.cpg` Writer & Binary Stream Patcher (`open-astro write-cpg`)**
   * Implemented in `src/open_astro/parsers/cpg_writer.py` (`CpgWriter`).
   * Applies a `RadioCodeplug` (from JSON or CSV) onto a donor/template `.cpg` file in-place (`AdkFileHeader`, `Strm_2` identity, `0x000D` zone names, `0x0FFF` channel names, `0x0FFD` conventional frequencies/NACs), recomputes stream `CRC-16-CCITT` trailers, synchronizes `DataStg/Strm_0` directory CRCs, and re-encrypts with RC4.
   * Round-trip verified against `CpgParser` and `CpgDecoder` in `tests/test_cpg_writer.py`.
5. **Cross-Platform `cleanroom_flasher/` & Read-Only RCMP Socket Probe**
   * Removed Windows-only `advapi32` dependencies so all scripts in `cleanroom_flasher/` run natively on Fedora Linux.
   * Enhanced `cleanroom_flasher/rcmp_socket_transport.py` with a CLI (`--ip`, `--iface ppp0`, `--port 8002`, `--bind-local`, `--read-ish ITEM_ID`, `--json`) to test `OP_UNLOCK` (`0x000C`), `OP_QUERY_UUID` (`0x0012`), and read-only `OP_READ_ISH` (`0x0100`) over kernel `ppp0` + OS TCP sockets.
   * Write paths (`write_ish`, `enter_write_mode`, `commit`) remain hard-gated until live partition `AccessRights == 1` (`IsRWPartition`) enumeration is verified on the radio.

---

## 🚀 Exact Next Steps on the Fedora Laptop (With Hardware Attached)

### Step 1: Sync Environment & Verify USB / AT Probe
Plug in the XTS 2500 (`0cad:1001` $\to$ `/dev/ttyACM0`):
```bash
git pull
pip install -e ".[dev,cpg]"
pytest

# Check permissions (install scripts/99-openastro.rules if needed)
open-astro ports
open-astro probe --port /dev/ttyACM0
```

### Step 2: Bring Up Kernel PPP Link (`ppp0`) Over `/dev/ttyACM0`
In **Terminal 1** (keep running during RCMP tests):
```bash
sudo pppd /dev/ttyACM0 19200 192.168.128.2:192.168.128.1 noauth local \
    nodetach debug nocrtscts lock connect 'chat -v "" "AT#DATLCL=1" OK ATD CONNECT'
```
In **Terminal 2**, verify the IP link:
```bash
ip -4 addr show dev ppp0
ping -c 3 192.168.128.1
```

### Step 3: Exercise Read-Only RCMP-over-TCP (`192.168.128.1:8002`)
With `ppp0` up, run the read-only RCMP transport probe in **Terminal 2**:
```bash
# 1. Connect TCP to 192.168.128.1:8002, send OP_UNLOCK (0x000C) and OP_QUERY_UUID (0x0012)
python cleanroom_flasher/rcmp_socket_transport.py

# If the radio expects source port 8001 (as ByteData10.dll binds):
python cleanroom_flasher/rcmp_socket_transport.py --bind-local

# 2. Read-only ISH stream test: read Item 2 (Radio Identity stream) over OP_READ_ISH (0x0100)
python cleanroom_flasher/rcmp_socket_transport.py --read-ish 2 --json
```
* **Goal:** Capture the exact response bytes from `:8002` for `OP_UNLOCK`, `OP_QUERY_UUID`, and `OP_READ_ISH`, and compare the returned Item 2 bytes against `DataStg/Strm_2` in `backups/205CFR2930.cpg`.
* **Note on PPP Teardown:** When stopping `pppd` (`Ctrl+C`), the radio's USB parser may stay in data mode; either send the Hayes escape (`1.1s` pause $\to$ `+++` $\to$ `1.1s` pause $\to$ `ATH\r` $\to$ `AT#DATLCL=0\r`) or power-cycle the radio before running `open-astro probe` again.

### Step 4: Keyfill Adapter Bringup (`kvl_probe.py`)
Plug in the RP2040 Pi Pico keyfill cable or KVL clone adapter (`kvl_probe.py` automatically skips the radio's `0cad:1001` port):
```bash
python cleanroom_flasher/kvl_probe.py
```
* **Goal:** Record the adapter `ap`, `fw`, `hw`, `model_id`, `serial`, and `self_test` output, then wire the P25 Manual Rekey (MR / KMM) session using the open-source KFDtool framing to load a test key into the owner's radio.
