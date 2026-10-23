# `.cpg` Codeplug File Format

Recovered from `fhAdk10c.dll` ("File Handler ADK") — the DLL CPS uses to save and
load codeplug files. All of this is from the exported C++ symbols + targeted
disassembly (no sample `.cpg` was available to validate against yet — confidence
noted per item). This supersedes the vague/contradictory earlier takes: the
Fedora `CPS_BINARY_ANALYSIS.md` §3/§4 ("no Jet DB; maybe OLE compound file, not
checked") and the `FEDORA_RADIO_PROTOCOLS_GUIDE.md` §6 "relational stream layout"
— the latter's **OLE2 directory / `Strm_N` structure is now confirmed correct.**

## Container: OLE Structured Storage (Compound File) — confirmed

`CFhAdkIshArchHandler` (the codeplug/"ISH archive" handler) is built entirely on
COM `IStorage` / `IStream`: `IsStructStgFile`, `ReadStructStgFile`,
`CreateStreamMap`, `ReadDataStream`, `WriteStream`, `GetDataStreamMap`,
`StrmNameToStrmNum`, `OrderStreamStats` (via `IEnumSTATSTG`). So a `.cpg` is a
**Microsoft OLE Compound File** (magic `D0 CF 11 E0 A1 B1 1A E1`) — the same
container as a legacy `.doc`/`.xls`. Python can open it directly with `olefile`.

Not Jet, not a flat blob. It's a storage tree of **named streams**, each stream
one ISH data item.

## File header: `AdkMotFhHeader`, 800 bytes

`CFhAdkFileHeader::GetHeaderSize` returns **`0x320` = 800 bytes** (`mov ax,0x320;
ret`). The header object (`AdkMotFhHeader`) carries, via its accessors:

* `GetModelNo` → model number (CString)
* `GetSerialNo` → serial number (CString)
* `GetUUID` → a `_GUID` (16 bytes) — the file's UUID
* `GetEncryptionType` → `EncryptType` enum (legacy vs SDK crypto)
* `GetAdkType` → `AdkType` enum (codeplug vs tuner vs other)
* `GetCheckSum` + `IsHeaderOK` → header integrity via a checksum callback
* `IsEncrypted`, `IsUsingSdkCrypto`, `IsUsingSmartNet` → feature flags
* `GetInvalidLogBeginPosition` / `GetInvalidLogSize` → an "invalid field" log region

Exact byte offsets **within** the 800-byte header are not yet mapped (needs a
sample file or more disasm of `ReadFromFile`/`WriteToFile`). Known: it is read
whole from the OLE root (`ReadFromFile(IStorage*)` / `ReadFromFile(CFile*)`),
the model/serial/UUID identify the target radio, and the header has its own
checksum separate from the per-stream checksums.

## Payload: named, encrypted ISH data streams

Inside the storage, each codeplug block is a stream. The handler:

1. Enumerates streams (`IEnumSTATSTG`, `OrderStreamStats`), maps stream name ↔
   number (`StrmNameToStrmNum`, `GetWcName`), builds a `StreamMap`
   (`CMap<..DataStrmInfo..>`).
2. For each stream: `ReadDataStream` → **decrypt** (`CFhAdkEncryptDecrypt`, chosen
   per `EncryptType`) → verify (`VerifyStreamData`, `CalcDirStrmChecksum`).
3. Writing reverses it: `WriteStream` encrypts + `WriteStructStgData`.

The stream naming/`Strm_N` numbering and per-stream content (radio identity,
conventional personalities, zones, channel names, keysets, etc.) line up with
`FEDORA_RADIO_PROTOCOLS_GUIDE.md` §6's stream table — treat that table as the
**content map to validate** once a real `.cpg` is in hand; the container shape it
assumed is now confirmed.

## Crypto: legacy RC4 or "SDK crypto"

Two interchangeable implementations behind `CFhAdkEncryptDecrypt`
(MFC `GetRuntimeClass` dispatch; `EncryptType`/`IsUsingSdkCrypto` selects):

* **`CFhAdkEncrypt` (legacy).** A per-byte stream cipher: `Encrypt` allocates
  `2*len + 0xa`, then loops `encryptChar(byte, …)` over the input with a
  `randomGenerator`/`getRandomValue` salt (so output carries a random prefix and
  is expanded). This is the RC4 path keyed by the master key **`A8Z6J9QP5`**
  (`MD5("A8Z6J9QP5")[:5]` → 40-bit RC4, confirmed at `fhAdk10c.dll:0x10012018`).
* **`CFhAdkSdkCrypto` (newer).** A separate, stronger "SDK crypto" class
  (15 string refs) selected when the header says so — not yet dissected; likely
  the modern/stronger option. `IsSdkCryptoSupported` gates it.

Checksums: `fhAdkCalcChecksum` (8-bit, file layer) for the header/file;
`CalcDirStrmChecksum` + the `cgIsh10c` CRC-16-CCITT (poly `0x1021`) for stream
content.

## Sibling formats (same DLL, not the codeplug)

* `CFhAdkSRecHandler` — Motorola **S-record** (firmware/flash hex).
* `CFhAdkPbtHandler` — **PBT** text/config export (`WriteCfgLine`, VARIANT rows).
* `CFhAdkDosArchHandler` — a DOS/preamble-wrapped archive (`CalcPreambleCS`).
* `CFhAdkInvIshArchHandler` / `InvRideArchHandler` — "invalid field list" / RIDE.

## What this unlocks (offline, no radio)

An **offline `.cpg` reader** is now buildable without a radio:

1. `olefile.OleFileIO(path)` — open the compound file, list streams.
2. Read the 800-byte header stream → model/serial/UUID/encryption flags.
3. For each data stream: RC4-decrypt with the `A8Z6J9QP5`-derived key (legacy) and
   verify the CRC-16.
4. Map streams to the schema (`cgIsh10c` block/field dictionary — next target) to
   turn raw bytes into channels/zones/keysets.

**Blocked only by:** a sample `.cpg` to validate against (none on the Drive yet —
export one from CPS, or save one from a radio read), the exact 800-byte header
field offsets, and the `cgIsh` block/field schema (separate target). The SDK-crypto
path also needs dissection if any real file uses it instead of legacy RC4.
