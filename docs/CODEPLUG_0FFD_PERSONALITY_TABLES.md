# Codeplug `0x0FFD` Personality Tables — Empirical Findings

> Source: offline byte-diff of `backups/*.cpg` on 2026-10-26 (no binary/RE tool, no
> hardware). Ground-truthed on `Radio1_205CMB2249_codeplug.cpg` (500 objects — the
> full flashed fleet codeplug). Method = the same empirical diff that built
> `schema/field_layouts.json`.

## Summary

The conventional personality records (`0x0FFB`, 35-byte, see `field_layouts.json`)
are stored across **multiple instances** of the `0x0FFD` table — not one. There are
**43 unique personalities** on the full fleet codeplug.

> **Correction (2026-10-26):** an earlier note here claimed `decode-cpg` "reads only
> instance 1" and so saw 2 channels — that was **wrong**. `decode-cpg`'s zone-walker
> already traverses multiple `0x0FFD` instances via `0x0FFC` channel refs (it yields
> 147 channel instances on the full backup, ADP included). The earlier 2-channel
> result was simply `205CFR2930.cpg` being a genuine 2-channel *pre-flash* backup.
> `CpgDecoder.personality_records()` adds the distinct **unique-personality** view
> (43 records); it is surfaced in the `decode-cpg` summary line.

## `0x0FFD` instance map (Radio1_205CMB2249_codeplug.cpg)

19 instances, `0..18`, alternating two shapes:

| Instance parity | len | count | records | header first 4 bytes |
|---|---|---|---|---|
| even (0,2,4,…,18\*) | 356 | 10 | 10 × 35 B | `0x0FFD` + u16 sub-id (`0001,0003,0005,…`) |
| odd (1,3,5,…,17) | 216 | 6 | 6 × 35 B | `00 00 00 00` (zero) |

\* inst 18 is short (111 B / 3 records). Stride is **35 bytes everywhere**.

**Total `0x0FFB` records across all instances: 43.**

## Schema corrections (vs current `field_layouts.json`)

1. **`0x0FFD` header `reserved[4]` is not always reserved.** On even instances the
   first 4 bytes are `0x0FFD` followed by a u16 sub-id (odd-numbered: 1,3,5,…). Only
   odd instances are zero-filled. The `count` u16 at offset 4 holds in both.
2. **`0x0FFB` `flags` byte (offset 27) RESOLVED:**
   - `0x80` = **simplex / direct** (rx == tx) — was already verified.
   - `0x40` = **duplex / repeater** (rx != tx) — previously "unresolved". Proven:
     every `0x40` record has distinct rx/tx (e.g. 806.5125 rx / 851.5125 tx, the
     standard 800 MHz 45 MHz public-safety split).

## ADP SECURE channel (851.5125)

Absent from `205CFR2930.cpg` (146 obj, pre-flash) and `205CMB2249_ADP.cpg`.
Present only in the full fleet backup:

| inst | rec | rx (MHz) | tx (MHz) | sq_rx | sq_tx | flags |
|---|---|---|---|---|---|---|
| 4  | 8 | 806.5125 | 851.5125 | 26 | 26 | 0x40 (duplex) |
| 14 | 2 | 806.5125 | 851.5125 | 26 | 26 | 0x40 (duplex) |
| 14 | 3 | 851.5125 | 851.5125 | 26 | 26 | 0x80 (simplex talkaround) |

## Status / applied

- `field_layouts.json`: header + `flags 0x40/0x80` corrections folded in. ✅
- `cpg_decode.py`: `CpgDecoder.personality_records()` returns the 43 unique
  personalities; surfaced in the `decode-cpg` summary line. ✅ (The channel export
  path was already multi-instance — see the correction note above.)
- Open question: decode the even-instance sub-id (`0001,0003,…`) — likely a
  zone/personality-group link; needs cross-ref with `0x000D` (zone defs, unmapped).
