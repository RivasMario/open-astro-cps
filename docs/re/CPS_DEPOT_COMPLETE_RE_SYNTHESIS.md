# ASTRO 25 CPS & Depot — Complete RE Synthesis for OpenAstro Builders

> **Audience:** Any AI agent or developer building `open-astro-cps` (Python or Rust).
> **Scope:** Complete architectural & EEPROM-persistence synthesis from Ghidra 12.2 headless decompilation + `qwen2.5-coder:14b` function-by-function analysis (**544 functions** across Batches 1–6) of Motorola ASTRO 25 Portable CPS & Portable Depot (`R20.01.00`).

---

## 1. Key Discovery: CPS and Depot Share the Exact Same Core Engine

SHA-256 verification of the extracted `R20.01.00` InstallShield `.cab`s proves that **Regular CPS** and **Portable Depot** use **byte-identical** core DLLs:

| Binary | SHA-256 | Shared? |
|---|---|---|
| `NextGen10.dll` | `99fa3efbf1b7aa58722558841336c68035b9c4d562bf656f8f180d4f60348746` | Identical in CPS & Depot |
| `ByteData10.dll` | `08c2e4807d56a5a6c9bb7c608018e1fb3c5dc6f7feda878221f562c8a7028443` | Identical in CPS & Depot |
| `UdcDrIsh10c.dll` | `1859b7a91489edf7b4b600ed397f6dc406153b77ff9de773e150d61ab4a4b266` | Identical in CPS & Depot |
| `EncatenComponent.dll` | `5f2a1fe54770716885e3a7edb50cfa0c38813e9ac6490dfd5e6213084184d4c8` | Identical in CPS & Depot |
| `SECURITYLIB.dll` | `f51a72b66e64ef78908d7a805111e0216e22f62894aad6770f050b278deb4466` | Identical in CPS & Depot |

**Depot-only differences:** `PatPortDepot.exe` (UI) and `PBT2.dll` (Depot-specific helper DLL, analyzed in Batch 5).

---

## 2. The 5-Layer Software Architecture (What the Original Software Actually Did)

1. **Layer 1 — UI Host (`PatPort.exe` / `PatPortDepot.exe`):**
   - MSVC MFC 4.2 GUI that builds the 169-block ISH layout at runtime via `cgIsh10c.dll`.
2. **Layer 2 — Schema, `.cpg` Container & Image Bridge:**
   - `cgIsh10c.dll`: Generic ISH engine defining `AccessRights` (`0 = ReadOnly`, `1 = ReadWrite`, `2 = ReadWriteLocked`) and CRC-16.
   - `fhAdk10c.dll`: `.cpg` file container (40-bit RC4 `"A8Z6J9QP5"`, `DataStg/Strm_0` directory of 10-byte BE records).
   - `UdcDrIsh10c.dll`: `CudcDrIshDoc::WriteToDevice` packs the full codeplug image into a COM `SAFEARRAY` and makes one COM call: `IVirtualRadio::WriteCodeplug` (`+0x28`). (`WritePartitionToDevice` is an unimplemented stub.)
   - `EncatenComponent.dll` / `udcDrXAdk10c.dll`: Image assembly / import-export helpers.
3. **Layer 3 — Virtual Radio & RCMP Engine (`NextGen10.dll`, 1,373 non-thunk funcs — WHERE PERSISTENCE LIVES):**
   - `CVirtualRadio::WriteCodeplug` (`FUN_1001c92d`) orchestrates:
     1. `LoadServer` (`FUN_1001d137`)
     2. `VerifyRadioParamsForWrite` (`FUN_1001d472`)
     3. `PopulateRadioParams` (`FUN_1001ddc8`)
     4. `WriteDataToRadio` (`FUN_1001df9a` $\rightarrow$ `FUN_1000fe49` + COM vtable `+0x1c`/`+0x30`)
   - `CRcmpBundler` manages the radio state machine:
     - `Open` (`1000c01f`, `0x0106`), `EnterProgramMode` (`10011a98`), `EnterWriteMode` (`10016776`, mode `4`)
     - `UnlockSecurity` (`1000cce7`, `0x0107` + LFSR `1000fd89`, seed `0x51E88D21`, tap bit 9) — required for `0x81` persistence
     - `DelIshTypes` (`10009f15`, `0x0103`), `DelIshItem` (`10009e3f`), `WriteIshList` (`1000ab20`, `0x0101`)
     - `Send ReOrg` (`1001773c`, builds `[0x01, 0x07, 0x80, 0x00]` + CRC-16 `FUN_100177e1` $\rightarrow$ `SendRcmp` `1000b5b0`)
     - `ResetRequest` (`100135cd`, builds `[0x02, 0x00, 0x0D]`)
     - `Close` (`1000ca08`)
   - `CRcmpProtocol`: `SendRcmp` (`1000b5b0`), `BundleTCP` (`100187b6`, 2-byte BE length prefix), `SendRequest` (`10018123`, `<= 0x410` chunks), `OpenPort` (`10017c71`, routes modes `{4,8,9,10}` to TCP/IP-PPP and `{3,5,7,0xC,0xD}` to direct/serial, passing the 16-byte UUID on `0x0D`).
4. **Layer 4 — Transport Glue, Custom PPP & Serial (DO NOT REIMPLEMENT AS COM):**
   - `ByteData10.dll` (`415` funcs): Pure transport glue (`CRawBytes::Open` `1100421d`, `fudally_usb.dll` `11005601`, `ConnWinSock10.dll` loader `11004c4b`). Contains **zero** EEPROM/commit logic.
   - `ConnWinSock10.dll` (`144` funcs): `OpenSock`, `CloseSock`, `OpenPPP`, `ReadData`, `BroadcastData`, `RequestData`.
   - `RadioCustStack10.dll` (`382` funcs): USNET embedded PPP+TCP (`PPPConnect@1000ee10`, `PPPHandshake@1000ef60` `"CLIENT"`/`"CLIENTSERVER"`, async-HDLC).
   - `PortManager10.dll` (`186` funcs), `PatComm10.dll` (`177` funcs), `RadioSerial10.dll` (`111` funcs): Win32 COM/USB enumeration and serial I/O.
   - `otaprwcdtimer.dll` (`72` funcs): Windows Registry (`CPSinVals` / `OTAP_ABORT_FLAG`) timer/lock flags.
5. **Layer 5 — Radio Flash / EEPROM Partitions (`192.168.128.1:8002`):**
   - **`0x80` (`ReadWrite`, `0x10020000`, 384 KB, 164 block types):** Codeplug (channels, zones, personalities, ADP keys). Persists permanently after `0x0106 00` $\rightarrow$ `0x0102` $\rightarrow$ `0x0103` $\rightarrow$ `0x0101` $\rightarrow$ `0x0106 01`.
   - **`0x81` (`ReadWriteLocked`, `0x1000A000`, 16 KB, 3 block types):** `0x1004` Serial, `0x1005` 43-byte FLASHcode bitmask, `0x1006` 16-byte FLASHcode string. Bootloader silently drops `0x81` writes unless `0x0107` `UnlockSecurity` succeeds first.
   - **`0x85` (`ReadWriteLocked`, 2 block types):** `0x12BE`, `0x12BF`.
   - **`0x82` (`ReadOnly`, `0x10100000`, 512 KB):** RF alignment soft-pots. **NEVER WRITE.**

---

## 3. How to Build the Better OpenAstro Replacement

Future agents should **not** replicate Motorola's 7-layer COM/`SAFEARRAY`/Windows-Registry/dual-PPP architecture:

1. **Collapse Layers 1–4 into one clean pipeline:**
   `JSON/YAML Codeplug` $\rightarrow$ `ISH Schema Encoder (schema/field_layouts.json)` $\rightarrow$ `RCMP Framer` $\rightarrow$ `Windowed PPP/TCP (or OS pppd)`.
2. **Keep schemas declarative (`schema/*.json`),** never compiled into C++ classes.
3. **Enforce hardware safety in code:**
   - Hard-block Partition `0x82` in `PartitionPolicy`.
   - Gate writes with `--expect-serial` (`0x1004`) and mandatory `.cpg`/JSON backup.
   - Use ACK-tracked, window-bounded TCP (`ppp_link.py` or Rust `open_astro_cli`) so writes never overrun the radio MCU.
   - Always run post-write read-back verification.
4. **One remaining gap for `0x81` persistence:** Confirm `WIRE_PROFILE_CONFIRMED = True` in `src/open_astro/protocol/unlock_session.py` by capturing one live CPS `0x81` write over `device 5` (or against a mock radio in `LXC 120`).

---

## 4. Full RE Artifact Index

- Visual Tarkov/Architecture Dashboard: [astro25_re_dashboard.html](astro25_re_dashboard.html)
- Logical Architecture & Coverage Map: [ASTRO25_DECOMPILATION_STATUS_MAP.md](ASTRO25_DECOMPILATION_STATUS_MAP.md)
- Batch 1 (`NextGen10` + `ByteData10`, 20 funcs): [HOMELAB_AI_EEPROM_PERSISTENCE_ANALYSIS.md](HOMELAB_AI_EEPROM_PERSISTENCE_ANALYSIS.md)
- Batch 2 (`WriteCodeplug` callees + `ByteData10`, 26 funcs): [HOMELAB_AI_EEPROM_BATCH2.md](HOMELAB_AI_EEPROM_BATCH2.md)
- Batch 3 (`NextGen10` Trace3 + `ConnWinSock10` + `NewProto10` + `PortManager10`, 56 funcs): [HOMELAB_AI_BATCH3_TRACE_AND_UNOPENED.md](HOMELAB_AI_BATCH3_TRACE_AND_UNOPENED.md)
- Batch 4 (`PatComm10` + `RadioSerial10` + `otaprwcdtimer`, 53 funcs): [HOMELAB_AI_BATCH4_SERIAL_AND_OTAP.md](HOMELAB_AI_BATCH4_SERIAL_AND_OTAP.md)
- Batch 5 (`EncatenComponent`, Depot `PBT2.dll`, `RemoteProtocols01`, `UdcDrIsh10c`, `udcDrXAdk10c`, 349 funcs): [HOMELAB_AI_BATCH5_CABS_AND_DEPOT.md](HOMELAB_AI_BATCH5_CABS_AND_DEPOT.md)
- Batch 6 (`SECURITYLIB.dll` + `authAES.dll`, 40 funcs): [HOMELAB_AI_BATCH6_SECURITY_AND_AUTHAES.md](HOMELAB_AI_BATCH6_SECURITY_AND_AUTHAES.md)
- Batch 7a (`fudally.sys`, `Security.exe`, `PortMgrWrapper`, `PSTWrapper`, `RemoteRadioProg`, 89 funcs): [HOMELAB_AI_BATCH7_DRIVERS_AND_WRAPPERS.md](HOMELAB_AI_BATCH7_DRIVERS_AND_WRAPPERS.md)
- Mobile Depot (`ASTRO_25_MOBILE_DEPOT_R15.00.00.zip`, `XTL`/`PM` `G*` options & R15 DLLs): [MOBILE_DEPOT_RE_PLAN.md](MOBILE_DEPOT_RE_PLAN.md)
