# Session Log — 2026-11-25

## 1. Complete CPS & Portable Depot RE (`504 / 504` functions, Ghidra 12.2 + Homelab `qwen2.5-coder:14b`)
- Verified via SHA-256 that **Regular CPS** and **Portable Depot (`R20.01.00`)** share **byte-identical** core DLLs (`NextGen10.dll`, `ByteData10.dll`, `UdcDrIsh10c.dll`, `EncatenComponent.dll`, `SECURITYLIB.dll`). Depot-only binaries are `PatPortDepot.exe` and `PBT2.dll`.
- Analyzed all **504** undocumented/unopened functions function-by-function on TrueNAS Ollama (`qwen2.5-coder:14b`, `num_ctx=8192`, `$0` API cost) across 5 batches:
  - `docs/re/HOMELAB_AI_EEPROM_PERSISTENCE_ANALYSIS.md` (20 funcs)
  - `docs/re/HOMELAB_AI_EEPROM_BATCH2.md` (26 funcs)
  - `docs/re/HOMELAB_AI_BATCH3_TRACE_AND_UNOPENED.md` (56 funcs)
  - `docs/re/HOMELAB_AI_BATCH4_SERIAL_AND_OTAP.md` (53 funcs)
  - `docs/re/HOMELAB_AI_BATCH5_CABS_AND_DEPOT.md` (349 funcs, incl. `PBT2.dll` & `UdcDrIsh10c.dll`)
- Synthesized everything for future AI agents in:
  - `docs/re/CPS_DEPOT_COMPLETE_RE_SYNTHESIS.md`
  - `docs/re/ASTRO25_DECOMPILATION_STATUS_MAP.md`
  - `docs/re/astro25_re_dashboard.html` (visual Tarkov Flash/EEPROM map + architecture)

## 2. Simulated Radio Capture & Persistence Verification
- Added `tools/mock_radio_capture.py`: TCP:8002 RCMP mock radio loading `.cpg` backups, modeling staged vs persistent flash/EEPROM (`0x80` commits on `0x0106 01`, `0x82` rejected with `0x01`, `0x81` dropped unless `0x0107` unlocked).
- Verified simulated flash + `0x80:0x005D` ADP key (`a1b2c3d4e5`) persistence across simulated reboot on both **XTS 2500 (`205CFR2930.cpg`)** and **XTS 5000 (`721CLZ0655.cpg`)**.
- Added `tools/web_app.py` (Python local Web App prototype on `:8765`).

## 3. Unified Rust CLI + Embedded Web UI (`rust/open_astro_cli`)
- Updated `docs/OPENASTRO_V2_BUILD_PLAN.md` for a single cross-platform Rust binary (Windows + Fedora Linux) with CLI + embedded Web UI + serial/PPP + Tailscale relay + Phase 5 CPS folder tree.
- Generated 10 Rust modules via `qwen2.5-coder:14b` and verified with `cargo test` (**29 passed, 0 failed**):
  `rcmp_crc`, `partition_policy` (`0x82` firewall), `serial_gate`, `cpg_codec`, `flashcode`, `channel_patch`, `hdlc`, `ppp_ipcp`, `relay`, `web_ui`.
- Wired `web`, `relay`, `flashcode`, and `check-partition` into `rust/open_astro_cli/src/main.rs` and built `open_astro_cli.exe` (`--release`).

## 4. Next Steps for Next Agent
1. **Confirm `0x0107` wire bytes:** Run `tools/mock_radio_capture.py` against CPS/Depot in `LXC 120` (`cps-capture`) to flip `WIRE_PROFILE_CONFIRMED = True` in `src/open_astro/protocol/unlock_session.py`.
2. **Rust Phase 3 & 5:** Add `serialport` + windowed PPP/TCP to `rust/open_astro_cli` for native Fedora `/dev/ttyACM0` & Windows `COMx`, and expand `web_ui.rs` to load/edit `.cpg`/JSON files from disk.
