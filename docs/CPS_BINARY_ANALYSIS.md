# CPS Binary Analysis: What the Real Software Actually Contains

Static analysis of the real ASTRO 25 Portable CPS R20.01.00 installer
(`~/GoogleDrive/RADIO/ASTRO25SOFTWARE/astro25portablecpsr20.01.00/`). No radio was
contacted to produce this document — everything here comes from extracting and
reading Motorola's own binaries.

**Date:** 2026-10-20. **Tools used:** `unshield` 1.6.2 (built locally from source,
no sudo — see below), `pefile`, `objdump`, `strings`, `file`.

This document **supersedes** the protocol claims in
`astro_cps_reverse_engineering_guide.md`,
`deep_dive_radio_port_and_cpg_relational_database.md`,
`cps_subsystems_reference_notes.md`, and
`motorola_astro_cps_architecture_and_design_paper.md` wherever they conflict with
what is recorded here. Those documents described a plausible-sounding protocol;
this one describes the actual DLLs.

---

## 0. Getting in: no sudo needed

`7z`/`cabextract` cannot open InstallShield cabinets (confirmed:
`cabextract -t data1.cab` → *"found InstallShield header. Use unshield"*).
`unshield` is in Fedora's repos but wasn't installed and sudo wasn't available
in-session, so it was built from source entirely in user space:

```bash
pip install --user cmake              # cmake landed in ~/.local, no sudo
git clone --depth 1 https://github.com/twogood/unshield.git
cd unshield && mkdir build && cd build
~/.local/bin/cmake -DCMAKE_INSTALL_PREFIX="$HOME/.local" -DCMAKE_BUILD_TYPE=Release ..
make -j"$(nproc)" unshield             # links against system zlib + openssl
./src/unshield -d <outdir> x data1.cab
./src/unshield -d <outdir> x data2.cab
```
205 files extracted from `data1.cab` + the rest from `data2.cab` = the full
installed CPS tree.

---

## 1. The naming in the previous docs was invented, not reverse-engineered

The real executable is **`PatPort.exe`** (24 MB, `CPS_Application_Files/`), not
`A25CPS.exe`. There is no `A25Tuner.exe`, no `A25Core.dll`, `A25DB.dll`,
`A25Comm.dll`, `A25Val.dll`, `A25Model.dll`, `A25RDef.dll`, `A25Sec.dll`, or
`A25Res.dll` anywhere in the installer. Those eight names, and the "what each one
does" paragraphs describing them, do not correspond to anything shipped.

The real DLL topology, read directly from `PatPort.exe`'s PE import table
(`objdump -p`) and the installer's own folder names:

```
PatPort.exe  (main GUI, internal product name "RDK" — see RDK_DLL_s/RSS_Launcher.exe)
├── Comm-DLLs-Non-Self-Reg/RadioSerial10.dll    — CCommPort: raw Win32 COM-port wrapper
│                                                  (Open/Close/Read/Write/SetSpeed/
│                                                  CommPortSetDCB/CommResolveBaudRate).
│                                                  Generic serial I/O, nothing radio-specific.
├── Comm-DLLs/PatComm10.dll                     — CPortManager::ListDevices (thin wrapper)
├── Comm-DLLs-Non-Self-Reg/PortManager10.dll    — CPortManager: EnumerateDevices,
│                                                  GetDeviceInfo, GetNTCommPort,
│                                                  GetRadioInfo. Device identification layer.
├── Comm-DLLs_Legacy/RemoteProtocols01.dll      — THE ACTUAL WIRE PROTOCOL. See §2.
├── Comm-DLLs-Non-Self-Reg/RadioCustStack10.dll — CBSDsocket / CUSNETdpi / CUSNETppp
│                                                  (PPPConnect/PPPDisconnect/
│                                                  PPPGetRemoteIPaddr). A real PPP-over-radio
│                                                  stack — the "radio as network card" claim
│                                                  in the old docs has a genuine basis here.
├── Comm-DLLs/ByteData10.dll                    — more of the same socket/PPP primitives
├── RDK_DLL_s/cgIsh10c.dll                       — codeplug SCHEMA engine. See §3.
├── RDK_DLLs_for_Launcher/fhAdk10c.dll           — FILE format / encrypt / checksum. See §4.
├── RDK_DLL_s/udcIsh10c.dll, UdcDrIsh10c.dll      — import/export between the schema (cgIsh)
│                                                  and the application's in-memory DB/doc model
│                                                  (CudcIshDoc, CudcIshDbToImage,
│                                                  CudcIshDbCgXchg). The "normalize channels
│                                                  into relational tables" machinery — real,
│                                                  but not Jet/Access (see §3).
├── RDK_DLLs_for_Launcher/adkGen10c.dll          — generic exception/error plumbing (CAdkGenException)
├── iButtonWrapper/iBtnEncDec.dll, iBtnWrapperDLL.dll — Dallas 1-Wire iButton wrapper.
│                                                  Confirms the ASK dongle story has a basis.
└── Security/SECURITYLIB.dll, RDK_DLL_s/Security.exe, RDK_DLL_s/ruiX50c.dll, Rdb50c.dll,
    Rud50c.dll, Rui50c.dll, Prn50c.dll, pip50c.dll  — further RDK framework pieces
    (UI, printing, "database") not yet inspected in depth.
```

None of this is from documentation or memory — it is the literal `DLL Name:`
entries from `objdump -p PatPort.exe`'s import directory, cross-referenced against
`file` and `strings` on each DLL in turn.

---

## 2. The real transport: a COM interface called `IRemoteProtocol`

`Comm-DLLs_Legacy/RemoteProtocols01.dll` is a self-registering in-process COM
server (`DllRegisterServer`/`DllGetClassObject` exported; no other symbols
exported by name — all dispatch is through COM vtables). Its registry script
(readable directly as strings in the `REGISTRY` PE resource) shows three
coclasses:

| ProgID | CLSID | Friendly name |
|---|---|---|
| `RemoteProtocols.RemSB9600` | `{BB885C92-9093-11D3-A0A4-00108302D33D}` | "RemSB9600 Class" |
| `RemoteProtocols.RemSBEP`   | `{BB885C89-9093-11D3-A0A4-00108302D33D}` | "RemSBEP Class" |
| `RemoteProtocols.RemESBEP`  | `{BB885C95-9093-11D3-A0A4-00108302D33D}` | "RemESBEP Class" |

So **SB9600 is real** — it's a genuine protocol family name used by Motorola, not
an invention of the earlier docs. But there are *three* variants (SB9600, SBEP,
ESBEP — full expansions not yet confirmed; likely different radio generations or
link speeds), and the previous docs only ever described one, as if it were the
whole story.

The DLL carries an embedded COM type library (`RT_TYPELIB` resource, MSFT binary
format, extracted with `pefile` — 4016 bytes). Its name strings give the
`IRemoteProtocol` interface's methods, in this order (read directly off the
`"method ..."` entries in the typelib's name table):

```
GetPortNames
GetConfiguration
GetConfigurationValues
SetQueues
SetConfiguration
Close
Open
Read
Broadcast
Request
GetTimers
SetTimers
Send
Receive
```

Parameter names recovered from the same table: `Open(lpszDeviceName, dwFlags)`,
`Send(opcodeName, ...)`, `Read(irRxPacket)`, `Broadcast(lpInPacket)`,
`Request(jrTxPacket)`, `GetTimers(pTimers)` / `SetTimers(timers)`,
`SetQueues(NRxQueueSize, TxQueueSize)`,
`GetConfigurationValues(lpszProperty, lpszConfig)`.

**The load-bearing detail: `Send` takes `opcodeName` — a name, not a number.**
The previous docs' entire opcode table (`0x00` PING, `0x10` ENTER_PROGRAMMING,
`0x14` GET_RADIO_INFO, `0x20` READ_MEMORY, `0x30` WRITE_MEMORY, `0x32` COMMIT, …)
presents itself as captured wire bytes. There is no evidence for any of it in this
DLL. What *is* directly visible, as literal ASCII strings inside `PatPort.exe`
itself, are two real opcode **names**:

```
EPREQ        (almost certainly "Enter Programming REQuest")
TSTMODREQ    (almost certainly "Test Mode REQuest")
```

The actual byte value `Send("EPREQ", ...)` puts on the wire is not in
`RemoteProtocols01.dll`'s strings or in the two `.mdf` data files shipped next to
`PatPort.exe` (`modup.mdf`, `patphopt_{a,b,c}.mdf` — checked with `grep -a` for
`EPREQ`/`TSTMODREQ`, no hits). It is compiled into the DLL as a lookup table this
analysis has not yet located, or it lives in a resource/config file not yet
identified. **The numeric opcode table remains unknown.**

### What the disassembly directly refutes

`objdump -d` over all 17,855 lines of `RemoteProtocols01.dll`'s code:
* **Zero** `cmp`/`cmpb` instructions comparing anything to the immediate `0x05`
  (the claimed SB9600 `START_BYTE`), anywhere in the module.
* 15 `neg %eax`/`neg %ecx` instructions exist (the signature of a two's-complement
  calculation) — but see §4: the two real checksum functions found in this
  installer are in *different* DLLs, operate on different word sizes, and one of
  them is for the file-save format, not the wire protocol. There is no function in
  this DLL confirmed to be "the SB9600 checksum."

This is a negative result, not a gap: the earlier docs described `0x05` as the
single most load-bearing byte in the whole protocol, framing every packet. Its
total absence from the one DLL that implements the SB9600 COM class is strong
evidence the claim was fabricated rather than reverse-engineered.

---

## 3. The real codeplug model: a named schema engine, not a Jet database

`RDK_DLL_s/cgIsh10c.dll` ("cg" = CodePlug, "Ish" — expansion not yet confirmed)
implements the actual structural model, via these classes (names are literal
demangled C++ symbols imported by `PatPort.exe`):

* `CcgIshCpLayout` — the whole codeplug's layout. Methods: `AddBlkLayout`,
  `AddPartition(partitionNum, accessRights)`, `DoesBlkExist`, `GetBlkLayout`,
  `GetBlkLayoutMap`, `HasUniqueIshName`, `DoPostLayoutVerification`.
* `CcgIshBlkLayout` — one named block. Carries `GetIshID`, `GetIshType`,
  `GetPartitionNum`/`SetPartitionNum`, `SetAccessRights`, `GetNumCfgBytes`,
  `GetMaxDataSzInBytes`, `IsILSBlk`, `IsMultiInstanceBlk`.
* `CcgIshDataLayout` — a block's fields. `AddField`, `GetIDOfLastFieldInLayout`.
* Typed field classes: `CcgIshNumFieldLayout`, `CcgIshStrFieldLayout`,
  `CcgIshCharFieldLayout`, `CcgIshNameFieldLayout`, `CcgIshUnionFieldLayout`,
  `CcgIshListFieldLayout` — numeric, string, char, name, union (tagged variant),
  and list fields.
* The unpacked/runtime side: `CcgIshUp`, `CcgIshUpStdBlk`, `CcgIshUpField`,
  `CcgIshUpEntry`, `CcgIshUpEntryList` — turning a raw block's bytes into typed
  field values and back.
* `cgIshCalculateChecksum(const CByteArray&, WORD&)` — a **16-bit** checksum over
  a byte array. (Contrast with §4.)

This is a genuine relational-ish model — named blocks, each with an access-rights
level and a "partition number," each holding typed fields, with scan-list-style
cross-block references handled by `udcIsh10c.dll`'s `CudcIshDbCgXchg` /
`UdcIshXchgList` / `UdcIshXchgUnion` classes (list and union transforms between
blocks — plausibly the mechanism behind "a scan list is edited once and every
channel pointing to it updates," which the old docs attributed to Jet/SQL
relational integrity).

**No evidence of Microsoft Jet, DAO, or ODBC** was found anywhere in `PatPort.exe`'s
import table (full list is in §1 — `ADVAPI32`, `COMCTL32`, `GDI32`, `KERNEL32`,
`MFC42`, `MSVCIRT`, `MSVCRT`, `ole32`, `OLEAUT32`, `SHELL32`, `USER32`, `VERSION`,
`WS2_32`, plus the RDK/Comm DLLs above — no `msjet*.dll`, `dao*.dll`, `odbc32.dll`).
The previous docs' claim that `.cpg` is "an OLE Compound File Binary with an
embedded Microsoft Jet/Access database inside it" has no support in this binary.
It may still be true of the on-disk file format (not checked — no sample `.cpg`
was available this session; see §4 for what *is* confirmed about the save path),
but the *in-memory* model driving the GUI is `cgIsh10c.dll`'s own schema engine,
not Jet SQL.

---

## 4. The real file-save path: `fhAdk10c.dll`

`RDK_DLLs_for_Launcher/fhAdk10c.dll` ("fh" = File Handler) implements:

* `CFhAdkFileHeader` — constructed with an `AdkType` (from `AdkCommonEnums`), a
  `_GUID`, two `CString`s, and an `EncryptType` (from `AdkMotFhHeader`).
* `CFhAdkFileHandler::SaveImage(modelType, header, byteArray, ...)` — writes a
  file.
* `CFhAdkEncrypt::Encrypt(const CByteArray&, CByteArray&)` /
  `::Decrypt(...)` — generic byte-array encrypt/decrypt, pluggable via
  `GetRuntimeClass` (MFC runtime-class dispatch, so there may be more than one
  concrete encryption implementation registered under this interface).
* `fhAdkCalcChecksum(const CByteArray&)` returning a **single BYTE** (the mangled
  return type `E` = `unsigned char`).

So there are **two different checksum functions** in this installer:
`cgIshCalculateChecksum` → 16-bit `WORD`, over schema blocks; `fhAdkCalcChecksum`
→ 8-bit `BYTE`, over whatever `SaveImage` is writing to disk. The earlier docs
described one single 8-bit two's-complement checksum and applied it to the wire
protocol. At best that story could map onto `fhAdkCalcChecksum`'s file layer; it
does not describe `cgIsh`'s 16-bit checksum, and nothing here confirms either one
is used framing SB9600 packets on the wire (§2).

`AdkMotFhHeader::EncryptType` strongly suggests saved codeplug files
(`Codeplug.cpg`, per strings found directly in `PatPort.exe`) are a custom
Motorola header + encrypted payload, not a plain OLE Compound File. Not yet
confirmed by hex-dumping an actual `.cpg` — no sample exists in this repo or in
the Google Drive folder checked this session.

---

## 5. What this means for `open-astro-cps`

1. **Done (2026-10-20):** `src/open_astro/protocol/` was refactored to speak in
   the real shape -- `commands.py` now defines named commands (the two
   confirmed real names, `ENTER_PROGRAMMING`/"EPREQ" and `TEST_MODE`, plus a
   `DeviceAddress` four-tuple matching the real `Send()`/`Receive()`
   signature), and `serial_link.py`/`flasher.py` call by name instead of by
   invented numeric opcode. `framing.py`'s actual byte encoding is still the
   same unverified placeholder as before (name -> small-int -> `0x05`-framed
   packet) -- that part still has zero basis and is still gated behind
   `allow_unverified_protocol` everywhere. What changed is the *shape* of the
   API, so that swapping in the real wire encoding later (once captured) is a
   change to one lookup table in `framing.py`, not a redesign of
   `serial_link.py`/`flasher.py`'s call sites.
2. **The single highest-value remaining unknown is the opcode-name → byte-value
   table**, plus the actual packet byte layout `Send()`/`Receive()` produce on the
   wire. Two paths to it, in order of reliability:
   * Deeper disassembly of `RemoteProtocols01.dll`'s compiled `Send`/`Receive`
     vtable methods (hard without the vtable's vtable-offset-to-symbol mapping;
     COM method bodies aren't exported by name). A disassembler with better
     structure recovery (Ghidra, IDA) would get much further than `objdump -d`
     plus `grep` did here.
   * A live USB capture (`usbmon`) of `PatPort.exe` (under Wine, or on real
     Windows) actually opening `/dev/ttyACM0` and calling `EPREQ`. This sees the
     real bytes regardless of how the code producing them is structured. See
     `docs/HARDWARE_GROUND_TRUTH.md` for the verified transport details a capture
     would ride on top of (USB CDC-ACM, bulk transfer, no real UART).
3. **The safety story needs re-deriving from scratch.** `CcgIshBlkLayout`'s
   `PartitionNum` + `AccessRights` is a real access-control mechanism, but nothing
   found so far maps a specific partition number to "the tuning/calibration data."
   The `0x0020_0000`/`0x0000_4000` addresses in the old docs have no support here
   either — they may be entirely fictional, or they may be real ColdFire physical
   addresses that this application-layer schema never needs to mention because it
   talks to the radio in terms of named blocks, not raw addresses. Until a capture
   or deeper disassembly turns up the real boundary, `flasher.py`'s
   `allow_unverified_protocol` gate (see `PROTOCOL_STATUS.md`) stays in place for
   exactly this reason.

---

## 6. Update 2026-10-20 (same day): exact `IRemoteProtocol` signatures, and why live calls still don't work

Follow-up session. Built a native typelib introspector and a native COM
driver (both compiled with `ziglang` — `pip install ziglang`, no sudo, full
`x86-windows-gnu` cross-compiler) instead of relying on VBScript's loose
automation binding. Source for both is in `tools/wine_harness/`
(`tlbdump.c`, `sb9600_live.c`).

### 6.1 Exact method signatures (via Wine's real `oleaut32`, not guesswork)

`tlbdump.c` calls `LoadTypeLib` + `ITypeInfo::GetFuncDesc`/`GetNames` — the
real Microsoft/Wine typelib parser, not a hand-rolled one — against the
embedded typelib. This is authoritative, not inferred:

```
GetPortNames()                                                      -> VARIANT
GetConfiguration()                                                   -> VARIANT
GetConfigurationValues(lpszProperty: BSTR)                           -> VARIANT
SetQueues(RxQueueSize: I4, TxQueueSize: I4)                          -> void
SetConfiguration(lpszParams: VARIANT)                                -> void
Close()                                                               -> void
Open(lpszDeviceName: BSTR, dwFlags: I4)                              -> void
Read()                                                                -> VARIANT
Broadcast(lpInPacket: VARIANT)                                       -> void
Request(rTxPacket: VARIANT)                                          -> VARIANT
GetTimers()                                                           -> VARIANT
SetTimers(timers: VARIANT)                                           -> void
Send(opcodeName: BSTR, tPacket: VARIANT,
     lAddress: I4, lDeviceMajor: I4, lDeviceMinor: I4, lGroup: I4)   -> void
Receive(opcodeName: OUT BSTR*, lAddress: OUT I4*, lDeviceMajor: OUT I4*,
        lDeviceMinor: OUT I4*, lGroup: OUT I4*)                      -> VARIANT
```

This directly explains why the earlier VBScript probes failed: `GetTimers()`
and `GetPortNames()` take **zero** arguments (the earlier scripts passed one),
and `Open()` returns `VT_VOID` (the earlier scripts tried to capture a return
value from it). Those were script bugs, not findings about the radio.

`Send`'s signature confirms, precisely: the opcode is a name (`BSTR`), the
payload is a `VARIANT` (so presumably a `VT_ARRAY|VT_UI1` byte array in
practice), and every call is addressed to a device by the same four-integer
tuple (`lAddress`, `lDeviceMajor`, `lDeviceMinor`, `lGroup`) that
`PortManager10.dll`'s `DeviceList` struct uses to enumerate devices (§1).
`Receive` returns the same tuple identifying who sent what was received.
This is a real, coherent, cross-confirmed piece of the architecture — not
present anywhere in the earlier (fabricated) docs.

### 6.2 Getting a live call to actually run: three real bugs fixed, one real wall hit

Driving the real `RemoteProtocols01.dll` (`RemSB9600` COM class,
`{BB885C92-9093-11D3-A0A4-00108302D33D}`) under Wine surfaced a chain of
genuine environment problems, each with a concrete fix:

1. **32-bit DLL into a 64-bit host.** This Wine build's default `cscript.exe`
   and a plain `-target x86_64-windows-gnu` build are 64-bit; the DLL is
   32-bit. Loading it into a 64-bit process doesn't fail cleanly — it
   produces confusing downstream errors (COM 429, then `E_ACCESSDENIED`)
   that look like registration problems but aren't. Fix: use
   `C:\windows\syswow64\cscript.exe` for scripts, and compile native tools
   with `-target x86-windows-gnu` (32-bit).
2. **`sed`-in-`sed` backslash collapse.** Generating the `.reg` file's
   `InprocServer32` path by escaping backslashes once, then feeding that into
   a second `sed` substitution, silently undoes the escaping — `sed`'s own
   replacement-string syntax treats `\\` specially. Symptom: the registered
   path had no backslashes left at all. Fix: do the substitution in Python,
   not nested shell tools.
3. **Wine's loader does not search a dependent DLL's own directory** (same as
   modern Windows' default/safe search order) — only the loading
   executable's directory and `system32`/`syswow64`. `PatComm10.dll` (which
   imports `PortManager10.dll`) failed to load with `STATUS_INVALID_IMAGE_FORMAT`
   (0xc0000135, "not found") even sitting right next to its dependency in a
   scratch directory. Fix: copy every extracted DLL into
   `~/.wine/drive_c/windows/syswow64/` (32-bit DLLs need the 32-bit system
   directory in a WoW64 prefix, not `system32`).
4. **The real wall:** even with every self-registering DLL in the installer
   (`RemoteProtocols01`, `mcomUnknown`, `ByteData10`, `PatComm10`, `NextGen10`,
   `Macro`, `iBtnWrapperDLL`, `iBtnEncDec`, `EncatenComponent` — checked by
   grepping every DLL in the installer for `DllRegisterServer` as an export)
   registered cleanly via `regsvr32`, calling `Open()` or `GetPortNames()`
   still fails with `DISP_E_EXCEPTION`, `scode=0x80040154`
   (`REGDB_E_CLASSNOTREG`) for CLSID `{CD8D04DD-E675-11D0-8013-0060B03C8AFF}`.
   That GUID's packed binary form (not readable as text — it's constructed at
   runtime via `StringFromCLSID`, not a static resource string) appears
   inside `ByteData10.dll`, `RemoteProtocols01.dll`, and `mcomUnknown.dll` —
   but all three only *reference* it (call `CoCreateInstance`/
   `CoGetClassObject` with it), none of them *register* it. It is not
   registered by any `DllRegisterServer` in this installer. It is most likely
   written by the real InstallShield engine's own script-driven registry
   merge (a `.reg`/`.ini` step, separate from per-DLL self-registration),
   which was never run — this session extracted files with `unshield` and
   registered individual DLLs by hand, deliberately skipping the installer
   GUI/engine.

### 6.3 What this means going forward

* The method signatures in §6.1 are solid ground truth and don't depend on
  resolving §6.2's wall — they came from Wine's real typelib parser reading
  the DLL's own embedded type library.
* Getting a live call to actually complete needs either: (a) running the
  real InstallShield installer properly (interactively, with a display, not
  the silent flags tried earlier which did nothing) so its own registry
  script runs in full, or (b) finding and hand-registering whatever CLSID
  `{CD8D04DD-...}` is by tracking down its owner more directly — e.g. a
  registry `.reg`/`.ini` file bundled in `data1.cab`/`data2.cab` that this
  session's extraction may have passed over as "support files" rather than
  inspected (worth a targeted `grep` for that GUID's text form, since a
  static `.reg` file — unlike the DLLs — stores GUIDs as plain ASCII, not
  packed binary).
* Reusable tools from this session: `tools/wine_harness/tlbdump.c` (dumps any
  DLL's embedded typelib with exact types via Wine's own `oleaut32` — useful
  for `PortManager10.dll`'s plain exports too, if it ever gets its own
  typelib, or for any other RDK DLL), `tools/wine_harness/sb9600_live.c` (the
  native `IDispatch::Invoke` driver, parameterized by COM port and phase).
  Both compile with `python3 -m ziglang cc -target x86-windows-gnu <file>.c
  -lole32 -loleaut32 -o <file>.exe` — no sudo, no system mingw package.
