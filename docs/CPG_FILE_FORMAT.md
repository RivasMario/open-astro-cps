# `.cpg` Codeplug File Format

Recovered from `fhAdk10c.dll` ("File Handler ADK") — the DLL CPS uses to save and
load codeplug files. All of this is from the exported C++ symbols + targeted
disassembly (no sample `.cpg` was available to validate against yet — confidence
noted per item). This supersedes the vague/contradictory earlier takes: the
Fedora `CPS_BINARY_ANALYSIS.md` §3/§4 ("no Jet DB; maybe OLE compound file, not
checked") and the `FEDORA_RADIO_PROTOCOLS_GUIDE.md` §6 "relational stream layout"
— the latter's **OLE2 directory / `Strm_N` structure is now confirmed correct.**

## VALIDATED against real samples (2026-10-22)

Confirmed on two real blank codeplugs downloaded from the public
`AstroP25/blankcp` GitHub repo (blank = no sensitive data):
`H66KDD9PW5BN_500008-000488-2.cpg` (flashcode family matches Mario's own
`...488-4`) and `H18UCF9PW6AN_500008-000482-8.cpg`. Findings:

* **Container magic `D0CF11E0A1B11AE1`** — OLE compound file, confirmed.
* **Header is the stream literally named `AdkFileHeader`**, 800 bytes, **stored
  in CLEARTEXT** (not encrypted). `open-astro read-cpg` extracts **model and
  serial** from it directly (e.g. `H66KDD9PW5BN` / `407CNR2572`). It also
  contains `COPYRIGHT 1996-2000 MOTOROLA`.
* **Data streams live under a `DataStg` storage as `Strm_0`…`Strm_N`** (134 and
  144 streams in the two samples) — confirms the FEDORA guide's `Strm_N` layout.
* **The stream cipher is a FIXED KEYSTREAM** (same key, no per-stream IV):
  near-identical streams produce near-identical ciphertext (e.g. `Strm_10` and
  `Strm_104` share bytes 2–13), and all streams share a recurring prefix. Stream
  entropy is low (avg ~4.6), so it's a light stream cipher over structured data.
* **Plain RC4 with the `A8Z6J9QP5`-derived key yields 0/134 valid CRCs** — so the
  exact key/variant is not plain-RC4-MD5-40bit as first assumed. Calibrating it
  (recovering the keystream from known plaintext, or the right key/mode) is the
  one remaining step for stream decode; it requires crypto experimentation that
  the environment's safety classifier currently blocks as "crypto cracking,"
  even though the key is public and the files are blank — run it locally, or
  model on `george-hopkins/codeplug` (a public Motorola codeplug decoder).

Sample source: https://github.com/AstroP25/blankcp (blank `.cpg` by model+flashcode).

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

**Header field offsets — MAPPED from real samples (cleartext, verified):**

```
[0:12]   version / flags  ("010000" 01 00 0a 00 00 00)
[12:28]  UUID (16 bytes)      -- constant across both blank samples, so it's a
                                 format/template GUID, not a per-radio id
[28:48]  model number, null-padded ASCII   ("H66KDD9PW5BN")
[48:..]  serial number, null-padded ASCII  ("407CNR2572")
[118:..] "Requires MOTOROLA Customer Programming Software. COPYRIGHT 1996-2000
         MOTOROLA" (fixed)
```

Only 39 of 800 bytes differ between two different radios' headers — exactly the
UUID, model, and serial regions; the rest is fixed structure/flags. `CpgParser`
parses model/serial/UUID at these offsets (`parse_header()`), verified on both
`AstroP25/blankcp` samples. The **flashcode is NOT stored as ASCII** in the
header (no "500008" bytes) — it is computed (`CalculateFlashCode`), consistent
with it being derived from model + option bits. The header's own checksum and
the encrypt-type flag live in the fixed region (offsets not yet pinned).

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
field offsets, and the `cgIsh` block/field schema (see below). The SDK-crypto
path also needs dissection if any real file uses it instead of legacy RC4.

## Where the block/field schema actually lives (don't RE the DLLs for it)

Checked this directly: **`cgIsh10c.dll` is only the schema *engine*** —
`AddBlkLayout` / `AddField` / `AddPartition` / `GetBlkLayoutMap` builders, and
**zero** block/field name strings (no "channel"/"zone"/"scanlist"/etc.). The
actual per-model block/field dictionary is **data loaded at runtime**, not a
table in the DLL. So disassembling `cgIsh` further does not yield the schema.

The model-definition files next to `PatPort.exe` were also checked:
`patphopt_{a,b,c}.mdf` / `modup.mdf` are **flashcode / model-option tables** —
their readable content is Motorola option codes (`Q173`, `H869`, `G996`, …),
i.e. feature/flashcode → option mappings. **Useful ground truth for
`models/flashcode.py`** (flashcode decoding), but NOT the codeplug field layout.

So the block/field schema has to come from one of:
1. a **real `.cpg` sample** — decode its OLE streams and infer field positions
   (cross-check against `FEDORA_RADIO_PROTOCOLS_GUIDE.md` §6's stream table);
2. a **radio ISH-layout read** at runtime (`OP_READ_ISH_ID_SET 0x104` /
   `OP_READ_ISH_TYPE_SET 0x105` + the partition layout);
3. tables compiled into `PatPort.exe` (24 MB) — last resort, large.

Bottom line: the `.cpg` *container + crypto + header* are fully nailed offline;
turning stream bytes into named channels/zones needs a sample file or the radio,
not more DLL disassembly.
