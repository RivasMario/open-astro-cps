# OpenAstro CPS — Cross-Platform Local & CLI Build Plan (Windows + Linux)

> **Baseline (verified):** Python test suite `285 passed, 1 skipped` (`pytest`); Rust CLI prototype exists at [`rust/open_astro_cli/`](../rust/open_astro_cli/Cargo.toml); full CPS/Depot RE synthesis at [`docs/re/CPS_DEPOT_COMPLETE_RE_SYNTHESIS.md`](re/CPS_DEPOT_COMPLETE_RE_SYNTHESIS.md).

---

## 1. Unified Rust Architecture (`open_astro_cli` = CLI + Embedded Web App)

One single static Rust binary (`rust/open_astro_cli`) for **Windows** (`COMx`, x64/ARM64) and **Linux/Fedora** (`/dev/ttyACM0`, x86_64/aarch64) provides **both**:
1. **CLI mode (`open_astro_cli read|write|flash|relay`)**: Zero-dependency field flashing, `--expect-serial` gate, hard `0x82` firewall, windowed PPP/TCP, and Tailscale network relay.
2. **Embedded Web UI mode (`open_astro_cli web`)**: Serves the local browser UI (`http://127.0.0.1:8765/`) directly from the same Rust binary (using `axum` or `tiny_http` + `include_str!`), replacing the Python `tools/web_app.py` prototype.
3. **Shared Truth (`schema/*.json`)**: Reads `field_layouts.json`, `partition_map.json`, and `block_type_map.json` alongside the existing Python `285`-test offline reference suite.

---

## 2. Phased Implementation Plan

### Phase 1 — Hardening & Local Simulator Parity *(Homelab AI `ai-ready` safe)*
1. **Rust Safety Gates (`rust/open_astro_cli/src/main.rs`):**
   - Reject any write targeting Partition `0x82` before framing.
   - Add `--expect-serial <SERIAL>` check (reads `0x81:0x1004` first, aborts on mismatch).
   - Gate `0x81` writes behind `--unlock-81` + confirmed `0x0107` profile (keep `0x80`-only as default).
   - Add CRC-16-CCITT (`poly 0x1021, init 0x0000`) to `encode_frame` / response verification.
2. **Simulator Integration Tests (`tests/test_mock_radio.py`):**
   - Test full `0x80` read/write/ADP-key/commit persistence, `0x82` rejection, and `0x81` lock behavior against `tools/mock_radio_capture.py`.

### Phase 2 — `0x0107` Wire Confirmation *(LXC 120 WinXP VM)*
1. Run `python tools/mock_radio_capture.py --host 0.0.0.0 --port 8002 --cpg backups/721CLZ0655.cpg --out captures/sim_0107.jsonl`.
2. Point CPS/Depot in `LXC 120` at the mock radio to record the exact `0x0107` request/seed offset.
3. Update `src/open_astro/protocol/unlock_session.py` (`WIRE_PROFILE_CONFIRMED = True`) and mirror the exact framing into `rust/open_astro_cli`.

### Phase 3 — Cross-Platform Serial/PPP + Network Relay *(Windows + Linux)*
1. **Native Serial + Userspace PPP in Rust:**
   - Add `serialport` crate to `rust/open_astro_cli/Cargo.toml` for `--serial COMx` (Windows) and `--serial /dev/ttyACM0` (Linux), porting the hardened ACK/windowed TCP state machine from `src/open_astro/protocol/ppp_link.py`.
   - Eliminates Windows RAS dial-up (`OpenAstroRadio`) and Linux `pppd` setup.
2. **Network Workbench Relay (`--socket` / `relay`):**
   - Add `open-astro relay --serial /dev/ttyACM0 --listen <tailscale-ip>:8002` so a radio plugged into a homelab node or field Pi can be programmed remotely over Tailscale from Windows or Linux.

### Phase 4 — Cross-Platform Builds & Field Packaging
- Build release binaries for:
  - Linux: `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu` (Fedora / Raspberry Pi)
  - Windows: `x86_64-pc-windows-msvc`, `aarch64-pc-windows-msvc` (this ARM64 workstation)
- Keep Python package (`pip install -e .`) for offline JSON/CSV/`.cpg`/SDR workflows.

### Phase 5 — Interactive CPS-Style Tree, Inspector & Manual Editor (`open_astro_cli web`)
- **Left-Hand CPS Tree & Subfolders** (full visibility into every radio option, zero raw hex required):
  1. **Radio Info & FLASHcode Decoder:** Model, Serial, Bandsplit, and human-readable Q/H/G feature checkboxes (current vs target).
  2. **Zones & Channels:** Per-zone channel table (Name, RX/TX Freq, Analog/P25, CTCSS/NAC, `rx_only` PA lockout, ADP Key Slot).
  3. **Conventional & Trunking Personalities:** Timeouts, TX power, signaling, trunking systems & talkgroup lists (`0x0FFB`, `0x0FD0`, `0x0FF8`).
  4. **Scan Lists, Buttons & Switches:** Priority/nuisance scan (`0x0FF1`) and Side/Orange/Concentric switch assignments (`0x0020`, `0x003C`).
  5. **Secure / ADP Keys & Radio-Wide:** 40-bit RC4 ADP key slots (`0x005D`), CKR (`0x0037`/`0x0038`), Display, Audio, MDC1200, Emergency.
- **Custom OpenAstro Superpowers (Not in Original Motorola CPS):**
  - **One-Click NAS Generator (`make-nas`):** Passive trunked monitoring channels with enforced `tx_frequency = 0.0`, `rx_only = True`, `tx_inhibit = True`.
  - **One-Click SDR Export (`export-sdr`):** Export zones/NACs/talkgroups directly to DSD-FME & SDRTrunk.
  - **CSV / JSON Fleet Sync & Side-by-Side Diff:** Clone/sync channels across mixed-generation radios (`XTS 2500` / `XTS 5000` / `PRC-153`) with Git-diffable JSON.
  - **Tailscale Network Relay & Pre-Flight Simulator:** Test writes against `MockRadioServer` or program remote radios over Tailscale, with `0x82` permanently blocked.
