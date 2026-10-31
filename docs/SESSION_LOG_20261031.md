# Session Log — 2026-10-31

Branch: `fix/cps-cli-and-capture-validators` (tip was `5c7cc25` at session start).
Agent: Claude Code (Opus). Machine: Windows 11 workstation. Radio on bench: **Radio 4 `721CLZ0655`** (XTS 5000 Mod III) on **COM9** (VID:PID `0cad:1002`).

## Done

### 1. Fixed CLI package-shadow bug
A tracked root file `open_astro.py` (the unified flash/read/diff wrapper, added in
`e977b84`) had the **same name as the installed `open_astro` package** (`src/open_astro`).
With the editable install's `.pth` adding `src` to `sys.path` but the repo root also on
`sys.path`, running from the repo root made `python -m open_astro.cli` import the root
wrapper instead of the package:

```
ModuleNotFoundError: __path__ attribute not found on 'open_astro' ...
```

Only the installed `open-astro` console script worked; the documented `python -m
open_astro.cli` form (AGENTS.md, NEXT_AGENT_HANDOFF.md) was broken.

Fix: renamed `open_astro.py` → `astro_tasks.py` (`git mv`), updated its docstring and the
3 references in `docs/ASTRO_FLASHING_AND_CODEPLUG_GUIDE.md`. Nothing imports it by module
name, so the rename is safe. `python -m open_astro.cli ports` now works. Full suite
**272 passed, 1 skipped**.

### 2. Live reads verified on Radio 4
- `open-astro probe --port COM9` → `721CLZ0655`, Host/DSP `R15.00.00`, `SECURE: R000000`.
- `open-astro rcmp-read --serial COM9 --partition 0x80 --object 0x0047 --length 0x10`
  → 14 bytes `2610270849030024000001524550` (`...REP`), reproduced twice.
- A single short RCMP session reliably reads many objects (saw `0x0ffc` inst 0–9 in one
  session).

### 3. Rebuilt the resilient dumper (`tools/resilient_rcmp_dump.py`)
The prior `scratchpad/resilient_dump.py` (Fedora) was gitignored and lost. Rebuilt and
**promoted to `tools/`** so it survives. Read-only (uses `RcmpReadClient`, no write method).
Strategy: one short PPP session **per object tag**, reconnect + retry/backoff on drop,
critical tags (`0x0fff`, `0x0ffd`) read first.

## Hardware finding (important)

The stock `open-astro rcmp-dump` runs **one long session** reading every tag; on this XTS
5000 that session wedges partway (`TCP retransmit limit reached ... link lost`). But the
XTS also **re-enumerates its USB CDC-ACM interface after every PPP session** — the COM port
briefly disappears or returns `PermissionError(13, 'Access is denied')` /
`'device not functioning'` / `FileNotFoundError`. So rapid per-tag reconnect races the
re-enumeration and most sessions fail. First resilient run got only 12 objects (missed
`0x0fff`/`0x0ffd`) → decoded 0 zones.

After heavy session churn the radio's PPP stack stops answering (`no SYN-ACK`) even though
AT still works; earlier in the session it **self-recovered after a rest**. It needs either a
quiet period or a power-cycle to come back.

`tools/resilient_rcmp_dump.py` was tuned for this: `_wait_for_port()` polls until the port
is actually openable before each attempt, and defaults raised to `--settle 6`,
`--backoff 4`, `--retries 5`.

## Next (resume here)

1. **Power-cycle Radio 4**, then run a clean full dump. Best odds, in order:
   - `python tools/resilient_rcmp_dump.py --serial COM9 -o scratchpad/721CLZ0655_full.json --serial-number 721CLZ0655`
   - If still partial, the real fix is to make the per-session **port-open wait live inside
     `PppTcpConn`** (`src/open_astro/protocol/ppp_link.py`) rather than the dumper, so
     every tool benefits, and consider a single-session dump started on a freshly
     power-cycled radio (which reads many objects before it wedges).
2. Verify the dump against `backups/Radio4_RedmondPD_721CLZ0655_codeplug.*` with
   `tools/verify_live_read.py COM9`.
3. Uncommitted working-tree changes from this session (not yet committed, awaiting Mario):
   rename `open_astro.py`→`astro_tasks.py`, `docs/ASTRO_FLASHING_AND_CODEPLUG_GUIDE.md`,
   new `tools/resilient_rcmp_dump.py`. Also untracked `tools/run_depot_write.py` (pre-existing).

Roadmap priority #1 (`0x0107 UnlockSecurity` wire-frame confirmation) is unchanged and still
needs a real unlock capture — not touched this session.

## Finding: Radio 4 holds a PARTIAL codeplug (9 of 13 zones)

After a radio power-cycle, a single-session `open-astro rcmp-dump --serial COM9` (one PPP
bring-up, no reconnect churn — the only pattern this XTS 5000 tolerates) read a clean
codeplug: **9 zones / 144 ch**, zone names `ZA ZB ZC ZD ZE ZE ZH ZI ZJ`. The master backup
(`backups/721CLZ0655.cpg`) is **13 zones / 194 ch** (`ZA … ZJ ZK ZL ZM ZR`).

The 9 live zones are a **byte-exact prefix** of the master: per-zone channel names match
for all 9, 16 ch each. Backup object instances are contiguous (`0x0fff`/`0x0ffc` = inst
0–13, `0x0ffd` = inst 0–26). The radio returns data through **instance 9** and empty from
10 on, across all three per-zone tags.

Ruled out a contiguous-probe gap with a direct tail-instance read (`scratchpad/probe_tail.py`,
one healthy session):
```
0x0ffc inst  9: 15 bytes DATA
0x0ffc inst 10-13: empty
0x0fff inst 10,13: empty
0x0ffd inst 10,15,26: empty
```
Hard cutoff at inst 9 → the tail zones `ZK/ZL/ZM/ZR` (instances 10–26, ~50 ch) were
**never written**. Classic partial/truncated flash (same failure class as the 205CFR2930
burst that died mid-write). **ROADMAP's "13-Zone/194-Ch flashed" for Radio 4 was wrong;**
corrected to PARTIAL. Fix = re-flash the full master `backups/721CLZ0655.cpg`.

`rcmp_transport.read_streams` was hardened while chasing this: added tag `0x000D` (live zone
names) and a transient-empty retry (`retry_empty`, default 1) so a dropped response no longer
truncates a dump. Tests: `tests/test_rcmp_transport.py` (+3). Suite 275 passed, 1 skipped.

## Flash investigation — completing Radio 4 (NOT executed; read-only survey)

Goal: write the 4 missing zones (`ZK/ZL/ZM/ZR`, 25 objects) onto Radio 4.

Facts established:
- **All 25 missing objects are partition `0x80`** (plaintext): 4×`0x0ffc`, 17×`0x0ffd`,
  4×`0x0fff`, instances ≥10. So completing the zones needs **NO `0x0107` unlock and NO
  `0x81` write** — the whole unlock blocker is irrelevant here. Master backup CRC-clean (0 bad).
- `src/open_astro/protocol/write_session.py` `CpgWriteAssembler.from_cpg()` already builds a
  write session straight from the master `.cpg` (no pcap): CRC-checks every object, refuses
  `0x82`, emits `0106 00 open → 0103 prepare → 0101 writes → 0106 01 commit`. Default prepare
  records cover `0x80` only (`types 2..500` + `items 3595..4095`, which spans both the low tags
  like `0x000D` and the high `0x0ffx` tags).
- `RcmpWriteClient` (rcmp_write.py) is gated (`allow_write=True`) and **OS-socket only** —
  userspace PPP cannot sustain the write burst (205CFR2930 lesson, codified).
- RAS dial-up entry **`OpenAstroRadio` exists** on the Windows workstation (`rasphone.pbk`),
  currently not connected. Bring up with `tools/ppp_up.ps1`, down with `tools/ppp_down.ps1`.
- `rcmp_replay_write.py` drives from a **pcap capture** + `--edit`, not from the assembler.
  No driver yet wires `CpgWriteAssembler` → `RcmpWriteClient` + readback-verify. **That driver
  is the missing piece.**

### OPEN BLOCKER — EEPROM persistence of a SYNTHESIZED session (Mario's lesson)
Prior hardware lesson: writing **identical** data makes the radio see "nothing changed" and it
does not re-commit to EEPROM. Our zone fill IS a real delta (9→13 zones), so that specific
no-op does not apply. BUT a deeper risk remains:
- `docs/how_motorola_writes_to_eeprom_and_partitions.md` (§4 diagram, lines 124-127): the radio
  flushes cache + recomputes the partition checksum **on commit (`0106 01`)**, and only then
  persists.
- The assembler's synthesized finalize is just `0106 01`. The **real CPS write sessions also
  sent `0102` and possibly `0104`/`0107` finalize records** (flagged "to confirm" in earlier
  notes). Only **pcap REPLAYS** (which carry CPS's exact finalize) are hardware-proven to
  persist (205CFR2930 recovery, ADP deploys). A fully synthesized `build_session` is **NOT yet
  proven to hit EEPROM** — it could write-then-not-persist, exactly the symptom Mario warned of.
- Also (§5, lines 144-145): `0x81` flashcode writes are **silently dropped** by the bootloader
  (re-read from the immutable factory sector on boot) — flashcode upgrade via standard RCMP
  never persists regardless. Not relevant to the `0x80` zone fill, but confirms `0x81` is a wall.

### NEXT (resume here — do NOT transmit without Mario's explicit go + fresh backup)
1. Parse a real decoded write capture's finalize tail to confirm the exact commit record
   sequence. `captures/cps_20261023_084833_decoded.json` has keys `OUT host->radio` /
   `IN radio->host`; `OUT` is a dict of 7 (not a flat hex string) — dig into its structure to
   extract the ordered `0101…0102/0104/0107/0106 01` tail.
2. Decide: **replay-with-substitution** (take a proven-persistent capture, swap in the zone
   objects via `--edit`, keep CPS's exact finalize → proven persistence) vs **synthesized
   `build_session`** (needs the finalize sequence confirmed + a hardware persistence test first).
   Replay-with-substitution is the lower-risk path to a permanent EEPROM write.
3. Build the assembler→live-write+readback driver OR extend `rcmp_replay_write.py` to inject the
   25 `0x80` zone objects. Dry-run (CRC byte-exact, no `0x82`) before any `--socket --confirm`.
4. Pre-write safety: fresh backup of the radio's CURRENT 9-zone state, CPS closed, RAS up,
   `--expect-serial 721CLZ0655`, `0x80` only, NEVER `0x82`, readback-verify vs master after.
