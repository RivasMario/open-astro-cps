# ASTRO 25 Portable CPS R20.01.00 — Full File Inventory & Analysis Status

Every file in the extracted CPS tree, with whether it was analyzed. 205 files,
extracted from `data2.cab` via `unshield`. **`data1.cab` was NOT extracted** this
session (it holds mostly the same installer/support set; re-extract if a file
below is missing). Legend: ✅ analyzed (disassembled/documented) · 🟡 partial
(role/strings/exports only) · ❌ not opened · ⬜ noise (framework/3rd-party/
installer/media — intentionally skipped).

## Radio logic — the files that matter

| File | Status | Notes |
|---|---|---|
| `Virtual_Radio_2000_DLL/NextGen10.dll` | ✅ | RCMP engine (`CRcmpBundler`) — deep. `NEXTGEN10_RCMP_DISASSEMBLY.md` |
| `Virtual_Radio_98_ME_dll/NextGen10.dll` | ✅ | duplicate of the above (OS variant) |
| `Comm-DLLs/ByteData10.dll` | ✅ | `CRawBytes` transport glue + connect choreography |
| `Comm-DLLs-Non-Self-Reg/RadioCustStack10.dll` | ✅ | userspace PPP+IP+TCP stack (`CUSNETppp`/`CUSNETdpi`) |
| `RDK_DLL_s/cgIsh10c.dll` | ✅ | codeplug schema engine; partition access class + CRC-16 |
| `RDK_DLLs_for_Launcher/fhAdk10c.dll` | ✅ | `.cpg` file format + RC4 key. `CPG_FILE_FORMAT.md` |
| `CPS_Application_Files/PatPort.exe` | 🟡 | 24 MB GUI; opcode strings + RC4 key + a few funcs (not fully) |
| `CPS_Application_Files/patphopt_{a,b,c}.mdf` | ✅ | flashcode/model-option tables (Q/H/G codes) |
| `CPS_Application_Files/modup.mdf` | 🟡 | model-update data; opaque, characterized only |
| `Comm-DLLs_Legacy/RemoteProtocols01.dll` | 🟡 | legacy SB9600/SBEP COM server; strings only (Fedora), not deep-disasm |
| `Comm-DLLs-Non-Self-Reg/RadioSerial10.dll` | 🟡 | `CCommPort` raw serial; role known, not opened |
| `Comm-DLLs-Non-Self-Reg/PortManager10.dll` | 🟡 | device enumeration; role known |
| `Comm-DLLs/PatComm10.dll` | 🟡 | `CPortManager::ListDevices`; role known |
| `RDK_DLL_s/udcIsh10c.dll` | 🟡 | schema↔model transform; role from symbols, not disasm'd |
| `RDK_DLL_s/UdcDrIsh10c.dll` | 🟡 | same family |
| `RDK_DLLs_for_Launcher/udcXAdk10c.dll`, `udcDrXAdk10c.dll` | ❌ | export/import variants of the above |
| `RDK_DLLs_for_Launcher/adkGen10c.dll` | ❌ | generic ADK exception/error plumbing |
| `RDK_DLLs_for_Launcher/ruiX50c.dll`, `RDK_DLL_s/{Prn50c,Rdb50c,Rud50c,Rui50c,pip50c}.dll` | ❌ | RDK framework (UI/db/print) — not opened |
| `FLASHport_self-reg/EncatenComponent.dll` | ❌ | **codeplug image assembly (suspected) — worth a look** |
| `Comm-DLLs_Legacy/mcomUnknown.dll`, `Comm-DLLs/Macro.dll` | ❌ | COM plumbing / macro support |
| `Security/SECURITYLIB.dll`, `CPS_Application_Files/Security.exe` | ❌ | **ASK / feature security — worth a look for licensing** |

## NOT opened but potentially interesting (flagged for a future pass)

| File | Why it might matter |
|---|---|
| `NetworkRadioProg_DLLs/authAES.dll`, `RDK_DLL_s/authAES.dll` | AES authentication — .NET, easily decompiled |
| `NetworkRadioProg_DLLs/{INetVR,NetVRClientLib,Interop.NEXTGENLib}.dll` + `.tlb` | the .NET "Network Radio Programmer" / OTAP-over-network path |
| `NetworkRadioProg_DLLs/EncryptionSink.dll`, `ARS_DLLs/{SSLManagerComp,DataStoreDecryptionHandler}.dll` | network/data crypto layer |
| `OtapTimerDll/OtapRWCDTimer.dll`, `CPS_Application_Files/OtapRWCDTimerExe.exe` | OTAP (over-the-air programming) timing |
| `FeatureLevelPassword/CPSFeatures.enc`, `_Support_.../LicenseGenerator.exe` | CPS feature-level unlock / licensing |

## Noise — intentionally skipped (⬜)

Not radio logic; not analyzed and not worth it:

* **MS runtimes:** `mfc42.dll`(×2+Vista), `msvcrt.dll`, `msvcp60.dll`, `Msvcirt.dll`,
  `OLEAUT32.DLL`, `olepro32.dll`(×2), `atl.dll`(×2), `dbghelp.dll`, `RHGBTN32.DLL`,
  `inetwh32.dll`, `Roboex32.dll`.
* **OpenSSL / .NET crypto libs:** `libeay32.dll`, `ssleay32.dll`, `ManagedOpenSsl.dll`.
* **Crystal Reports / .NET report viewer:** `ReportViewer.exe`(×3), `pvdt60.ocx`,
  all 32 `CrystalReport_rpt_Files/*.rpt` (per-model button/info report templates:
  H10D/H18C/H46/H66/H67/H79…).
* **iButton / Dallas 1-Wire (ASK dongle hardware):** `Ib10e32.dll`/`IB10E32.dll`,
  `ibfs32.dll`/`IBFS32.dll`, `IBUSB32.dll`, `ib90usb.dll`, `iBtnEncDec.dll`,
  `iBtnWrapperDLL.dll`, `Ds1410d.sys`, `DS1410D.sys`, `DS2490.sys`, `DS2490.inf`,
  `ds2490winusb_x86.{cat,inf}`, `wdfcoinstaller01007.dll`, `winusbcoinstaller.dll`,
  `wudfupdate_01007.dll`, `VSAuthD.vxd`.
* **Drivers / modem INFs / installers:** `usbser.sys`(×3), all `MotorolaModem*`
  INF/CAT (Win2000/XP/7/8/ME/Vista), `fudally.{sys,cat,inf}` + `fudally_usb.dll` +
  `DPInst.exe`(×6), `WdfCoInstaller01005.dll`, `WinUSBCoInstaller.dll`,
  `difxapi.dll`, `ISBEW64.exe`(×2), `isrt.dll`, `_isres_0x0409.dll`,
  `_isuser_0x0409.dll`, `StringTable_0x0409.ips`, `{DIFxData,FontData,corecomp}.ini`,
  `dotnetinstaller.exe`, `msxml.msi`, `remove_{fudally,p2k}_devices.exe`,
  `NetworkProgrammerDllRegister.exe`, `default.pal`.
* **Help / media / legal:** `PATPORT.chm`, `Security.chm`, `PatPortTips.tip`,
  `Keyhh.exe`, `KeyHelp.ocx`, `TSCC.exe`, `Intro.exe`, `RSS_Launcher.exe`,
  all `FlashPlayer/*` (`Welcome*.swf`, `*.htm`, `swfobject.js`), every `*.txt`
  (License/ReadMe/FCC/OSS legal/Com_Info/Ole_Info), `XTS2500 & XTS5000.lst`,
  `patcfg.cps` (FCC exception list), `*.config`.

## Summary

* **Deeply analyzed (✅): ~8 files** — the entire codeplug protocol + transport +
  file format + schema engine chain. This is the part that matters, and it's done.
* **Role-known (🟡): ~9 files.**
* **Not opened (❌): ~10 files**, of which ~5 are flagged interesting (authAES,
  NetVR/.NET network programmer, OTAP, licensing, EncatenComponent).
* **Noise (⬜): ~170 files** — MS/OpenSSL/Crystal/iButton/installer/driver/media.
* **Not extracted:** `data1.cab` (separate archive; re-run `unshield` if needed).
