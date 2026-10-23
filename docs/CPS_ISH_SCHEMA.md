# CPS ISH schema — what the DLLs actually say (2026-10-23)

Source: ASTRO 25 Portable CPS R20.01.00 InstallShield cab (`data1.hdr` +
`data1.cab` + `data2.cab`), unpacked with `unshield 1.6.2` (on Fedora WSL —
there is no Windows build; the cab is `ISc(` InstallShield, not MSCF, so 7z /
cabextract don't work). No Motorola binaries are committed; only derived facts.

## Where the schema lives

| File (in cab) | Role |
|---|---|
| `RDK DLL_s\cgIsh10c.dll` | **Generic ISH engine** — a C++ class library (`CcgIshCpLayout`, `CcgIshPartitionLayout`, `CcgIshBlkLayout`, `CcgIsh*FieldLayout`, `CcgIshXmlData`, …; 627 exports). It holds no concrete schema tables. |
| `CPS_Application_Files\PatPort.exe` | **The CPS app — builds the concrete codeplug layout at runtime** by calling the engine. This is where the schema is. |
| `RDK DLL_s\udcIsh10c.dll`, `UdcDrIsh10c.dll` | UDC document layer over the engine (imports `cgIsh10c`). |
| `CPS_Application_Files\*.mdf` | `modup.mdf`, `patphopt_{a,b,c}.mdf` — packed/compressed blobs with a shared header (`PE`/`PG` magic). Not decoded. |

## Partition layout (VERIFIED, from code)

`PatPort.exe` calls `CcgIshCpLayout::AddPartition(WORD partition, AccessRights)`
exactly three times, with immediate arguments:

| Partition | AccessRights | Meaning | Block layouts |
|---|---|---|---|
| `0x80` | 1 | ReadWrite | 164 |
| `0x81` | 2 | ReadWriteLocked | 3 |
| `0x85` | 2 | ReadWriteLocked | 2 |

- The **AccessRights enum** comes from the engine's own comparators:
  `CcgIshBlkLayout::IsReadOnly` tests `== 0`, `IsReadWrite` `== 1`,
  `IsReadWriteLocked` `== 2` (field at `this+0x28`).
- **0x82 (tuning / soft-pots) is not part of the CPS codeplug layout at all.**
  It is only addressed by the separate tuner session.
- Block → partition comes from the 169 `CcgIshBlkLayout::SetPartitionNum`
  calls; each partition's block count **equals the number of objects CPS
  addressed in that partition in the live capture** (164 / 3 / 2). Two
  independent sources, same answer.
- "Locked" partitions (0x81, 0x85) need the session unlock step before a write;
  this is what the `OP_UNLOCK 0x0C` / `OP_LOCK 0x0D` / `0104` records around the
  write burst are for. `PartitionPolicy.requires_unlock()` exposes it.

Reproduce: `python -P tools/patport_partition_layout.py <PatPort.exe> <cgIsh10c.dll>`
→ `schema/patport_layout.json`. Enforced by `protocol/write_session.PartitionPolicy`
(in the assembler and the live `RcmpWriteClient`) together with the capture
map `schema/partition_map.json`.

## Block type id ≠ wire object id (OPEN)

The ids PatPort pushes per block (e.g. `0x2b`, `0x18`, `0xf3`; range 1–300) are
ISH **block type** ids. The RCMP wire / `.cpg` tag is a different **item id**
(10–4095, 4100–4102, 4798–4799). Per-partition counts match, and an ordered
pairing looks plausible (0x85: 238→4798, 239→4799) — but that is unproven, so
nothing relies on it.

The mapping (and each block's field layout — names, types, offsets, which is
what full channel/talkgroup/scan-list decoding needs) lives inside per-type
builder functions: PatPort's block lookup `0x7d6dd8` dispatches through jump
tables on `(type >> 3, type & 7)` to a builder per type (`0xd5e14d`,
`0x839088`, `0x65fffc`, …), each constructing `CcgIshBlkLayout` and its
`CcgIsh*FieldLayout`s. Walking those builders is the next RE step and would
give an authoritative field schema for the decoder (open item #4).
