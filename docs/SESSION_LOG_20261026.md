# Session Log — 2026-10-26 (Claude Code / Opus)

Narrative record for this working day. Read before starting; append as you go.
Task status lives in `ROADMAP.md`; this explains how it got there.

## Shipped (committed)

- **`3e9e004`** (prior) flashcode-upgrade CLI + verified Luhn check digit + EEPROM map.
- **`4c2977e`** (Gemini) SDR export, button patcher, field-schema decoder, virtual radio.
- **`5b51f39`** build phase:
  - `export-sdr`: `--key` / `--emit-launch` → DSD-FME run script with `-K <ADP key>`.
  - `virtual_radio`: socket timeout, thread pruning, OP_WRITE CRC check, dead import
    removed, optional `--lock-security` 0x81 UnlockSecurity (0x0107) gate. 0x82 firewall
    unchanged. Fuzzed: 4000 random frames + 2000 0x82 writes, no crash, firewall held.
  - `cpg_decode.personality_records()` → 43 unique 0x0FFB personalities, shown in
    `decode-cpg` summary.
  - `field_layouts.json`: flags `0x80`=simplex / `0x40`=duplex verified; `0x0FFD`
    even-instance header carries `0x0FFD`+subid.

## Verified facts (and where proven)

- FLASHcode check digit = Luhn mod-10 (PatPort `conCalculateFlashcode`). ADP (Q667)
  upgrade `000008-002410-2` → `000008-006410-3`. Max-software code `FBFFFF-B7F3FF-1`
  (43 feats, 0 hardware-gated) — verified against our own KAT'd tool.
- Codeplug personalities span many `0x0FFD` instances (19 on the full fleet backup,
  43 records). See `CODEPLUG_0FFD_PERSONALITY_TABLES.md`.
- End-to-end simulated flash proven (`scratch/demo_flash.py`, now
  `tests/test_e2e_flash.py`): real RCMP client ↔ virtual radio, read identity →
  compute ADP upgrade → write `0x81:1006` → read-back verified; 0x82 refused both
  client- and server-side; 0x81 gated behind 0x0107 under `--lock-security`.

## Corrected assumptions (do not repeat)

- **"decode-cpg reads only 0x0FFD inst 1" was WRONG.** The zone-walker was always
  multi-instance (147 channels on the full backup, ADP included). The earlier
  "2 channels" was just `205CFR2930.cpg` being a genuine 2-channel pre-flash backup.
  `personality_records()` is a separate unique-personality view, not a bug fix.

## Infrastructure

- **RE binaries now reachable** on this machine via Google Drive for Desktop:
  `G:\My Drive\RADIO\ASTRO25SOFTWARE\astro25portablecpsr20.01.00\...` (PatPort.exe 24.8 MB,
  ByteData10.dll, NextGen10.dll, Depot R20.01.00 suite). Resolve with
  `python tools/re_paths.py` — never hardcode (see `AGENTS.md`). Env
  `OPENASTRO_RE_ROOT` set on this box.

## Open threads

- Web app (Epic 4.4, FastAPI + frontend) being built in an agent — pending landing.
- Binary RE now UNBLOCKED (Drive mounted): #5 deep codeplug schema (zones `0x000D`,
  controls `0x0020`, trunking `0x0FD0`, password `0x0047`), #6 extended-alphabet
  flashcode check digit, #7 toggle switch, NextGen10 pin-8000 proxy path.
- Hardware-only (still parked): Epic 3.2/3.3 live P25 over SDR; any live radio write.
