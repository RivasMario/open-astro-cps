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

## Still open
1. Wire the live exchange into the write/session layer: send `UnlockSecurity` request (msg tag
   `0x2011`) → read the 32-byte seed → `unlock_response()` → send response → confirm `0x81` unlocked.
2. Confirm message tag `0x2011` ↔ wire opcode `0x0107` mapping against a live capture.
3. Record a hardware seed/response pair and add it as the acceptance test vector.

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
