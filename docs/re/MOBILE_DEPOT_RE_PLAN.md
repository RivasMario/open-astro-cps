# ASTRO 25 Mobile Depot (`R15.00.00`) — Decompilation & Schema Extraction Plan

> **Source:** `G:\My Drive\RADIO\ASTRO25SOFTWARE\ASTRO_25_MOBILE_DEPOT_R15.00.00.zip` (147 MB)
> **Target Radios:** Motorola **XTL 1500**, **XTL 2500**, **XTL 5000**, **PM 1500** (`0cad:1003`, `1010`, `1011`, `1014`, `1015`)
> **Pipeline:** Ghidra 12.2 headless (`ExportSecAuth.java`) $\rightarrow$ CRT filter $\rightarrow$ TrueNAS Ollama `qwen2.5-coder:14b` (`num_ctx=8192`).

---

## 1. Already Proven Shared with Portable (`SHA-256` Verified)

No need to re-analyze these core binaries — they are **byte-identical** to Portable CPS/Depot `R20.01.00`:

| Binary | Size | Role |
|---|---|---|
| `fhAdk10c.dll` | 90,112 B | `.cpg` RC4 (`A8Z6J9QP5`) container & object directory |
| `UdcDrIsh10c.dll` | 86,016 B | Codeplug image $\rightarrow$ `IVirtualRadio::WriteCodeplug` |
| `udcIsh10c.dll` | 245,760 B | UDC ISH engine |
| `Security.exe` | 53,248 B | Security UI wrapper |

---

## 2. Phased Mobile RE & Schema Plan

### Phase M1 — Mobile MDF & FLASHcode Option Tables *(Python, no Ghidra needed)*
- **Files:** `patmhopt_a.mdf` (59,145 B), `patmhopt_b.mdf` (35,672 B), `modup.mdf` (4,038 B)
- **Goal:** Parse Mobile **`G*`** FLASHcode option codes (e.g., `G857`, `G806`, `G51`, `G996`), model numbers (`M20*`, `M21*`, `M30*`), and bandsplits into `schema/mobile_flashcode_options.json`.

### Phase M2 — Mobile Core & Schema Diffs *(Ghidra + `qwen2.5-coder:14b`)*
- **`adkGen10c.dll` (24,576 B):** ADK generation helper (not in Portable `R20` `.cab`s).
- **`udcXAdk10c.dll` (32,768 B):** XML/ADK codeplug bridge (compare against Portable `udcDrXAdk10c.dll`).
- **`cgIsh10c.dll` (204,800 B, `R15`):** Diff/check for any Mobile-specific ISH block types, control-head objects, or `AccessRights` differences vs `R20`.
- **`SECURITYLIB.dll` (45,056 B, `R15`):** Quick export/string diff vs `R20`.

### Phase M3 — Mobile R15 RDK, Database & UI Layers *(Targeted Ghidra + String/Symbol Scan)*
- **`Rdb50c.dll` (180 KB) & `Rud50c.dll` (647 KB):** Radio Database & Radio User Data layers — check for Mobile-only control-head (`M5`/`O5`/`MX`/`W3`/`W4`/`W5`/`W7`/`W9`), siren/DEK, dual-radio, or VRS objects.
- **`pip50c.dll` (212 KB), `Rui50c.dll` (544 KB), `ruiX50c.dll` (45 KB), `Prn50c.dll` (192 KB):** UI/Import/Export/Print layers.
- **`scpw32.dll` (163 KB), `scpw32a.dll` (69 KB), `SysKeyAdmin.exe` (1.2 MB), `RSS_Launcher.exe` (126 KB):** Password/ASK/launcher utilities.
- **`PatMobDepot.exe` (29.3 MB):** Targeted string & ISH block-ID extraction (avoid full MFC UI decompilation).

### Phase M4 — Integration into OpenAstro (`Python` + `Rust`)
- Add Mobile `G*` option decoding & XTL/PM model detection to `flashcode` (`Python` + `rust/open_astro_cli/src/flashcode.rs`).
- Add Mobile-specific ISH block layouts (control heads, siren/PA, mobile power levels) to `schema/field_layouts.json`.
