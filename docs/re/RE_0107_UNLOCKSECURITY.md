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

## 2026-10-30 — bundler dispatch vtable located; slot mapping DISPROVEN

Found a bundler method table by scanning `.rdata` for the pointer to `FUN_1000cce7`
(`FindBundlerVt.java`): table at **`0x10025cc0`** (UnlockSecurity ptr at `+0xd0`), plus a second
variant at `0x10026020`. Full dump: `docs/re/nextgen10_bundler_vtable.txt`.

**But this table is the OLE-automation/dispatch table, NOT the object `FUN_1000cce7` indexes with
`(*piVar2+0x5c/0x60/0xb0)`.** Decompiling those slots (`docs/re/nextgen10_unlock_slots_decomp.txt`)
disproves the build/send/reply labels:
- `0x10025cc0+0x60` = `FUN_1000c01f` — `CRcmpBundler::Open` dispatcher (not an unlock builder).
- `0x10025cc0+0x5c` = `FUN_1000a610` — a `ReadIshList`-style request routine.
- `0x10025cc0+0xb0` = `FUN_1000f978` — builds a `"Host"` (`48 6f 73 74`) request via vtable `+0x68`.

None is UnlockSecurity's build/send/reply. The `+0x60/+0x5c/+0xb0` offsets in `FUN_1000cce7` apply to
`piVar2`'s *runtime* vtable (the internal `CRcmpProtocol`/COM object), whose true vtable is not this
dispatch table. **Correcting the earlier RE note: `+0x60`≠build, `+0x5c`≠send, `+0xb0`≠reply against
this table.**

**`0x2011` is a generic RCMP message-container tag**, not the unlock discriminator: `FUN_1000a610`
(ReadIshList) and `FUN_1000f978` ("Host") both `operator_new` a message and set its first `u16` to
`0x2011`, exactly like `FUN_1000cce7`. So the real unlock opcode (`0x0107`?) is a *field inside* the
message body, set somewhere not yet located — the "`0x2011` vs `0x0107`" framing is a false dichotomy.

Next static step (uncertain, slow): identify `piVar2`'s actual class + vtable at the unlock call
site and decompile its real `+0x5c/+0x60/+0xb0`, or where the message body's opcode field is written.
Decompiler stack-param/offset inference on these naked `unaff_EBP` thunks is unreliable — a live
unlock capture remains the reliable oracle.

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

## 2026-10-30 (ctd) — seed buffer + scramble arg confirmed; request framing still open

Decompiled `FUN_1000cce7` / `FUN_1000c01f` / `FUN_1000fd89` (Ghidra 12.2 headless, `-noanalysis`,
`DecompUnlock2.java`):

- **`FUN_1000fd89` arg confirmed:** operates on the 32-byte buffer passed at `EBP+8`, in place —
  `new[0x100]` temp, transform, copy `0x20` back. `pbVar9 = arg + 0x1f` (reads `seed[31-i]`), init
  `0x51e88d21`, tap bit 9, inner loop bits 7..1 (bit 0 untouched). **Byte-for-byte = `unlock.py`.**
- **Seed global = `DAT_1002f7e8`:** `FUN_1000c01f` (CRcmpBundler::Open) **mode `0xd`** does
  `memcpy(&DAT_1002f7e8, *(void**)(EBP+0x1c), 0x20)`, then `_DAT_1002f7fe = 0x1f43` and
  `*(u16*)(piVar2+0x92) = DAT_1002f806`. So Open(0xd) = "deliver the 32-byte seed to the engine".
- **`FUN_1000cce7` order:** build(`*piVar2+0x60`) → `Ordinal_23`(lock)/`FUN_1000fd89`(scramble)/
  `Ordinal_24`(unlock) → send(`*piVar2+0x5c`) → reply(`*piVar2+0xb0`). msg container tag `0x2011`
  set at `EBP-0x30`; `*puVar1 = 0` is the out-status init.

**Still NOT byte-confirmed (unchanged blocker):** the on-wire `0x0107` request body and the seed's
offset in the reply. build/send/reply dispatch through `piVar2`'s *runtime* COM vtable, which static
decomp of these `unaff_EBP` thunks cannot resolve to exact bytes. `WIRE_PROFILE_CONFIRMED` stays
False. **Decisive step: one live unlock capture** (now feasible — dockur CPS VM is stable and
bridged to the real XTS 5000 via the relay; tcpdump is armed on the relay bridge, port 8002).
Capture a CPS "program radio" exchange, extract the `0x0107` request + seed offset, add a
seed/response KAT vector, then flip the flag.
