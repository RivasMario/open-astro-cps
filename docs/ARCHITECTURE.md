# ASTRO 25 CPS — Complete Architecture (how every piece works together)

The whole picture, reconstructed from the real ASTRO 25 Portable CPS R20.01.00
binaries (disassembly + cab extraction). This is the map; the per-topic docs
hold the byte-level detail. Read this first.

Detail docs: [`NEXTGEN10_RCMP_DISASSEMBLY.md`](NEXTGEN10_RCMP_DISASSEMBLY.md),
[`CPG_FILE_FORMAT.md`](CPG_FILE_FORMAT.md),
[`ENCRYPTION_MODEL.md`](ENCRYPTION_MODEL.md),
[`PROVENANCE_AUDIT.md`](PROVENANCE_AUDIT.md),
[`AT_INTERFACE_DISCOVERY.md`](AT_INTERFACE_DISCOVERY.md),
[`HARDWARE_GROUND_TRUTH.md`](HARDWARE_GROUND_TRUTH.md),
[`KEYLOADER_ROADMAP.md`](KEYLOADER_ROADMAP.md).

---

## 1. The layers (top to bottom)

```
   PatPort.exe  (the CPS GUI, internal name "RDK")
        │  edits a codeplug in memory; reads/writes radios and .cpg files
        ├──────────────── codeplug model & schema ────────────────┐
        │                                                           │
   cgIsh10c.dll            udcIsh10c.dll / UdcDrIsh10c.dll     fhAdk10c.dll
   codeplug SCHEMA engine  schema <-> editable model            .cpg FILE format
   (blocks, fields,        (normalize into channels/zones/      (OLE compound file,
    partitions, access      scanlists; cross-block refs)         800B header, named
    class, CRC-16)                                               encrypted ISH streams,
        │                                                        RC4 A8Z6J9QP5 / SdkCrypto)
        │
        │   to talk to a radio:
        ▼
   NextGen10.dll  (CRcmpBundler)  — the RADIO PROGRAMMING engine
        │  builds RCMP commands: unlock, get-UUID, enter-write-mode,
        │  read/write ISH items, commit (OP_LOCK + UUID). Opcodes:
        │  0x106 enter-mode, 0x100 read-ISH, 0x101 write-ISH,
        │  0x12 query-UUID, 0xC unlock, 0xD commit. Payload = VT_UI1 SafeArray.
        ▼
   ByteData10.dll  (CRawBytes)  — byte transport glue
        │  hands the RCMP message to the network stack via CUSNETdpi
        ▼
   RadioCustStack10.dll  — a COMPLETE userspace PPP + IP + TCP stack
        │  (CUSNETppp = PPP; CUSNETdpi/CBSDsocket = TCP sockets).
        │  Imports ONLY kernel32/winmm/RadioSerial10 — NO Winsock.
        │  Connects TCP to radio:8002 (local 8001); Nwrite/Nread = TCP send/recv.
        ▼
   RadioSerial10.dll  (CCommPort)  — raw Win32 serial I/O (Open/Read/Write/DCB)
        ▼
   the COM port  ==  the radio's USB CDC-ACM interface (0cad:1001 / ttyACM0)
        ▼
   Motorola XTS 2500 / 5000 radio
```

Parallel, independent path for **encryption keys** (NOT through the above):

```
   KVL / KFD adapter  (Pi Pico cable or KVL clone)  --USB serial, KFDtool protocol-->
        │   3-wire P25 keyfill bus (TRRS) -> Hirose -> radio crypto module
        ▼  loads DES/AES-256 keys via P25 Manual Rekey. Our side: kfdtool.py / kvl_probe.py.
```

---

## 2. Every file, grouped

### 2a. Radio logic — the DLLs that matter (reverse-engineered here)

| File | Role | Status in this repo's docs |
|---|---|---|
| `PatPort.exe` (24 MB) | CPS GUI + top-level orchestration; holds the real opcode strings/RC4 key | partially mapped (opcodes, key) |
| `NextGen10.dll` | `CRcmpBundler` — RCMP radio-programming engine (read/write codeplug over TCP) | **fully mapped** — NEXTGEN10 doc |
| `ByteData10.dll` | `CRawBytes` — passes RCMP bytes to the stack; also has the connect choreography | **mapped** (ports, connect) |
| `RadioCustStack10.dll` | userspace PPP+IP+TCP stack over serial (`CUSNETppp`/`CUSNETdpi`/`CBSDsocket`) | **mapped** — thin TCP send/recv, §1 |
| `RadioSerial10.dll` | `CCommPort` — raw Win32 COM-port I/O | role known (generic serial) |
| `cgIsh10c.dll` | codeplug **schema engine** — blocks/fields/partitions, access class (RO/RW/RWlocked), CRC-16 | **engine mapped**; schema is runtime data |
| `udcIsh10c.dll`, `UdcDrIsh10c.dll` | transform between schema and the app's editable model (channels/zones/scanlists; list/union cross-refs) | role known, not byte-mapped |
| `fhAdk10c.dll` | `.cpg` **file format** — OLE compound file, header, encrypted ISH streams, RC4/SdkCrypto | **fully mapped** — CPG doc |
| `RemoteProtocols01.dll` | legacy SB9600/SBEP/ESBEP COM server (`RemSB9600`) — the *old* hardware-bus transport, not the XTS-USB path | strings only (see CPS_BINARY_ANALYSIS) |
| `PortManager10.dll`, `PatComm10.dll` | device enumeration / port listing | role known |
| `EncatenComponent.dll` | codeplug image assembly/concatenation (suspected) | not yet analyzed |
| `mcomUnknown.dll`, `Macro.dll` | COM plumbing / macro support | not analyzed |
| `Security*/SECURITYLIB.dll`, `iBtn*.dll`, `IB*.dll` | ASK dongle / iButton 1-Wire licensing | not analyzed (niche) |
| `Rdb50c/Rud50c/Rui50c/Prn50c/pip50c.dll` | RDK framework: database / UI / print | generic framework |

### 2b. Data files

| File | Content |
|---|---|
| `patphopt_{a,b,c}.mdf` | flashcode / model-option tables (Q/H/G option codes) — ground truth for `flashcode.py` |
| `modup.mdf` | model-update data (opaque, small) |
| `Codeplug.cpg` (user files) | a saved codeplug — OLE compound file (see CPG doc). None present yet; needed to finish the field schema |

### 2c. Framework / third-party / installer (NOT radio logic — ignore for RE)

MFC42, msvcrt/msvcp60/Msvcirt, OLEAUT32/olepro32/ole32/atl, dbghelp — MS runtimes.
libeay32/ssleay32/ManagedOpenSsl — OpenSSL. WdfCoInstaller/wudf/WinUSBCoInstaller/
difxapi/DPInst/ISBEW64/_isres/_isuser/isrt/winusbcoinstaller — driver + InstallShield
installer. Intro.exe/RSS_Launcher.exe/TSCC.exe/Roboex32.dll/*.swf/*.chm — splash + help.
IBFS32/IBUSB32/IB10E32/ib90usb — Dallas iButton 1-Wire (ASK dongle hardware).

---

## 3. Data flow: reading a codeplug from a radio

1. **Open the link.** `RadioSerial10` opens the COM port (the radio's CDC-ACM).
   The radio is put in data mode via AT: `AT&V` (identity) → `AT#DATLCL=1` →
   `ATD` → `CONNECT` (see AT doc).
2. **Bring up PPP/IP.** `RadioCustStack10::CUSNETppp::PPPConnect` runs LCP+IPCP;
   radio = `192.168.128.1`, host = `.2`.
3. **TCP connect.** `ByteData10` → `CUSNETdpi::Nopen(ip, svc, 8001, 8002, 0)` — a
   normal 3-way handshake to the radio's programming service on **TCP 8002**.
4. **RCMP session.** `NextGen10::CRcmpBundler`: `UnlockSecurity` (0xC) →
   `GetRadioUUID` (0x12) → read the ISH layout/items with `ReadIshList` /
   `OP_READ_ISH` (0x100), each item addressed by its descriptor
   (type/id/partition/offset/length). Bytes travel RCMP-over-TCP (`Nwrite`/`Nread`).
5. **Interpret.** `cgIsh10c` + `udcIsh10c` turn raw ISH block bytes into typed
   fields → channels, zones, scan lists, keysets.
6. **Save.** `fhAdk10c` writes a `.cpg`: OLE compound file, 800-byte header, each
   block an encrypted stream.

## 4. Data flow: writing a codeplug to a radio

Same link/PPP/TCP bring-up, then: `EnterWriteMode` (0x106, mode 4, timeout) →
stream `WriteIshList` / `OP_WRITE_ISH` (0x101) chunks (≤880 B each) → **`OP_LOCK`
(0xD) carrying the 16-byte UUID** to commit RAM→flash and reboot. An empty/wrong
UUID = abort (no commit). **Safety:** every write must target a partition the
schema marks `IsRWPartition` (AccessRights==1); RO(0)/RW-locked(2) hold
calibration + security and must never be written.

## 5. Data flow: loading encryption keys (separate subsystem)

Codeplug defines the encrypted channels + key slots (SLN/CKR) and algorithm.
The actual DES/AES key bytes are loaded separately over the **3-wire keyfill bus**
by a KVL/KFD running P25 Manual Rekey — never through the codeplug/RCMP path.
ADP (40-bit, software) is the only key type the codeplug itself can carry. See
ENCRYPTION_MODEL + KEYLOADER_ROADMAP.

## 6. The clean-room reimplementation (this project)

| CPS component | OpenAstro equivalent |
|---|---|
| RadioSerial10 + RadioCustStack10 (serial + userspace PPP/TCP) | Linux kernel `pppd` + an OS TCP socket |
| ByteData10 + NextGen10 (RCMP) | `cleanroom_flasher/rcmp_socket_transport.py` |
| cgIsh10c / udcIsh10c (schema/model) | `src/open_astro/models/*` + CSV/JSON (field schema still needs a `.cpg` sample) |
| fhAdk10c (.cpg format) | to build: `olefile` reader + RC4(`A8Z6J9QP5`) + CRC-16 (format fully documented) |
| KVL (keyfill) | `kfdtool.py` + `kvl_probe.py` + KFD hardware |

The reimplementation is sound because the CPS stack is just standard PPP/IP/TCP
with an application protocol (RCMP) on top — nothing exotic. The Linux kernel
does the networking; we only need to speak RCMP and the `.cpg` format.
