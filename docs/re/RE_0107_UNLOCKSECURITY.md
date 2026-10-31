# RE: RCMP `UnlockSecurity` (opcode `0x0107`) — NextGen10.dll

Clean-room reverse-engineering notes toward documenting the Partition `0x81` `UnlockSecurity`
authentication frame. Target binary resolved via `tools/re_paths.py nextgen10`
(`.../NetworkRadioProgrammer/System32/NextGenNon98/NextGen10.dll`). Analyzed with Ghidra 12.2
headless on Fedora (JDK 25). Raw decompiles: `docs/re/nextgen10_unlocksecurity_decomp.txt`.

## Binary layout
- **NextGen10.dll** — image base `0x10000000`; `.text 0x10001000–0x10012fff`. 571 functions.
  Holds the `CRcmpBundler` / `CRcmpProtocol` C++ engine (MFC). This is the RCMP engine, **not**
  `ByteData10.dll` (base `0x11000000`).
- RTTI/debug string `"CRcmpBundler::UnlockSecurity"` @ `0x1002c9d0`.

## `CRcmpBundler::UnlockSecurity` — `FUN_1000cce7`
Referenced by the method's own `CString` debug-name ctor at `0x1000cd07`. Structure:
- Builds a request message; sets a 16-bit field `*(u16*)(ebp-0x30) = 0x2011`.
- `this` = `piVar2`. Checks byte flag `this[8]`; if `!= 1` calls `FUN_1000b2ad` (pre-step/session).
- Branch on `this[0x20] == 0x0c` (sub-protocol selector); sub-object `this[0xc]` path calls its
  vtable `+0x50`.
- Main path drives the protocol object via **vtable calls**:
  - `(*this + 0x60)(this, &msg, out)` → **bundle/build**; failure sets error `0x97`.
  - `(*this + 0x5c)(this, &msg, out)` → **send**; failure sets error `0x98`.
  - `(*this + 0xb0)(this, arg, out)` → **read reply**; failure sets error `0x99`.
  - Between send and reply: `Ordinal_23/FUN_1000fd89/Ordinal_24` (buffer lock / process / unlock).
- Returns HRESULT in `ebp-0x10`.

So UnlockSecurity = build(`0x60`) → send(`0x5c`) → reply(`0xb0`) on a `CRcmpProtocol` vtable, tagged
message `0x2011`.

## RESOLVED — seed→response transform (`FUN_1000fd89`)

`CRcmpBundler::UnlockSecurity` (`FUN_1000cce7`) build→send→reply sequence, with the RCMP methods
resolved by their debug-name strings:
- `CRcmpProtocol::BundleTCP` = `FUN_100187b6` — just prepends a 2-byte big-endian length (framing).
- `CRcmpProtocol::SendRequest` = `FUN_10018123`, `GetReply` = `FUN_10018030`, `UnpackTCP` = `FUN_10018838`.
- `FUN_1000b2ad` (the `this[8] != 1` pre-step) = `CoCreateInstance`/`LoadServer` COM setup — **not crypto**.
- **`FUN_1000fd89`** (run between send and reply) = **the seed→response scramble**.

`FUN_1000fd89` is a self-synchronising LFSR scrambler over a fixed 32-byte block, with a hard-coded
constant and **no key/secret/asymmetric input** — so it is fully reversible and platform-independent:

```
state = 0x51E88D21                 # hard-coded init in .text
for i in 0..31:                    # output byte i
    val = seed[i]                  # base = forward byte
    in_byte = seed[31 - i]         # keystream driver = reversed byte
    for b in 7..1:                 # bit 0 is NEVER processed -> low bit passes through
        fb    = ((in_byte >> b) & 1) XOR ((state >> 9) & 1)   # tap = bit 9
        state = (state * 2 + fb) & 0xFFFFFFFF                 # input bit fed back
        val  ^= fb << b
    out[i] = val
```

Because the response is computed purely from the radio's seed + the constant, and the radio verifies
with the same algorithm, re-implementing this answers any seed and unlocks Partition `0x81`.

**Implementation:** `src/open_astro/protocol/unlock.py` (`unlock_response(seed: bytes) -> bytes`).
Tests: `tests/test_unlock.py` (golden vectors + structural invariants; **live radio seed/response
pair is the final acceptance, pending**).

## 2026-10-30 — CRcmpBundler vtable + slot functions resolved

The `+0x60 / +0x5c / +0xb0` vtable calls in `FUN_1000cce7` are **`CRcmpBundler`**
slots (`piVar2` = the bundler `this`). The bundler vtable is **not** symbolized; found it by
scanning `.rdata` for the pointer to `FUN_1000cce7` (`FindBundlerVt.java`).

- **CRcmpBundler vtable base = `0x10025cc0`** (ends `0x10025df0`; `UnlockSecurity` is slot `+0xd0`).
  Full dump: `docs/re/nextgen10_bundler_vtable.txt`. (A second table at `0x10026020` is a
  derived/`OTAP` variant with the same methods at shifted offsets.)
- Resolved UnlockSecurity slots (decompiles in `docs/re/nextgen10_unlock_slots_decomp.txt`):
  - `+0x60` **build** = `FUN_1000c01f` — a command dispatcher (`CRcmpBundler::Open` debug name).
    Takes a command selector; `== 0xd` branch does `memcpy(&DAT_1002f7e8, arg, 0x20)` (0x20 = the
    32-byte seed block) and sets `_DAT_1002f7fe = 0x1f43`, writes `piVar2+0x92`; sets the
    sub-protocol selector `piVar2[0x20]`. Calls `FUN_1000d523` on the non-`0xc` path.
  - `+0x5c` **send** = `FUN_1000a610`.
  - `+0xb0` **reply** = `FUN_1000f978`.

So the `0x2011`→wire-record serialization lives in `FUN_1000c01f`/`FUN_1000d523` + the `DAT_1002f7xx`
globals, not in the `CRcmpProtocol` TCP codec (`SendRequest`/`BundleTCP` just chunk and length-prefix
an already-built buffer — see below). **Decompiler stack-param inference is unreliable for these
naked `unaff_EBP` thunks**; the exact request body + seed offset still need either careful tracing of
`FUN_1000c01f`→`FUN_1000d523`+globals, or one live unlock capture.

Confirmed framing facts (do not re-derive):
- `CRcmpProtocol::BundleTCP` (`FUN_100187b6`) prepends a **2-byte big-endian length** — matches
  `rcmp.frame()`.
- `CRcmpProtocol::SendRequest` (`FUN_10018123`) transmits an already-built payload in `0x410`-byte
  chunks; its `*pcVar2=='\x01' && pcVar2[1]=='\x01'` (WRITE) branch reads the length at payload bytes
  7–8 — matches the verified `rcmp.py` WRITE layout (`01 01 <part><obj:2><inst:2><len:2>`).
- Wire opcode `0x0107` is a **strong inference** (fits the verified family `0x0100` read / `0x0101`
  write / `0x0103` prepare / `0x0106` session), **not yet byte-confirmed**. `0x2011` is the internal
  message-object tag, distinct from the wire opcode.

## Still open
1. Recover the exact UnlockSecurity request body + the seed's offset in the reply — trace
   `FUN_1000c01f`→`FUN_1000d523` + `DAT_1002f7xx`, or capture one live unlock exchange.
2. Fill the constants in `src/open_astro/protocol/unlock_session.py`, set
   `WIRE_PROFILE_CONFIRMED = True`.
3. Record a hardware seed/response pair as the acceptance test vector.

## False leads (recorded so we don't repeat)
- A naive `01 07` byte search hit incidental immediates. `FUN_10008b95/_c10/_c8f/_d09/_d83` are
  **codeplug record-stream parsers** (walk `[u16 part][u16 obj][u16][u16 len]`, step `len+8`), e.g.
  scan partition `0x80`/object `0x0ff1`, object `0x000a`. Not the unlock opcode.

## Pipeline (repeatable on Fedora)
```
JAVA_HOME=~/tools/jdk-25.0.5+8 \
~/tools/ghidra_12.2_PUBLIC/support/analyzeHeadless ~/re/ghidra_projects ng \
  -import "$(python tools/re_paths.py nextgen10)" -overwrite \
  -scriptPath ~/re/ghidra_scripts -postScript DecompTargets.java
```
NOTE: full Ghidra analysis of the 24M `PatPort.exe` **hangs** in MSVC RTTI/type analysis on this
laptop; the small engine DLLs (`NextGen10.dll` 240K, `ByteData10.dll` 132K) analyze in seconds and
are the right targets anyway.
