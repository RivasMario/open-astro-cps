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

## Block type id → wire item id (SOLVED)

The ids PatPort pushes per block (1–300) are ISH **block type** ids; the RCMP
wire / `.cpg` tag is the **item id**. The link is in PatPort's block builders:
the block lookup (`0x7d6dd8`) dispatches on the type (nested jump tables and
compare chains) to a builder; most builders hard-code the item id as the first
argument of `CgIshBlkLayoutAttrib(item_id, 0, 0, 0)` (and validate it is in
1..0xFFFD), while one shared generic builder (`0xc47ac2`) takes the item id as
its 4th argument and switches on it.

`tools/patport_block_map.py` **emulates** the dispatcher (unicorn) once per
type, stubs imported calls, stops at the builder call, and reads the item id →
`schema/block_type_map.json` (169 blocks: 131 from the attribute immediate, 38
from the generic builder's argument). Verified (tests/test_cps_schema.py):

- per partition, the mapped item ids **equal** the object ids CPS addressed in
  the live capture (0x80 164/164, 0x81 3/3, 0x85 2/2); no duplicates;
- every object tag in all 3 real backups has a CPS block type;
- anchors: types 24/43/243 → 4100/4101/4102 (0x81), 239/238 → 4798/4799 (0x85).

## .cpg object directory (Strm_0) — VERIFIED

`DataStg/Strm_0` (RC4) is N 10-byte big-endian records
`<item_id><instance><partition><stream_crc><stream#>` + a 2-byte trailer (not a
plain CRC-16 of the records; unverified). Every entry matches its stream's
tag/instance/CRC on all 3 backups (146 / 110 / 500 entries), and the partition
equals the one CPS assigns that block. So a `.cpg` says where each object is
written — `CpgWriteAssembler.from_cpg` now takes partitions from the file and
needs no capture (`CpgParser.directory()`).

## Next: field layouts

Each builder also constructs the block's fields — PatPort makes ~2,580
field-layout calls (2,349 `CcgIshNumFieldLayout`, 64 `Str`, 43 `Name`, 91
`List`, 33 `Union`, 1 `Char`) with offsets/sizes as arguments. Extracting them
per builder (now that every builder is known) gives an authoritative per-object
field schema for the decoder (open item #4).

## Write path: who builds the RCMP session (2026-10-23)

- `UdcDrIsh10c.dll` is CPS's device read/write layer (`CudcDrIshDoc`):
  `OpenRadio`, `AppCanWriteToDevice`, `OkayToWriteImageToDevice`,
  `GetDataToBeWritten`, `WriteToDevice`, `RetryOnWriteFailure`,
  `AppEndOfWriteToDevice`, `GetCodeplugFromDevice`.
- `WriteToDevice` packs the **entire codeplug image into one SAFEARRAY of
  bytes** and makes a single COM call: `IVirtualRadio::WriteCodeplug`
  (vtable `+0x28`). CPS itself never issues RCMP records.
- `IVirtualRadio` is implemented by `NextGen10.dll` (type library `NEXTGENLib`).
  The session (program mode, unlock, write list, commit) is assembled there by
  `IRcmpBundler`, whose methods include `EnterProgramMode`,
  `UnlockIshPartition`, `WriteIshList`, `ReadIshList`, `readIshIDSet`,
  `DelIshItem`, `DelIshTypes`, `ClearHostMarker`, `WriteMarkers`,
  `RestoreHostMarker`, `GetRadioUUID`, `ResetRadio`, `ReadSoftPotValues`,
  `WriteSoftPotValues`.
- `WritePartitionToDevice` is an unfinished stub in the shipped build: it logs
  "Waiting on Virtual Radio APIs from Earl..." instead of writing.

The exact call order inside `NextGen10`'s `WriteCodeplug` was not extracted.
The practical source of truth for the record-level sequence is the captured CPS
write session (home PC pcap), whose shape is in docs/RCMP_WIRE_PROTOCOL.md.
