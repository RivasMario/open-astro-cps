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

## Independent re-confirmation (2026-10-29, Ghidra 12.2 headless, Windows ARM64)

Re-decompiled `FUN_1000fd89` cold from `NextGen10.dll` (resolved via
`tools/re_paths.py nextgen10`) with a fresh Ghidra 12.2 headless pass — no
reference to the notes above. Recovered verbatim:

```
*(undefined4 *)(EBP + -0x14) = 0x51e88d21;                 // init state
*(undefined4 *)(EBP + -0x18) = 0x20;                       // 32-byte block
uVar7 = *pbVar9 >> (iVar4 & 0x1f) & 1 ^ state >> 9 & 1;     // fb = inbit ^ (state>>9)  tap=9
state = uVar7 + state * 2;                                 // state = state*2 + fb
bVar8 = bVar8 ^ (char)uVar7 << (iVar4 & 0x1f);             // out bit ^= fb
```
`MOV dword ptr [EBP + -0x14],0x51e88d21` @ VA `0x1000fdc4`. Every constant
(`0x51E88D21`, tap bit 9, `state*2+fb`, length `0x20`) equals
`src/open_astro/protocol/unlock.py`. Static chain confirmed independent of the
earlier Fedora analysis. Live hardware/real-CPS seed/response vector (open item
#3) remains the only acceptance still pending — see
`docs/FEDORA_CAPTURE_HANDOFF.md`.

## Third re-confirmation + full flash-path map (2026-11-01, Ghidra 12.1.4, Windows x64)

Cold re-analysis of `NextGen10.dll` (SHA256 `99fa3efbf1b7aa58722558841336c68035b9c4d562bf656f8f180d4f60348746`,
245760 bytes, 1814 procedures) plus the transport DLL `RadioCustStack10.dll`
(SHA256 `58539e91beba47780a01db38a95535c16cdd4e7b005b4146011836c8a8a6c0c4`). The LFSR
scrambler `FUN_1000fd89` and the `CRcmpBundler::UnlockSecurity` sequence
(`FUN_1000cce7`: build `+0x60` → `FUN_1000fd89` → send `+0x5c` → commit `+0xb0`,
errors `0x97/0x98/0x99`) both re-recovered verbatim. New findings below.

### Transport layer — NOT RCMP's secret (RadioCustStack10.dll)
Depot's USB "device 13" link is the **US Software "USNET" embedded TCP/IP stack**,
wrapped by Motorola as `RadioCustStack` (version resource: "Motorola", "Copyright
2003-2005"). Serial via `CCommPort` (`I8250` 16550 driver) from `RadioSerial10.dll`.
Link bring-up (`CUSNETppp::PPPConnect@0x1000ee10`): a **plaintext ASCII chat**
(`CUSNETppp::PPPHandshake@0x1000ef60` writes `"CLIENT"`, waits for `"CLIENTSERVER"`;
modem `ATA`/`CONNECT` script strings present) then USNET PPP in a pump thread
(`0x10001420`), async-HDLC framed (device-13 `0x7e` suppressed ~2× = byte-stuffing
active). **Conclusion:** USNET PPP and our Windows-RAS PPP deliver identical RCMP to
the radio at `192.168.128.1:8002`. The transport is interchangeable; flashcode
persistence is an *application-layer* (RCMP opcode) matter, not a link-layer one.
Full notes: `docs/SESSION_LOG_20261101.md` §4.

### RCMP wire framing (CRcmpProtocol)
- `CRcmpProtocol::BundleTCP` (`FUN_100187b6`): RCMP-over-TCP frame = `[len_hi][len_lo][payload]`
  — a 2-byte **big-endian length prefix** (payload shifted right 2, length += 2).
- `CRcmpProtocol::SendRequest` (`FUN_10018123`): request records begin `01 01`;
  a global byte-progress counter advances by `payload[7]<<8 | payload[8]` for `01 01`
  records; payload is sent in ≤ `0x410` (1040)-byte chunks; transport-mode values
  `{4,8,9,10,0xc,0xd}` at `this+0x30` select the `BundleTCP` TCP framing, mode `0xd`
  = OTAP (`SetOtapAbortFlag`).

### Where the static call graph ENDS (the COM boundary)
`FUN_1000b2ad` = `CRcmpBundler::LoadServer`: when `this+0x20 != 1` it
`CoCreateInstance`s three COM objects (CLSIDs at `DAT_10025aa0`/`10025b00`, plus
`10025af0`+riid `10025ad0` when the arg == 3 [OTAP/network transport] else
`10025a90`+`10025a30` [serial]) into `this+0x18/+0x14/+0xc|+0x8`, then sets
`this+0x20 = 1`. **The actual RCMP opcode bytes (`0x0106`/`0x0107`/`0x0101`/`0x0100`)
are built inside those separate RCMP-core COM servers, not inside NextGen10.**
NextGen10 is the orchestration ("Bundler") layer; `UnlockSecurity`'s `+0x60/+0x5c/+0xb0`
are vtable calls into the COM transport object. This is why the wire opcode of the
unlock request (`0x0107` vs the `0x2011` message tag — open item #2) **cannot be
resolved from NextGen10 alone**; it needs either the RCMP-core COM DLL or a live wire capture.

### Flash-write path (how a 0x81 write works)
- Flashcode `0x81:1006`, serial, and model are all **ISH items**; `ReadWriteRadioSerialNumber`
  (`FUN_1000ace8`) writes them through the generic single-instance ISH R/W primitive
  (`FUN_1000b8b5`/`FUN_1000a201`), dispatching local vs remote-proxy on `this+0x80==0xc`.
- `EnterWriteMode` (`FUN_10016776`) is the **OTAP** entry: builds a VT `0x2011` SAFEARRAY
  size `0x410`, sends via `FUN_1000b5b0`, reads reply where `reply[2]`=status
  (`2`="Radio is Not an OTAP Enabled…", `reply[3]==4`="Radio is Busy", else "Radio is
  Not Responding"). Not required for a direct serial `0x81` write.
- A second unlock variant `FUN_100133df` runs the same challenge→LFSR→response, then
  reads back three fields (`FUN_10012a96/d25/d76` → `this+0x2a/0x29/0x28`) — a
  capability/version read gated behind unlock.

### Capture-evidence check (2026-11-01)
No capture on hand contains a decodable `UnlockSecurity`:
- `captures/cps_20261023_*.pcap` (CPS, **device 5** = RCMP-over-RAS-PPP, fully decodable
  by `tools/decode_usb_ppp.py`): OUT/command streams show only `0106`/`0103`/`0100`
  (session + reads). **No `0107` OUT** — these are read-only sessions. (The lone `0107`
  in an IN stream is incidental data inside an ISH descriptor list `11 17 21 27 31 …`.)
- `captures/depot_*.pcap` (Depot, device 13): USNET async-HDLC, undecodable by the
  device-5 parser and missing the chat handshake (capture began after link-up).

### THE remaining gap + how to close it
Crypto = solved (`unlock.py`). Exchange shape = solved (build→seed→scramble→respond→commit).
Unconfirmed = the **wire bytes**: `0x0107` vs `0x2011` on the record header, the request
body, and the seed's byte offset in the reply (`unlock_session.WIRE_PROFILE_CONFIRMED=False`).
To close it, capture **one live CPS session that writes `0x81`** (e.g. change radio
model/serial/flashcode) over **device 5** (CPS, not Depot — decodable), then read the
`0107` request + 32-byte seed reply + response straight out of
`tools/decode_usb_ppp.py` output and drop the constants into `unlock_session.py`.
Do NOT transmit a guessed UnlockSecurity frame to a radio.
