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

## RE session #5 — codeplug schema past 0x0FFB (empirical + PatPort)

RE binaries unblocked: copied G: -> local NTFS `C:\Users\v-mariorivas\re_quarantine\astro25\`
(Ghidra refuses to analyze off the Drive-for-Desktop volume: "Backing volume must be NTFS").
PatPort.exe opened in REA (sha ae26c95c…); `binary_overview` indexing in background.

Empirically mapped + cross-validated on 3 backups (into `schema/field_layouts.json`):
- **0x000D = Zone name table.** resv[4] + u16(=50 const) + u16 count + count×17 B
  (16-byte ASCII zone name + 1 byte). 205CFR2930=Z1/Z2, 407CHT0214=A/B/C, Radio1=A..J,RB.
- **0x0020 = Physical controls matrix.** resv[4] + u16 count + u16 cap + count×(u8 control_id,
  u8 function). 7 controls {03,04,60,61,62,94,86} identical across radios; functions differ.
  **Function enum still TBD — needs PatPort builder 0x50c4fc (type 174).**
- **0x0047 = codeplug NAME/comment** (e.g. "KENT-PD_XTS 2500-II_160406-RB2D"), 44 B, NOT a
  password. **Revise Epic 4.2: password is 0x0002, not 0x0047.**

Open: Ghidra `binary_overview` (task running) to decode the 0x0020 function enum + confirm
builders. Then trunking 0x0FD0..0x0FDF (#5 cont.), extended-alphabet flashcode (#6).

## RE session #6 — P25 Trunking Subsystem (0x0FD0..0x0FDF) & Zero-Dongle Verification

Decoded the entire relational trunking graph from `Radio1_205CMB2249_codeplug.cpg`:
- **0x0FD2 = Control-channel frequency table:** Count x 5-byte records (`flags` + `rx_ch` + `tx_ch`).
  - **Frequency Grid Formula:** $\text{Freq (Hz)} = 851{,}000{,}000 + (\text{channel\_id} \times 6{,}250)$.
  - Validated down to the exact Hz against real King County / Seattle public safety allocations:
    `0x05e6` (1510) = 860.4375 MHz, `0x033a` (826) = 856.1625 MHz, `0x06ee` (1774) = 862.0875 MHz.
- **0x0FDF = Talkgroup table:** Count x 5-byte records (`flags` + `u16 TGID` + `u16 priority/flags`).
  - Master fleet list (Inst 0) decodes 28 talkgroups (1188, 930, 1192, 1742, 1148, 866, etc.).
  - Instances 1..9 decode zone-specific talkgroup selector lists.
- **0x0FDC = System Name table:** 15 systems (SEATTLE, APPLE CV, EPSCA, KCVC, etc.).
- **0x0FDD = System ID table:** 15 systems (SysIDs 1, 2, 3, 6, 7, 8, etc.).
- **0x0FDE = System Link bridge:** Maps 0x0FDD IDs to 0x0FDC Names.
- **Shipped `src/open_astro/parsers/trunking_decode.py`:** Clean-room typed parser `TrunkingDecoder`.
- **Shipped `tests/test_trunking_decode.py`:** 7 unit tests covering frequency math, synthetic tables, and end-to-end codeplug extraction (208 total tests passing).
- Documented in `docs/TRUNKING_0FD0_MAP.md`. Zero-dongle trunking read is complete.

