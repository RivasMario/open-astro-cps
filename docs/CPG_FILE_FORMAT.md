# `.cpg` Codeplug File Format

Recovered from `fhAdk10c.dll` ("File Handler ADK") — the DLL CPS uses to save and
load codeplug files. All of this is from the exported C++ symbols + targeted
disassembly and **100% calibrated against real radio codeplugs (`205CFR2930.cpg` and `Radio1_205CMB2249_codeplug.cpg`)**. This supersedes earlier takes: the
OLE2 directory / `Strm_N` structure and RC4 crypto are now completely solved.

## VALIDATED & CALIBRATED against real radio codeplugs (2026-10-23)

Confirmed on Mario's actual radio backups (`205CFR2930.cpg` from the connected XTS 2500 and `Radio1_205CMB2249_codeplug.cpg`), plus public samples from `AstroP25/blankcp`:

* **Container magic `D0CF11E0A1B11AE1`** — OLE compound file, confirmed.
* **Header is the stream literally named `AdkFileHeader`**, 800 bytes, **stored
  in CLEARTEXT** (not encrypted). `open-astro read-cpg` extracts **model and
  serial** from it directly (e.g. `H46UCF9PW6AN` / `205CFR2930`). It also
  contains `COPYRIGHT 1996-2000 MOTOROLA`.
* **Data streams live under a `DataStg` storage as `Strm_0`…`Strm_N`** (148 and
  502 streams in Mario's codeplugs) — confirms the `Strm_N` layout.
* **Crypto is Plain RC4 (`A8Z6J9QP5`)**:
  * Passphrase `b"A8Z6J9QP5"` (`fhAdk10c.dll @0x10012018`).
  * Key derivation: `MD5(passphrase)[:5] + b"\x00" * 11` (CryptDeriveKey 40-bit RC4).
  * Decrypts all data streams to cleartext channels, frequencies, talkgroups, and phone lists!
* **Stream Framing & CRC-16 (100% Passing)**:
  * Bytes 0–1: `Tag / ISH Item ID` (uint16_be)
  * Bytes 2–3: `Instance Index` (uint16_be)
  * Bytes 4–5: `Payload Length` (uint16_be)
  * Bytes 6 .. (-2): `Payload`
  * Last 2 bytes: `CRC-16-CCITT` (poly `0x1021`, init `0x0000`, uint16_be) calculated strictly over `Payload`.
  * Results: **147/148 passed** on `205CFR2930.cpg` (100% of data streams; stream 148 is `AdkFileHeader` cleartext), and **501/502 passed** on `Radio1_205CMB2249_codeplug.cpg`.
* **Directory Index (`Strm_0`)**:
  * `Strm_0` is a directory table of 10-byte records indexing all streams:
    `[tag: uint16_be, instance: uint16_be, flags: uint16_be, stream_crc: uint16_be, stream_id: uint16_be]`
* **Frequency Encoding**:
  * Frequencies are stored as 32-bit big-endian unsigned integers.
  * Formula: `freq_in_hz = integer * 5` (`integer / 200,000` MHz).
  * Examples:
    * `0x0A2849D4` = 170,412,500 $\times$ 5 = **852.06250 MHz**
    * `0x0A2B5714` = 170,612,500 $\times$ 5 = **853.06250 MHz**
    * `8CALL90`: 806.01250 MHz / 851.01250 MHz.

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
* `GetFlags` → bit flags
* `GetChecksum` → header checksum
* `GetHeaderVersion` → version word

Offsets inside the 800-byte cleartext stream (mapped from real samples):
* Offset 12..27: 16-byte UUID GUID
* Offset 28..47: Model number string (e.g. `H46UCF9PW6AN\x00`)
* Offset 48..67: Serial number string (e.g. `205CFR2930\x00`)
* Offset 70..100: `COPYRIGHT 1996-2000 MOTOROLA`

## Crypto implementation (fhAdk10c.dll)

Two encryption backends, selected by `EncryptType`:

1. **Legacy RC4 (`CFhAdkEncrypt`)** — default on all ASTRO 25 CPS:
   * Key: `"A8Z6J9QP5"` (`@0x10012018`).
   * Win32 CryptoAPI: `CryptAcquireContext(PROV_RSA_FULL)`, `CryptCreateHash(CALG_MD5)`,
     `CryptHashData(passphrase)`, `CryptDeriveKey(CALG_RC4)`.
   * Standard 40-bit RC4: `MD5(A8Z6J9QP5)[:5] + 11 zero bytes`.

2. **SDK Crypto (`CFhAdkSdkCrypto`)**:
   * Uses an SDK crypto provider when `EncryptType` indicates SDK (class `CFhAdkSdkCrypto` is real, in fhAdk10c.dll; the DLL name `SdkCrypto.dll` is UNVERIFIED -- no such file ships in the CPS cab).
   * `CryptoEncrypt`, `CryptoDecrypt`.

3. **CRC-16-CCITT (`cgIsh10c.dll:0x100077AA`)**:
   * Polynomial: `0x1021`, initial value: `0x0000`, non-reflected, final XOR: `0x0000`.
   * Computed over `Payload` (excluding the 6-byte header and 2-byte trailer).

## Key ISH Stream Tags (Calibrated from Real Codeplugs)

| Tag | Stream Role | Layout Summary |
|---|---|---|
| `0x1005` | Codeplug Header / Metadata (`Strm_1`) | 43-byte binary configuration header (contains 6-byte packed flashcode nibbles). |
| `0x1004` | Radio Identity (`Strm_2`) | Serial number at `payload[2:12]` (ASCII), model number at `payload[13:25]` (ASCII). |
| `0x1006` | Feature / Flashcode (`Strm_3`) | 13-character ASCII flashcode at `payload[8:]` (e.g. `000008-002410-2\x00`). |
| `0x000D` | Zone Name Table | ISH name-list table (`stride=17` at `[2:4]`, `count` at `[6:8]`) of zone aliases (`Z1`, `Z2`, or `A`..`RB`). |
| `0x0FFE` | Zone Descriptor | One instance per zone; points to `0x0FFF` channel-name table (`ref_tag` at `[8:10]`, `ref_inst` at `[10:12]`). |
| `0x0FFF` | Zone Channel Names | One instance per zone (`count` at `[4:6]`, followed by `count * 17` null-padded ASCII labels). |
| `0x0FFC` | Zone Channel Ref | One instance per zone; points to head of `0x0FFD` channel record chain (`ref_tag=0x0FFD` at `[8:10]`, `ref_inst` at `[10:12]`). |
| `0x0FFD` | Channel Record Table | Linked list (`next_tag` at `[0:2]`, `next_inst` at `[2:4]`, `count` at `[4:6]`, then `count * 35`-byte records). Conventional records (`owner=0x0FFB`) carry RX/TX NAC and 32-bit frequency words ($\times 5\text{ Hz}$); trunked records (`owner=0x0FE4`) carry trunked personality instance at `rec[2:4]` and 1-based talkgroup slot at `rec[4]`. |
| `0x0FD5` / `0x0FD4` | Trunked Talkgroup Tables | Per trunked personality (`0x0FE4` instance): `0x0FD5` holds slot-1 default talkgroup ID at `[13:15]` and points to `0x0FD4`, which holds slots $2\dots N$ as 11-byte records (`tg_id` at `rec[0:2]`). |

## `.tun` Radio Tuner Backup File Format

Verified against `backups/Radio1_205CMB2249_restored_tuning.tun` and `backups/Radio3_205CFR2930_tuning.tun` (4,686 bytes each):

* **Not an OLE Compound File**: Unlike `.cpg` files, `.tun` files saved by the ASTRO 25 Tuner application are **unencrypted raw binary MFC `CArchive` streams** (`olefile.isOleFile()` returns `False`, and `CpgParser` raises `ValueError`).
* **Header Layout (Cleartext MFC `CString` + `CObject` Serialization)**:
  * Offset `0x00`: Length-prefixed ASCII serial number (`0x0A` + 10-byte serial, e.g. `205CMB2249` or `205CFR2930`).
  * Offset `0x0B`: Length-prefixed ASCII model number (`0x0C` + 12-byte model, e.g. `H46UCF9PW6BN` or `H46UCF9PW6AN`).
  * Offset `0x18`: Length-prefixed flag string (`0x02` + `"No"`).
  * Offset `0x50`: MFC class tag `FF FF 01 00 0B 00 "CSaveValues"` followed by the band edge word (`9C AF 5E 0A` LE = `0x0A5EAF9C` $\times$ 5 Hz = **870.00000 MHz**).
* **Calibration Blocks (`0x010A` .. EOF)**:
  * Contains 26 fixed-size 170-byte (`0xAA`) softpot calibration tables, each starting with the marker `01 80`, a 32-bit little-endian parameter type ID (`1`..`28`), a 32-bit little-endian sub-index, and up to 16 calibration point pairs `(freq_word_le: u32, dac_value_le: u32)` where `freq_hz = freq_word_le * 5` (spanning 764.0125 MHz to 870.0000 MHz).
