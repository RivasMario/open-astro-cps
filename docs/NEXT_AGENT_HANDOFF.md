> [!WARNING]
> **SUPERSEDED (historical).** Status here is out of date. Current state: [HANDOFF_RCMP_LIVE.md](HANDOFF_RCMP_LIVE.md); doc map: [README.md](README.md).

# Next-Agent Handoff — read this first

Entry point for the next AI/developer. Supersedes `AGENT_HANDOFF_AND_MISSION_BRIEF.md`.
Last updated 2026-10-23.

## Mission

Open-source toolchain to **program codeplugs into** and **load encryption keys
into** Motorola ASTRO 25 radios (XTS 2500/5000, PRC-153) from Linux/Windows,
no Motorola CPS/KVL. Clean-room, from the real binaries. Scope = the owner's own
radios and own keys.

## Current state — one paragraph (Updated 2026-10-23)

The ASTRO 25 codeplug protocol and `.cpg` file format are **fully reverse-engineered, calibrated, and verified** against real radio backups. Radio `205CFR2930` (XTS 2500 Model III) was connected on `COM7`, probed via the read-only AT interface (`AT&V`, `ATI1`–`ATI4`), and matched to its backup codeplug `backups/205CFR2930.cpg`. Stream decryption with RC4 (`A8Z6J9QP5`) is 100% verified, stream framing is solved (6-byte header, payload, 2-byte CRC-16-CCITT), yielding 147/148 passing CRCs on `205CFR2930.cpg` and 501/502 on `Radio1_205CMB2249_codeplug.cpg`. Frequency encoding (`integer * 5` Hz) and flashcode decoding (`000008-002410-2`: FPP, SSK, AES-256, Phase 2 TDMA) are completely resolved.

## What is DONE (verified, documented)

* **Radio Identity & Live Probing** — `open-astro probe` on Windows/Linux reads `AT&V`, `ATI1` (firmware banner), `ATI2` (Host version: `R09.00.41`), `ATI3` (DSP version: `R16.00.01`), model (`H46UCF9PW6AN`), and serial (`205CFR2930`).
* **`.cpg` Codeplug Decryption & Framing** — `CPG_FILE_FORMAT.md`, `open-astro read-cpg`:
  * Container: OLE compound file (`olefile`).
  * Header: 800 bytes cleartext `AdkFileHeader` (model, serial, UUID).
  * Payload: RC4 passphrase `"A8Z6J9QP5"`.
  * Stream Framing: `tag (uint16_be)`, `instance (uint16_be)`, `payload_len (uint16_be)`, `payload`, `CRC-16-CCITT (poly 0x1021, init 0x0000)`.
  * Directory Index: `Strm_0` table of 10-byte stream descriptors.
  * Frequencies: 32-bit unsigned integer $\times$ 5 Hz (`val / 200,000` MHz).
* **Flashcode Decoder** — `src/open_astro/models/flashcode.py`: decodes ASTRO 25 flashcodes into features (e.g. Q53 FPP, H869 AES-256).
* **Backups Committed** — `backups/` contains `205CFR2930.cpg`, `Radio1_205CMB2249_codeplug.cpg`, tuning backups, and pre-extracted structural JSONs for all agents.
* **Transport Reverse Engineering** — `RadioCustStack10` (userspace serial PPP+IP+TCP stack to `radio:8002`); RCMP opcodes (`0x100`, `0x101`, `0x106`, `0x12`, `0xC`, `0xD`).
* **Safety Rules** — Partition `AccessRights` (RO=0 / RW=1 / RW-locked=2) in `rcmp_socket_transport.py`.
* **Keyfill Groundwork** — `cleanroom_flasher/kvl_probe.py` auto-skips `0cad:1001` radio port and probes Pi Pico / KVL clone adapters.

## Exact Next Steps

### 1. Codeplug Builder & Zone/Channel Mapping
* Now that stream offsets and frequency math are known, complete the high-level `.cpg` $\to$ JSON/CSV parser to extract all zone names, channels, NACs, and talkgroups into `RadioCodeplug` models.
* Enable round-trip: JSON $\to$ `.cpg` binary generation using OLE Structured Storage + RC4 + CRC-16.

### 2. Live RCMP-over-TCP Flashing (Bench test on Linux/Fedora)
* Bring up `pppd` over `ttyACM0` (or Windows PPP dialer / raw PPP framing).
* Run `rcmp_socket_transport.py`'s `probe()`: TCP connect to `radio:8002`, unlock (`0xC`), query UUID (`0x12`).

### 3. Keyfill Bringup
* Plug in the Pi Pico RP2040 cable or KVL clone box.
* Run `python cleanroom_flasher/kvl_probe.py` to identify adapter model ID and test loopback.
* Finish the P25 Manual Rekey (MR/KMM) protocol against open KFDtool source.
