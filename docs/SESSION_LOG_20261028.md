# Session Log — 2026-10-28 (Fedora laptop, Claude Code)

Radio connected this session: **Radio 4 "Redmond PD" `721CLZ0655`** (XTS 5000 Mod III), native USB
CDC-ACM `0cad:1002` → `/dev/ttyACM0`.

## Done

### 1. XTS 5000 model differentiation
- `src/open_astro/protocol/serial_link.py`: added `MOTOROLA_PIDS[0x1002] = "XTS 5000 / XTL 5000"`.
- `open-astro ports` now tags the radio `[RADIO: Motorola XTS 5000 / XTL 5000]`; `probe` `model_hint` populated.
- `pytest`: **249 passed, 1 skipped, 19 subtests**.

### 2. Live link verified (read-only)
- `open-astro rcmp-read --serial /dev/ttyACM0 --partition 0x80 --object 0x0047 --length 0x10` →
  `SESSION_ACK`, 14 bytes, tag ends `REP` (REPD codeplug → confirms Radio 4).
- Live flashcode read `0x81:1006` → `400008-002000-0` (**base code; Option A ADP `400008-006000-1` is NOT on hardware**).
- Confirms prior finding: Partition `0x81` is hardware `ReadWriteLocked`; plain RCMP writes ACK at
  transport but EEPROM ignores them without `UnlockSecurity` (opcode `0x0107`).
- NOTE: the radio re-enumerates (`ttyACM0` device number bumps) when an RCMP/PPP session closes — normal XTS behavior, not a fault.

### 3. RE toolchain on Fedora (no sudo)
- `scripts/setup-re.sh` aborts at `sudo dnf` (no TTY for password). Installed sudo-free instead:
  - **Ghidra 12.2** → `~/tools/ghidra_12.2_PUBLIC` (requires **JDK 25**: `application.java.min=25`).
  - **Temurin JDK 25** (full, has `javac`) → `~/tools/jdk-25.0.5+8`. (JDK 21 and system JDK 25 are JRE-only / rejected by Ghidra.)
  - **rea-agents** → `~/.npm-global/bin/rea`.
- **REA MCP** registered at **local scope** for this repo: `GHIDRA_INSTALL_DIR=~/tools/ghidra_12.2_PUBLIC`,
  `JAVA_HOME=~/tools/jdk-25.0.5+8`. `claude mcp list` → `rea ✔ Connected`.

### 4. RE binaries staged on Fedora
- Vendor binaries live on rclone Google Drive mount `~/GoogleDrive/RADIO/ASTRO25SOFTWARE/astro25portablecpsr20.01.00/...`.
- Copied the 3 registered binaries to a fast **local** RE root (Drive stalls Ghidra):
  `~/re/openastro/` mirroring the relative tree (PatPort.exe 24M, ByteData10.dll 132K, NextGen10.dll 240K).
- `re_sources.local.json` (gitignored) → `{"root":"/home/mario/re/openastro"}`. `tools/re_paths.py` resolves all 3 OK.
- `cgIsh10c.dll` / `fhAdk10c.dll` NOT found in the portable CPS tree (likely in the Depot zip or Windows-only).

### 5. 0x0107 UnlockSecurity RE — started (Epic 1 / ROADMAP priority #1)
- `strings PatPort.exe` anchors: `LocalUnlock`, `P25 Radio Authentication`, `User Authentication`,
  `Site Lock/Unlock`, `Unable to unlock the radio.`, `Time out! Unlock the program!`, `Rekey Request`,
  `conIsCnvRekeyRequestAllowed`, `conIsTrkRekeyRequestAllowed`.
- Ghidra headless project built: `~/re/ghidra_projects/openastro` (PatPort.exe imported + auto-analyzed, JDK 25).
- Decompile script: `~/re/ghidra_scripts/FindUnlock.java` (xrefs + decompile of unlock-string callers). Output → `scratchpad/unlock.log`.

## Why Fedora can't flash yet (software/data only — NOT hardware)
1. `tools/flash_radio4_adp.py` replays `captures/cps_20261023_101302.pcap`, which is gitignored
   (`captures/*.pcap`) and Windows-only — absent here, so the write stream can't be built.
2. `0x0107 UnlockSecurity` is unsolved. Once implemented in pure Python in `open_astro`, it runs on
   Fedora identically; vendor DLLs are disassembly reference specs only (Ghidra reads them cross-platform).

**Path to full Fedora flashing:** solve `0x0107` + get the write-record stream into the repo (or regenerate on Fedora). No Windows needed at flash time.

### 6. 0x0107 UnlockSecurity — LOCATED (NextGen10.dll)
- Ghidra note: full analysis of 24M `PatPort.exe` **hangs** in MSVC RTTI/type phase on this laptop
  (tried: switch-analyzer off, lean preScript — same hang). Pivoted to the small engine DLLs.
- **NextGen10.dll** (base `0x10000000`, 571 funcs) is the `CRcmpBundler`/`CRcmpProtocol` RCMP engine.
  `ByteData10.dll` is base `0x11000000` (my earlier 0x10xx addrs were NextGen10 all along).
- **`CRcmpBundler::UnlockSecurity` = `FUN_1000cce7`**: builds msg tag `0x2011`, then vtable
  build(`+0x60`,err 0x97) → send(`+0x5c`,err 0x98) → reply(`+0xb0`,err 0x99) on `CRcmpProtocol`.
- Decompiles saved: `docs/re/nextgen10_unlocksecurity_decomp.txt`; analysis: `docs/re/RE_0107_UNLOCKSECURITY.md`.
- Ghidra scripts in `~/re/ghidra_scripts/` (DisableSwitch, LeanAnalysis, FindRcmp, DecompTargets, Diag).
  Gotcha: a backgrounded launch whose first cmd is `pkill` dies when pkill matches nothing — guard `|| true`.

### 7. 0x0107 seed→response transform — SOLVED + ported
- `CRcmpBundler::UnlockSecurity` (`FUN_1000cce7`) calls `FUN_1000fd89` between send and reply.
- **`FUN_1000fd89` = self-synchronising LFSR scramble over a 32-byte block**: init `0x51E88D21`,
  tap bit 9, `state = state*2 + (in_bit XOR tap)`, bits 7..1 (bit 0 passes through), input read reversed.
  **No key / no per-radio secret / no asymmetric crypto → fully reversible.**
- `BundleTCP`=`FUN_100187b6` (length framing only), `SendRequest`=`FUN_10018123`,
  `GetReply`=`FUN_10018030`; `FUN_1000b2ad` = COM `LoadServer` setup (not crypto).
- Ported: `src/open_astro/protocol/unlock.py` `unlock_response()`. Tests: `tests/test_unlock.py`
  (7 pass; golden vectors + bit0-passthrough/length/determinism). Full suite **256 passed, 1 skipped**.
- Decompiles: `docs/re/nextgen10_rcmp_methods_decomp.txt`; write-up `docs/re/RE_0107_UNLOCKSECURITY.md`.

### Live ADP state map (resilient dump, scratchpad/state_map.json, 50 objs)
- `0x80:0034` secure ENABLED; `0x0037/0x0038` CKR table CKR1–8; `0x005D` key slots 0001–0008 but
  **keys masked (not loaded)**; `0x81:1006` flashcode `400008-002000-0` (**Q667 ADP NOT entitled**).
- ADP scaffolding present; blockers: (1) Q667 flashcode via 0x0107, (2) write ADP key into codeplug
  0x80 (ADP = 40-bit RC4 = codeplug key field, NO KFDtool; KVL/KFDtool only for AES/DES), (3) verify
  channel `0x0FFD` ADP personality pointers.
- Live link note: XTS wedges on long/killed sessions (needs power-cycle); short batched reads +
  reconnect-on-drop are stable (`scratchpad/resilient_dump.py`).

### 8. UnlockSecurity handshake scaffold (gated, not transmitting)
- `src/open_astro/protocol/unlock_session.py`: `UnlockSession.exchange()` orchestrates
  send-req → read 32B seed → `unlock_response()` → send-resp; `perform()` refuses while
  `WIRE_PROFILE_CONFIRMED = False`. Tests `tests/test_unlock_session.py` (mock transport). Suite **261 passed**.
- CONFIRMED: exchange shape + scramble. UNCONFIRMED (needs a real unlock capture or COM trace):
  request wire opcode (`0x0107` vs msg tag `0x2011`), request body, seed offset in reply.
- Capture check: NO UnlockSecurity exchange on this laptop. `captures/cps_*` are codeplug READ
  sessions; `captures/depot_adp`/`depot_write` decoded JSON have 0 parsed RCMP (OUT empty, IN unparsed).

## Next
- Confirm the unlock wire frame via (A) a fresh Depot "unlock/program" capture, or (B) COM trace from
  `FUN_1000b2ad` CoCreateInstance (CLSIDs `DAT_10025aa0`/`DAT_10025af0`). Then set `WIRE_PROFILE_CONFIRMED`.
- Record a hardware seed/response pair as the acceptance vector for `unlock_response()`.
- Then live `0x81` flashcode write `400008-006000-1` (Luhn check digit already solved).
- Write ADP key (`A1B2C3D4E5`) into codeplug 0x80 key field (no KFDtool); verify channel `0x0FFD` ADP pointers.
- Flashing via replay still needs the write-record stream in-repo (not the Windows-only pcap).
