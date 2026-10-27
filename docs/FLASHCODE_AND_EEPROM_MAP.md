# FLASHcode & EEPROM Write Map (Capability Unlock)

> Single source of truth for: what a FLASHcode is, how its bits map to radio
> features, where it lives in the codeplug/EEPROM, and the exact path by which
> CPS/Depot writes it to flash. Capability unlock (enabling Q667 ADP, trunking,
> zones, etc.) is driven entirely from this structure.
>
> **Evidence labels:** `[VERIFIED-BIN]` confirmed in a disassembled DLL this
> session (REA + Ghidra 12.1.4); `[VERIFIED-HW]` confirmed on a radio;
> `[SCHEMA]` from repo schema/code; `[OPEN]` not yet proven — do not rely on it.

---

## 0. TL;DR — the Q667 ADP unlock

- FLASHcode string lives at **partition `0x81`, object `0x1006:0`** (16-byte ASCII).
- A parallel **binary bitmask at `0x81:1005:0`** is what the OS kernel actually reads.
- **Q667 "Motorola ADP Encryption" = nibble 8, bit 4.** `[SCHEMA]`
- Fleet today: `000008-002410-2`. Add ADP → flip nibble-8 from `2`→`6`
  (`0010`|`0100`=`0110`): **`000008-006410-3`** (check digit **3**, binary-verified — §7.1).
- Writing `0x81` is NOT a plain codeplug write — it needs a security unlock or
  bootstrap mode first (§6). Standard RCMP write to `0x81` is ACKed but the
  bootloader drops it. `[SCHEMA]`

---

## 1. FLASHcode string format

Printed as `AAAAAA-BBBBBB-C`:
- 12 payload characters, each a **hex nibble** (0–F) = 48 feature bits total.
- `C` = single check digit — **Luhn mod-10 over the 12 nibble values**, even-from-left
  indices {0,2,4,6,8,10} doubled (§7.1, `[VERIFIED-BIN]`).
- Nibble index is 0..11 left→right across the 12 payload chars. Each nibble
  carries bits `8 / 4 / 2 / 1`. A feature is ON when its (nibble, bit) is set.

Example `000008-002410-2` → nibbles `0 0 0 0 0 8 0 0 2 4 1 0`:
- nibble 5 = `8` → bit 8 set
- nibble 8 = `2` → bit 2 set
- nibble 9 = `4` → bit 4 set
- nibble 10 = `1` → bit 1 set

---

## 2. Feature matrix (nibble × bit)

Source: `src/open_astro/models/flashcode.py` `FLASHCODE_MATRIX`. `[SCHEMA]`
— treat the exact Q-code/feature names as best-known, not binary-proven, except
Q667 which the ROADMAP + fleet behavior corroborate. Bits per nibble: 8/4/2/1.

| Nibble | bit8 | bit4 | bit2 | bit1 |
|:-:|:--|:--|:--|:--|
| 0 | H38/G24 SmartZone | **Q806 ASTRO Digital** | H35 Conventional | Q173 Omnilink |
| 1 | H14 Digital ID Disp | H869 HW Multikey | H37 SmartNet | Q387 Voting Scan |
| 2 | Q352 Soft ID | Q351 StatAlert MDC | Q498 Junior OTAR | Q388 Tactical OTAR |
| 3 | H02 Enh. Secure | Q947 APCO Packet Data | Q157 Emergency | Q390 Dual Prio Scan |
| 4 | Q182 Radio Ctrl Proto | Q391 OTA Scanning | Q398 Mixed Mode | Q445 Fireground Acct |
| 5 | Q53 FPP | Q446 Fireground Voice | Q361 P25 Digital CAI | Q52 Fed FPP |
| 6 | H46 One-Touch Status | H868 Multikey (48 keys) | H18 Enh. Trunking | Q179 Direct Freq Entry |
| 7 | Q399 Advanced Sys Key | Q374 Enh. Zone/Channel | Q447 Digital Tone Sig | Q574 Enh. Channel Scan |
| **8** | H39 Selective Call | **Q667 ADP (RC4-40 SW)** | Q888 Software Sys Key | Q375 Unit-to-Unit |
| 9 | H865 DES/DES-XL | H869 AES-256 (HW UCM) | Q575 Call Alert Decode | Q448 Secondary P25 Ctrl |
| 10 | Q507 12.5 kHz | Q508 25.0 kHz | Q376 Private Conv | Q362 P25 Phase 2 TDMA |
| 11 | Q363 Dynamic Dual Mode | Q576 Emergency Alarm | Q377 Radio Inhibit | Q577 Failsoft |

Notes:
- **Q667 (nibble 8 bit 4)** is the software 40-bit ADP RC4 unlock — no UCM
  hardware needed. DSP firmware R16/R19 already contains the RC4-40 engine
  (ROADMAP Epic 2, proven), so flipping this bit is the whole "software ADP"
  capability unlock. `[SCHEMA]` + `[VERIFIED-HW]` (Ch 3 ADP SECURE active on R1/R2).
- Hardware crypto (AES-256 nibble 9 bit4 = H869) still needs a physical UCM —
  bit alone will not enable it. The UCM socket is empty on the fleet (`R000000`).

---

## 3. Where it lives — codeplug objects in partition 0x81

| Object | Size | Content | Consumer |
|:--|:--|:--|:--|
| `0x1004:0` | — | Radio serial (e.g. `205CFR2930`) | identity |
| **`0x1005:0`** | 43-byte binary bitmask | the entitlement bits the kernel reads | OS firmware |
| **`0x1006:0`** | 16-byte ASCII string | human FLASHcode `000008-002410-2` | CPS/Depot display + reprogram |

`0x1006` (string) and `0x1005` (bitmask) must agree. Changing capabilities means
writing BOTH: the ASCII at `1006` and the derived bitmask at `1005`. The exact
43-byte `1005` layout (bit order vs the §2 nibble map) is **`[OPEN]`** — see §7.

---

## 4. EEPROM / flash partition map

From `docs/how_motorola_writes_to_eeprom_and_partitions.md` + `schema/patport_layout.json`. `[SCHEMA]`

| Partition | Name | Flash addr | Geometry | Access | Content |
|:-:|:--|:--|:--|:--|:--|
| `0x80` | Codeplug | `0x10020000` | 6 × 64 KB | ReadWrite (1) | zones, channels, personalities, scan, controls |
| `0x81` | **Security / EEPROM** | `0x1000A000` | 2 × 8 KB | **RW-Locked (2)** | serial `1004`, bitmask `1005`, FLASHcode `1006`, HW key regs |
| `0x82` | Tuning / calibration | `0x10100000` | 8 × 64 KB | **ReadOnly (0)** | RF soft-pots — **NEVER WRITE** (unrecoverable detune) |
| `0x83/0x85` | DSP / host firmware | bootstrap | variable | RW-Locked (2) | firmware; FlashZap/IROM only |

---

## 5. RCMP wire format (write)

```
[Len:2 BE][Opcode:2][Payload:N][CRC-16:2]
```
CRC-16-CCITT (poly 0x1021, init 0x0000) over opcode+payload. `[SCHEMA]`

Opcodes `[SCHEMA]`:
- `0x0100` READ object · `0x0101` WRITE object
- `0x0102` prepare write mode · `0x0103` erase/DelIshTypes blocks
- `0x0106` session open(`..00`)/commit+reboot(`..01`)
- `0x0107` **security unlock / challenge-response**
- `0x81xx` = ACK of request `0xxx` (high bit set)

WRITE (`0x0101`) payload: `[Part:1][ItemID:2][Inst:2][DataLen:2][Data:N]`.
FLASHcode write = `01 01 81 1006 0000 <len> <ascii>` and `01 01 81 1005 0000 2B <bitmask>`.

---

## 6. How the write actually reaches EEPROM

### Normal codeplug (0x80) lifecycle `[SCHEMA]` + `[VERIFIED-HW]`
1. `0x0106 00` session open → `0x8106 00`
2. read identity `0x0100 81 1004` / `1006`
3. `0x0102` prepare → `0x0103 80 ...` erase blocks
4. per-object `0x0101` write burst, each → `0x8101 00`
5. `0x0106 01` commit → radio flushes, checksums, reboots

### Partition 0x81 is locked — the extra step
- `0x81` is `ReadWriteLocked`. A bare `0101 81 1005...` is accepted at transport
  (radio returns `8101 00`) but the **bootloader silently drops it**; on reboot the
  radio re-reads the immutable license sector, so the change does not persist. `[SCHEMA]`
- To actually land a `0x81` write the host must first unlock:

**`CRcmpBundler::UnlockSecurity`** — `[VERIFIED-BIN]` (NextGen10.dll `FUN_1000cce7` @ RVA 0xcce7):
  - builds a `VT_ARRAY|VT_UI1` SafeArray (VARIANT type `0x2011`) = the challenge/key byte array
  - two transport branches on bundler mode: mode `0xc` (TCP-intranet, the proxy
    virtual-radio at `this[0xc]`, vtable `+0x50`); else direct transport via
    bundler vtable `+0x60` (send) → `SafeArrayAccessData` → `+0x5c` → `+0xb0`,
    with error rungs `0x97/0x98/0x99`.
  - i.e. UnlockSecurity sends the `0x0107` challenge-response, keyed off
    `SECURITYLIB.dll`, before `0x81` writes are honored.
- Companion COM entry points also present in NextGen10: `CRcmpBundler::EnterProgramMode`
  (`FUN` @ 0x11ab8), `EnterBootMode`, plus string `"Radio Failed to enter program mode"`
  and `"CheckSum Error"`. `[VERIFIED-BIN]`

### Bootstrap alternative (bypass runtime OS)
`FlashZapStart`/`IROMFlash` put the radio in bootloader mode for direct sector
programming via S-records — the path firmware itself is flashed through. `[SCHEMA]`
Higher risk; not needed for a FLASHcode change if UnlockSecurity succeeds.

### IRcmpBundler COM surface (NextGen10) `[SCHEMA]`
`Open, DelCodeplug, DelIshTypes, DelIshItem, WriteIshList, ReadIshList,
UnlockSecurity, UnlockIshPartition, UnLockRadio, EnterProgramMode, EnterBootMode,
FlashZapStart/Flash, IROMStart/Flash, ResetRadio`. (Class/method names present as
RTTI/trace strings in the binary; signatures from prior RE.)

---

## 7. Open items (do not assert these)

1. **Mod-10 check digit — `[VERIFIED-BIN]`, SOLVED (ROADMAP Task 2.1).**
   Source: `PatPort.exe` (sha256 `6b4c9ed6…0103`) `conCalculateFlashcode` @ VA
   `0x00a0b631`, check core `0xa0bbe1`–`0xa0bd96`, final at `0xa0bd83`. Algorithm =
   **standard Luhn mod-10 over the 12 nibble VALUES**:
   ```
   total = 0
   for i in 0..11:                 # i=0 leftmost char
       n = nibble_value[i]         # 0..15
       d = 2*n if i even else n    # even indices {0,2,4,6,8,10} doubled
       total += (d // 10) + (d % 10)   # sum decimal digits of d (idiv 10)
   check = (10 - total % 10) % 10
   ```
   Verify `000008-002410`: even-sum 6 + odd-sum 12 = 18 → `10-8` = **2** ✓ (matches stamp).
   Q667 upgrade `000008-006410`: even-sum 5 (nibble8 `6`→12→3, nibble10 `1`→2) + odd-sum 12
   (nibble5 `8`, nibble9 `4`) = 17 → `10-7` = **3** → **`000008-006410-3`**. The earlier
   "fails a blankcp sample" note was fuzzy memory; the binary is unambiguously Luhn. The
   `>100` branch at `0xa0bc0b` is dead code for nibbles ≤15. CLI may now compute check digits.

   **KAT-validated (two independent harvests, local + online):** 15+ real stamped codes pass,
   incl. fleet `000008-002410-2` / `140001-000000-3`, blankcp samples, and A–F tens-digit
   codes (`508048-00148C-0`, `54940F-E0078D-8`, `589108-101E87-0`); fabricated check digits
   correctly fail. Vectors are in `tests/test_flashcode.py` (`TestFlashcodeKnownAnswers`).
   **Limitation — second format:** newer H98/H51/M22/M25-SS/M37 families use an EXTENDED
   ALPHABET (letters `G/L/Q/R/S/Y` beyond hex, e.g. `9G10A8-811490-9`). The verified hex-Luhn
   does NOT cover them; `luhn_check_digit` raises and the CLI rejects them with a clear message.
   Their check scheme (likely Luhn over a larger base) is unverified — needs the PatPort routine
   run on an alphanumeric payload. **Bug fixed:** the repo's default template flashcode was
   `500008-000488-4` (invalid) everywhere (`cli.py`, `models/codeplug.py`, `examples/*.json`,
   `cleanroom_flasher/comm_pair_*.json`); corrected to the Luhn-valid `-2` (`100008-000488` → `-1`).
2. **`0x1005` bitmask byte layout `[VERIFIED-HW]` — read live from Radio 4 (`721CLZ0655`).**
   Read live over RCMP partition 0x81 on 2026-10-27 for FLASHcode `400008-002000-0`:
   `1d17325b7ef5b534fbebb9e20218c520008000801000000310e8000000000c040000000008000002000000` (43 bytes).
   RE this RE this
   session (static pefile/capstone over PatPort.exe + cgIsh10c) found both partition-`0x81`
   builders: item `0x1006` (ASCII string) builder @ `0x91e8cc` (ATTR ctor `0x91e8fe`,
   data-layout `0x3749/0x374a`); item `0x1005` (license bitmask) builder @ `0xa11a68`
   (ATTR ctor `0xa11a9e`, data-layout `0x206a`). The `0x1005` builder does NOT enumerate
   48 per-feature fields — its `0x206a` layout geometry (field id/offset/length) is computed
   programmatically in registers (helpers `0x1229d68`, `0x403520`), not inline immediates,
   so static push-scanning can't recover the byte/bit map. **`0x1005` is an opaque license
   blob in the ISH schema; the per-feature bit meaning (Q667 etc.) is the semantics of the
   `0x1006` string applied by radio firmware / a CPS feature table, NOT encoded in the
   `0x1005` field layout.** So the §2 nibble→feature grid is the authority and is neither
   confirmable nor refinable from cgIsh10c. To get the literal 43-byte map anyway: (a)
   unicorn-emulate builder `0xa11a68` to resolve the register-computed geometry of layout
   `0x206a`, or (b) diff two real `.cpg` streams whose only delta is one feature bit
   (ground-truth oracle; needs a `.cpg` that carries `0x1005`). CAVEAT: scratchpad
   `layout_0x1005.json`'s "49 fields" are MFC assert/validation strings (args to helper
   `0x1229f66`), NOT field names — do not treat as a field list.
3. **Does UnlockSecurity alone persist a `0x81` write, or is FlashZap required?**
   `[OPEN]` — needs a live Depot `0x81` write pcap (home PC) to confirm which path
   Depot actually takes.

---

## 8. Capability-unlock checklist (when solved + on hardware)

1. Pick target features → set their (nibble,bit) in the §2 grid → new 12-nibble payload.
2. Compute check digit (§7 item 1) → full `AAAAAA-BBBBBB-C`.
3. Derive the `0x1005` 43-byte bitmask (§7 item 2).
4. Back up the radio (`backups/*.cpg`) first.
5. `UnlockSecurity` (0x0107) → write `81:1006:0` (ASCII) + `81:1005:0` (bitmask)
   → commit → reboot → read back `1005`/`1006` to confirm persistence.
6. **Never touch `0x82`.** Writer in `tools/rcmp_replay_write.py` rejects it.

## 9. CLI: `open-astro flashcode-upgrade`

Offline — flips feature bits, computes the verified Luhn check digit, emits a
`--edit 81:1006:0:<hex>` flag for `rcmp_replay_write.py`. Does not transmit.

- `--list-features` — all named switches + profiles.
- `--profile recommended` — sane no-UCM P25 conventional load.
- `--profile max-nonucm` — every software feature, **strips** hardware-gated bits
  (the no-UCM "kitchen sink"; this is the right max load for the XTS2500 fleet).
- `--profile max-ucm` — all 48 bits incl. hardware crypto (implies a UCM is installed).
- `--enable <feature>` / `--disable <feature>` — named toggles (e.g. `--enable adp`,
  `--enable enhanced-scan`); repeatable. `--add N:B` / `--remove N:B` for raw bits.
- `--add-adp` — shortcut for Q667 ADP (software, no UCM).
- `--ucm` — allow hardware-gated features (AES/DES/HW-multikey/ASK). **Default refuses
  them** — the fleet has no UCM, so those bits are dead weight and get stripped by the
  `max-nonucm` preset.
- `--flashcode <code>` / `--input <json>` / `--set <12hex>` — starting point (default fleet).

Examples (no UCM):
```
open-astro flashcode-upgrade --add-adp                      # 000008-002410-2 -> 000008-006410-3
open-astro flashcode-upgrade --profile recommended         # curated software load
open-astro flashcode-upgrade --profile max-nonucm          # all software features, AES bit stripped
open-astro flashcode-upgrade --flashcode 140001-000000-3 --enable p25 --enable adp   # radio 3 (VHF)
```
Extended-alphabet codes (G/L/Q/R/S/Y, newer families) are rejected with a message —
the fleet is classic hex format, fully supported.
