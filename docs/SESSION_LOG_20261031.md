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
