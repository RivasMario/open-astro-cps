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

## Persist-control framing EXTRACTED + synthesized session built (2026-10-31, later)

Decoded the proven persistent write session `captures/cps_20261023_101302.pcap` **device 5**
(the 205CFR2930 recovery) via `rcmp_replay_write.extract_out_records` (native usbpcap_read +
PPP unframe + VJ + TCP reassembly — tshark `usb.capdata` is empty on the write device). 183
OUT records. Ordered control flow:
```
[0]   0106 00                 session open
[1]   0100 x1                 probe read
[2]   0104 8512bf00000000     control (part 0x85)
[3-28]0100 x26                CPS reads current plug
[29]0010 [30]0011 [31]000f    control
[32]  0102 80 0047 0000 0001  BEGIN-WRITE
[33]  0103 80 0002 01f4       prepare/erase types 2..500
[34]  0103 80 0e0b 0fff       prepare/erase items 3595..4095
[35]  0107 8000               partition-0x80 CHECKSUM/arm  (right before writes)
[36-181] 0101 x146            writes
[182] 0106 01                 commit
```
Key: `0107 8000` is the **0x80 partition checksum**, NOT the `0x81` UnlockSecurity
challenge — so a 0x80 codeplug write needs it and we can reproduce it. The old synthesized
`build_session` omitted both `0102` begin and `0107` checksum — the likely reason a synthesized
write would not commit to EEPROM.

Implemented (offline, no transmit; suite 279 passed, 1 skipped):
- `rcmp.build_begin()` / `rcmp.build_checksum()` — reproduce capture records [32]/[35]
  byte-exact (`010280004700000001`, `01078000`). Tests in `tests/test_rcmp_write.py`.
- `CpgWriteAssembler.build_session_full()` — emits the full persist framing
  `0106 00 → 0102 → 0103×2 → 0107 8000 → writes → 0106 01`, 0x80-only (refuses 0x81).
- Verified end-to-end: assembling from `backups/721CLZ0655.cpg` (0x80 objects, CRC-clean)
  yields **458 write objects + control framing byte-identical to the capture**. This is a
  complete synthesized write of Radio 4's full 13-zone codeplug (erase-prepare + full 0x80
  rewrite → rebuilds zones cleanly, 0x81 untouched).

STILL UNPROVEN (needs hardware, do NOT skip): whether CPS's read-phase records
(`0104`/`0100`×27/`0010`/`0011`/`000f`) are required for commit — `build_session_full` omits
them. The one real test: over `--socket` (RAS up), write + power-cycle + readback = 13 zones.

## Live-write + readback driver built (2026-10-31, later) — `tools/write_codeplug_full.py`

Driver that assembles the full 0x80 session from a source `.cpg` and, with `--confirm`,
transmits it over `--socket` (RAS/pppd) record-by-record (ack-checked via
`RcmpWriteClient.send_prebuilt`), then reconnects read-only and verifies zone count/names.

Safety gates (all verified offline):
- DRY RUN by default — assembles, validates control framing == proven capture, prints
  summary, transmits nothing.
- `--confirm` without `--socket` → refused. `--socket --confirm` without `--expect-serial`
  → refused.
- With `--confirm`: reads radio serial `0x80:0x1004` first and ABORTS unless it contains
  `--expect-serial` (wrong-radio guard).
- 0x80-only (assembler refuses 0x81); 0x82 never emitted.
- CRC-clean gate: any 0x80 object failing CRC aborts assembly.

Dry run on `backups/721CLZ0655.cpg`: 464 records, 458 writes, control framing matches the
capture, commit `0106 01`. Test: `tests/test_rcmp_write.py::test_full_session_records_roundtrips_build_session_full`.
Suite 280 passed, 1 skipped.

### THE flash procedure (when Mario is at the bench — NOT yet run)
1. Power-cycle Radio 4; confirm COM9 stable (not cycling) ~15s; CPS closed.
2. Fresh backup of CURRENT 9-zone state: `open-astro rcmp-dump --serial COM9 -o backups/721CLZ0655_pre_fullflash_<ts>.json` (then lower PPP).
3. Bring up RAS: `tools/ppp_up.ps1` (dials "OpenAstroRadio"; 192.168.128.1 reachable).
4. Dry run first: `python tools/write_codeplug_full.py backups/721CLZ0655.cpg`.
5. Live: `python tools/write_codeplug_full.py backups/721CLZ0655.cpg --socket --expect-serial 721CLZ0655 --confirm`.
6. If the write fails mid-burst (watchdog), power-cycle and re-read; 0x82 was never touched so soft-pots are safe.
7. Verify: readback prints zones; expect 13 zones / 194 ch (`ZA`–`ZR`). Lower PPP (`tools/ppp_down.ps1`).
If a synthesized write does NOT persist (still 9 zones after power-cycle), the read-phase
records are required → switch to capturing a real CPS full-plug write to Radio 4 and replaying
it, or add the missing `0104`/`000f` records to `build_session_full` from that capture.

## FLASH EXECUTED + PERSISTED (2026-10-31) — Radio 4 complete

Ran the full-`0x80` synthesized write to Radio 4 and it persisted to EEPROM. **The synthesized
session (no CPS read-phase records) was sufficient** — the `0102` begin + `0107 8000` checksum
framing was the missing persist trigger; the read-phase `0104`/`0100`×27/`000f` records are NOT
required.

Sequence that worked:
1. Backup current 9-zone state → `backups/721CLZ0655_pre_fullflash_20261031_171334.json`.
2. `tools/ppp_up.ps1` → RAS `OpenAstroRadio` up (dials over the COM7 modem interface; TCP 8002
   reachable). NOTE: RAS modem is COM7 even though the raw CDC-ACM read port is COM9.
3. First `--confirm` attempt ABORTED on the identity gate: it read the serial from `0x80:0x1004`
   but the serial lives in **partition `0x81`** (`0x1004`), so it read empty → fail-closed (good).
   Also learned this XTS drops PPP after *every* session, so a **separate** pre-read consumed the
   one session and tore down RAS before the write could connect.
4. Fixed `tools/write_codeplug_full.py` to do the identity read **in-session** on the write
   connection (`0x81:0x1004`, right after `0106 00`, before any `0101`). Re-dialed RAS.
5. Live write: identity OK (`721CLZ0655`), **458 `0x101` writes + `0106 01` commit all acked**,
   full burst sustained over the OS socket (userspace PPP would have dropped ~record 60).
   Post-session readback failed (radio drops PPP — expected).
6. `tools/ppp_down.ps1`; **power-cycled** Radio 4; cold `open-astro rcmp-dump` →
   **13 zones / 194 ch, names `ZA`–`ZR`, byte-match to master** (`scratchpad/721CLZ0655_postflash_*.json`).

Proven: `CpgWriteAssembler.build_session_full()` + `tools/write_codeplug_full.py` produce a
persistent `0x80` codeplug write on real hardware. `0x82` never touched; `0x81` not written (so
flashcode unchanged at `400008-002000-0` — still no Q667 ADP entitlement, which needs the
`0x81`/`0x0107` path, unchanged by this work). ROADMAP Radio 4 corrected to FULL.

## ADP write to Radio 4 + the 0x81 flashcode WALL confirmed (2026-10-31, later)

Big finding first: the proven write capture (`cps_20261023_101302` device 5) writes partition
`0x81` (`0x1004/1005/1006`) interleaved with `0x80`, under the single `0107 8000` checksum, with
**no `0x0107` UnlockSecurity challenge** (records [35] `0107 8000` → [36-38] `0101 0x81`). So the
`0x0107` wall was assumed, not shown — for a write of the SAME flashcode. That capture only ever
restored 205CFR2930's own flashcode, so it never tested a flashcode *change*.

Hardened `tools/flash_radio4_adp.py`: added an in-session identity gate (read `0x81:0x1004`,
abort unless `721CLZ0655`, before any erase) and `--no-unlock` (skip the `0x0107` exchange, since
the capture wrote `0x81` without it). Dry run = 505 records / 468 writes, no `0x82`.

Ran it live (`--write --no-unlock`, RAS socket): identity OK, all 505 records acked, committed.
Power-cycled. Cold readback:
- **ADP secure subsystem (`0x80`) PERSISTED:** `0x0034` master-enable (ends `0003`), `0x0035`,
  `0x0037` CKR, `0x0038` CKR1-8, `0x005D` key table (key reads back masked `0001**********` —
  radios mask key material on read; slot structure present).
- **Flashcode (`0x81:0x1006`) did NOT persist — reverted to base `400008-002000-0`** (target was
  `400008-006000-1`). AT&V: radio healthy, identity `721CLZ0655`/`H18UCF9PW6AN` intact,
  `SECURE: R000000` (UCM socket, unchanged — ADP is software).

CONCLUSION: EEPROM doc §5 is right — the bootloader re-reads the flashcode from the **immutable
license sector**, so a plain `0x81` write (no unlock) does NOT persist. **The `0x0107`
UnlockSecurity IS required to change the flashcode** (license sector), and its wire frame is still
unconfirmed (`unlock_session.WIRE_PROFILE_CONFIRMED = False`). So:
- Radio 4 now carries the ADP codeplug objects + key slots, but NOT the Q667 flashcode
  entitlement. Whether ADP keys up on-air without the flashcode bit is UNVERIFIED (needs SDR /
  on-air test, Epic 3). R1/R2 "ADP active" claims may rest on the same unverified footing.
- Kitchen-sink / any flashcode CHANGE (all radios) is BLOCKED on confirming the `0x0107` frame —
  back to handoff priority #1. A real Depot/CPS flashcode-write capture that contains the `0x0107`
  challenge is the unblock; `captures/depot_flashcode_20261024_214545.pcap` is raw bulk (no PPP/
  RCMP), not it.
- `0x82` never touched throughout. Radio 4 zones: full OptionA 13-zone `0x80` written + persisted
  (every 0x80 readback object present); a re-dump to re-count was blocked by the radio's
  post-session PPP flakiness, not data loss.
