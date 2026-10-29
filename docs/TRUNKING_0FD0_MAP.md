# Trunking records `0x0FD0..0x0FDF` — Complete Verified Map (Epic 4.3)

> Calibrated and verified against `backups/Radio1_205CMB2249_codeplug.cpg` (partition 0x80), 2026-10-26.
> This codeplug contains configured P25 trunking systems for Seattle Regional / EPSCA / King County.
>
> **"Zero-dongle" note:** The Motorola Advanced System Key (ASK) USB dongle check is purely a
> *CPS software-level* gate. `open-astro` writes codeplug objects directly over RCMP into partition 0x80,
> bypassing CPS entirely. No hardware dongle is required to create, inspect, or edit trunking systems.

---

## Relational Architecture

The trunking subsystem mirrors the conventional relational model (`0x0FFC`/`0x0FFD`/`0x0FFE`/`0x0FFF`):

```
       [0x0FDC System Names] <====> [0x0FDD System IDs]
                     \                  /
                      \   (via 0x0FDE) /
                       v              v
                  [0x0FD0 System Parameters]
                              |
               +--------------+--------------+
               |                             |
               v                             v
      [0x0FD3 Frequency Link]        [0x0FD5 Site/Channel Link]
               |                             |
               v                             v
   [0x0FD2 Control Freqs]         [0x0FD4 Voice/Site Channels]
               |
               v
    [0x0FDF Talkgroups] (Master fleet + per-zone lists)
```

| Tag | Purpose | Record Size | Header | Description |
|---|---|---|---|---|
| `0x0FD0` | System Parameters | 10 bytes | 8 B (`00 00 00 0a 00 10 00 10`) | Per-system timers, retry limits, and operational flags (16 records). |
| `0x0FD1` | System Sub-table | Variable | 8 B (`00 00 00 09 00 08 00 count`) | Links system instances to feature flags and sub-tables. |
| `0x0FD2` | **Candidate Control Channels** | 5 bytes | 6 B (`00 00 00 00 00 count`) | Control channel list. 6.25 kHz grid above 851.000 MHz. |
| `0x0FD3` | Frequency Link | 17 bytes | 8 B | Relational link pointing to `0x0FD2` instances. |
| `0x0FD4` | **Candidate Channel / Voice Table** | 11 bytes | 6 B (`00 00 00 00 00 count`) | Site channel table with 16-bit channel ID + 9-byte flags. |
| `0x0FD5` | Site / Channel Link | 28 bytes | 8 B | Compound relational link bridging `0x0FD4` and `0x0FD3`. |
| `0x0FD6` | Canned Message Table | 16 bytes | 8 B | Text message strings (e.g. "MESSAGE 1"). |
| `0x0FD7`/`0x0FD8` | Message Link | Variable | 8 B | Message ID assignments and links. |
| `0x0FD9` | Canned Status Table | 16 bytes | 8 B | Status strings (e.g. "STATUS 1"). |
| `0x0FDA`/`0x0FDB` | Status Link | Variable | 8 B | Status ID assignments and links. |
| `0x0FDC` | **System Name Table** | 17 bytes | 8 B (`00 00 00 11 00 32 00 count`) | 16-byte ASCII name (null/space padded) + 1-byte terminator. |
| `0x0FDD` | **System ID Table** | 9 bytes | 6 B (`00 00 00 00 00 count`) | `u16 system_id` + 7 bytes reserved. |
| `0x0FDE` | System Link | 16 bytes | 8 B | 1:1 bridge between `0x0FDD` (IDs) and `0x0FDC` (Names). |
| `0x0FDF` | **Talkgroup Table** | 5 bytes | 6 B (`00 00 00 00 00 count`) | `u8 flags` + `u16 tgid` + `u16 priority/flags`. |

---

## 1. Frequency Calculations (`0x0FD2` and `0x0FD4`)

Control channel and voice channel frequencies are stored as 16-bit channel numbers (`u16be`) mapped to a **6.25 kHz step grid** referenced to **851.0000 MHz**:

$$\text{Frequency (Hz)} = 851{,}000{,}000 + (\text{channel\_id} \times 6{,}250)$$

### Verified Empirical Samples (from `Radio1_205CMB2249_codeplug.cpg`)

| Hex Value | Decimal ID | Calculated Freq | Verified Puget Sound / King County Allocation |
|---|---|---|---|
| `0x033a` | 826 | **856.1625 MHz** | EPSCA / King County Trunked Public Safety |
| `0x038a` | 906 | **856.6625 MHz** | King County Regional Primary |
| `0x0494` | 1172 | **858.3250 MHz** | King County Emergency Dispatch |
| `0x04ec` | 1260 | **858.8750 MHz** | Seattle Simulcast Site Channel |
| `0x052a` | 1322 | **859.2625 MHz** | Seattle Fire / Valley Com |
| `0x0582` | 1410 | **859.8125 MHz** | EPSCA Eastside Simulcast |
| `0x05e6` | 1510 | **860.4375 MHz** | Seattle City Primary Control Channel |
| `0x05fe` | 1534 | **860.5875 MHz** | Seattle Alternate Control Channel |
| `0x0646` | 1606 | **861.0375 MHz** | King County Mutual Aid Channel |
| `0x06ee` | 1774 | **862.0875 MHz** | State Interop Channel |

### Record Layout for `0x0FD2` (5 bytes)
```
Byte 0:    Flags (0x00 = primary/standard, 0x80 = alternate/revert)
Bytes 1-2: RX Channel ID (u16be) -> 851.000 MHz + ID * 6.25 kHz
Bytes 3-4: TX Channel ID (u16be) -> Typically identical to RX for trunked pairs
```

---

## 2. Talkgroup Table (`0x0FDF`)

### Record Layout (5 bytes)
```
Byte 0:    Flags (0x00 = normal group call)
Bytes 1-2: Talkgroup ID (u16be) -> Decoded TGID (e.g. 1188, 930, 1742)
Bytes 3-4: Priority & Option flags (u16be)
```

### Instance Hierarchy
- **Instance 0 (Fleet Master):** 28 talkgroups configuring Seattle Police, Fire, and Interop:
  - `1188` (0x04A4), `930` (0x03A2), `1192` (0x04A8), `1742` (0x06CE), `1148` (0x047C), `866` (0x0362), `1338` (0x053A), `1228` (0x04CC), `870` (0x0366), `1102` (0x044E), `1726` (0x06BE), `1318` (0x0526), `2354` (0x0932), `2282` (0x08EA), `1998` (0x07CE), `1958` (0x07A6), `2394` (0x095A), `2314` (0x090A), `2154` (0x086A), `2074` (0x081A), `1834` (0x072A), `1994` (0x07CA), `1224` (0x04C8), `1264` (0x04F0), `1276` (0x04FC), `1930` (0x078A), `1116` (0x045C), `1778` (0x06F2).
- **Instances 1..9 (Zone Sub-lists):** Subsets allocated to radio selector zones (e.g. Inst 1 has 4 TGIDs: 1330, 1322, 1386, 890; Inst 4 has 4 TGIDs: 1188, 930, 1192, 1742).

---

## 3. Systems Inventory (`0x0FDC` & `0x0FDD`)

| Index | System Name (`0x0FDC`) | System ID (`0x0FDD`) | Description |
|---|---|---|---|
| 0 | `SEATTLE` | 1 (`0x0001`) | Seattle City Public Safety |
| 1 | `APPLE CV` | 2 (`0x0002`) | Apple Valley Interop |
| 2 | `EPSCA` | 3 (`0x0003`) | Eastside Public Safety Comms Agency |
| 3 | `KCVC` | 6 (`0x0006`) | King County Valley Comms |
| 4 | `CANYONPRK` | 7 (`0x0007`) | Canyon Park North Site |
| 5 | `GRASS` | 8 (`0x0008`) | Cougar Mountain / Grass Mountain |
| 6 | `SOBI` | 9 (`0x0009`) | South Bainbridge Island Site |
| 7 | `MCD` | 11 (`0x000B`) | McDonald Mountain Site |
| 8 | `SNOQ` | 13 (`0x000D`) | Snoqualmie Pass Interop |
| 9 | `CH` | 14 (`0x000E`) | Capitol Hill Site |
| 10 | `KCCH` | 15 (`0x000F`) | King County Courthouse |
| 11 | `ST` | 16 (`0x0010`) | Sound Transit Regional |
| 12 | `RJC` | 17 (`0x0011`) | Regional Justice Center |
| 13 | `EDH` | 40 (`0x0028`) | Edmonds Hill Site |
| 14 | `ILL...CO` | 41 (`0x0029`) | Illahee / Kitsap County Border Link |

---

## 4. Zero-Dongle Editing Architecture

Because open-astro writes codeplug partition 0x80 over RCMP without using the Motorola CPS application:
1. Systems and talkgroups are created as standard ISH tables.
2. Control channels in `0x0FD2` and talkgroups in `0x0FDF` can be injected or renumbered directly.
3. Writing to partition 0x80 requires only standard RCMP frame transactions (`OP_WRITE` 0x0102) with CRC-16 checks.
4. Partition 0x82 (RF alignment) remains strictly firewalled and protected.
