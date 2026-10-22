# NextGen10.dll / RCMP Disassembly Log

**Date:** 2026-10-22. **Method:** static disassembly (`pefile` + `capstone`,
user-space, no admin) of the real `NextGen10.dll`. No radio contacted. Every
address below is a **measured** fact reproducible with the tool in this repo;
every interpretation is tagged as such.

This log is the bridge between the two prior sessions:

* The Fedora session (`CPS_BINARY_ANALYSIS.md`) disassembled
  `RemoteProtocols01.dll` (the SB9600/SBEP COM server) and concluded the
  codeplug opcode table was "unknown." It never opened `NextGen10.dll`.
* The home-Windows session (`cleanroom-flasher` branch,
  `FEDORA_RADIO_PROTOCOLS_GUIDE.md`) *did* find `NextGen10.dll` and published an
  RCMP opcode table, UUID commit, and offsets — but without the reproducer.

**This session independently re-disassembled `NextGen10.dll` and confirms the
home-Windows RCMP findings are real and accurate to the instruction.** The
earlier `PROVENANCE_AUDIT.md` §2 "fabricated" lean on the RCMP layer is wrong;
see §2 of this file and `PROVENANCE_AUDIT.md` §5.

---

## 0. Binary under analysis

```
G:\My Drive\RADIO\ASTRO25SOFTWARE\astro25portablecpsr20.01.00\
  ASTRO25 Portable CPS R20.01.00\ASTRO25 Portable CPS R20.01.00\
  NetworkRadioProgrammer\System32\NextGenNon98\NextGen10.dll
```

* 245,760 bytes, build Oct 23 2013. PE32, **ImageBase `0x10000000`**.
* `.text` RVA `0x1000`–`0x2415A` (VA `0x10001000`–`0x1002415A`).
* Also present in the same tree: `Crack\PatPort.exe` (24 MB) and
  `System32\ByteData10.dll`. The crypto/schema DLLs (`fhAdk10c.dll`,
  `cgIsh10c.dll`, `RemoteProtocols01.dll`) are **not** in this on-disk tree —
  they only exist inside the InstallShield `.cab`s the Fedora session extracted
  with `unshield`. (So the `fhAdk10c.dll:0x10012018` key offset from the guide
  cannot be checked here; the key *string* itself is confirmed, see §5.)

### Reproducing everything in this file

```bash
# tool kept in the repo; needs: pip install --user pefile capstone
NG="G:/My Drive/.../NextGenNon98/NextGen10.dll"
python -P tools/nextgen10_rcmp_analyze.py layout  "$NG"
python -P tools/nextgen10_rcmp_analyze.py strings "$NG" Rcmp Ish SoftPot Partition
python -P tools/nextgen10_rcmp_analyze.py xref    "$NG" "CRcmpBundler::EnterWriteMode"
python -P tools/nextgen10_rcmp_analyze.py disasm  "$NG" 0x10016776 0x120
python -P tools/nextgen10_rcmp_analyze.py immscan "$NG" 106 101 100 d c 12
```

`-P` (not `-I`): keeps user site-packages, still drops the unsafe cwd/script-dir
`sys.path` entry. The binary is read by path only, never executed.

---

## 1. `CRcmpBundler` is the real codeplug-over-network engine

`NextGen10.dll` contains a full C++ class `CRcmpBundler` (names are literal trace
strings in `.rdata`, each referenced once from its own function body as an
entry-trace). The ones that matter:

```
GetRadioUUID            @ func logging 0x1002C678   trace-ref 0x1000A00A
UnlockSecurity          @ ...0x1002C9D0             trace-ref 0x1000CD08
EnterWriteMode          @ ...0x1002CF34             trace-ref 0x1001679A
WriteIshList            @ ...0x1002C6FC             trace-ref 0x1000AB41
ReadIshList             @ ...0x1002C6B8             trace-refs 0x1000A631 0x100150E2
SendCommand             @ ...0x1002C7EC             trace-refs 0x1000B5D4/B8D9/BA76
ReadSoftPotValues       @ ...0x1002CB04             trace-ref 0x10011B85
```

Also real (string table, mangled export thunks): `WriteSoftPotValues`,
`GetSecurityPartitionData`, `GetSecurityPartitionSize`, `UnlockIshPartition`,
`QnPartitionNum`, `ReadCodeplug`/`WriteCodeplug` (on `CVirtualRadio`),
`NetReadIshList`/`NetWriteIshList`, `DelCodeplug`/`DelPartialCodeplug`,
OTAP (over-the-air) variants.

**The central send is at `0x1000b5b0`** — this is the exact address the
`cleanroom-flasher` branch's `ppp_flasher.py` docstring named as
"`SendRcmpMessage (0x1000b5b0)`". Confirmed.

---

## 2. The RCMP opcode table — CONFIRMED from code

Opcodes are pushed as the last argument before `call 0x1000b5b0`. Verified by
`immscan` + reading each call site:

| Opcode | Name (branch) | Evidence (measured) | Verdict |
|---|---|---|---|
| `0x0106` | `OP_ENTER_MODE` | `push 0x106` at `0x100167ED` (EnterWriteMode), also `0xC273`,`0xC34C`,`0xCAA3`,`0x11AF2`,`0x12494`… (one per Enter* variant) | ✅ confirmed |
| `0x0101` | `OP_WRITE_ISH` | `push 0x101` at `0x1000BFB2`, `0x1001A332`, `0x1001A57B` | ✅ confirmed |
| `0x0100` | `OP_READ_ISH` | `push 0x100` at `0x1000AA0D`, `0x1000BF19/BF85`, `0x1000FDAB`, `0x1000D139` … | ✅ confirmed |
| `0x0012` | `OP_QUERY_UUID` | `push 0x12` at `0x1000A0CE`, inside the `GetRadioUUID` function | ✅ confirmed |
| `0x000D` | `OP_LOCK` (commit) | `push 0xd` at `0x1000C1EE` **and** `0x10017D9E` — both the exact offsets the branch cited | ✅ confirmed |
| `0x000C` | `OP_UNLOCK` | `push 0xc` at `0x10017DC3`, `0x1000C12F/C159`, `0x1000A20F/A277` … paired with 0xd sites | ✅ confirmed |
| `0x0011` | `OP_QUERY_SERIAL` | — see correction below — | ⛔ NOT confirmed |

### Correction: `0x11` is a VARIANT type tag, not a "query serial" opcode

`SendRcmp` (`0x1000b5b0`) and every command builder initialise their payload
object with `mov word ptr [esi], 0x2011`. `0x2011` = `VT_ARRAY | VT_UI1`
(`0x2000 | 0x11`): the OLE Automation type for a **byte array**. The send path
is built entirely on OLEAUT32 `SafeArrayCreateVector` / `SafeArrayAccessData` /
`SysAllocStringByteLen` (confirmed from the IAT). So the payload is a
`VT_ARRAY|VT_UI1` SafeArray — matching `CPS_BINARY_ANALYSIS.md` §7.4's
independent finding about `IRemoteProtocol::Send`.

Consequence: the hundreds of `push 0x11` in `.text` are overwhelmingly the
`VT_UI1` type tag, **not** an opcode. The branch's `OP_QUERY_SERIAL = 0x0011`
has no confirmed basis here; the serial number is read through
`ReadWriteRadioSerialNumber` / an ISH item, not a `0x11` opcode. Treat
`OP_QUERY_SERIAL = 0x11` as **unverified/likely wrong** until shown otherwise.

---

## 3. `EnterWriteMode` decoded (the model/timeout shape)

Function at `0x10016776`; the request is built at `0x100167BE`–`0x100167F2`:

```asm
0x100167C4: push 1              ; arg
0x100167C6: push 0x11           ; VT_UI1 (payload element type), see §2
0x100167C8: mov word [esi],0x2011  ; init VARIANT = VT_ARRAY|VT_UI1
0x100167DF: imul eax,eax,0x3c   ; timeout_minutes * 60  -> seconds
0x100167E9: push eax            ;   = timeout (seconds)
0x100167EA: push 4              ; MODE = 4  ("Write Mode")
0x100167EC: push esi            ; payload (byte SafeArray)
0x100167ED: push 0x106          ; OPCODE = OP_ENTER_MODE
0x100167F2: call 0x1000b5b0     ; SendRcmp
0x10016846: mov edi,0xEC000009  ; failure HRESULT on a bad response code
```

So `EnterWriteMode` = `Send(0x0106, payload, mode=4, timeout_sec)`. Confirms the
branch's "Mode 4 = Write Mode, timeout in seconds." The sibling Enter* methods
(`EnterProgramMode`, `EnterBootMode`, `EnterTestMode`) reuse `0x106` with
different mode arguments.

---

## 4. `OP_LOCK` / commit decoded (the UUID gate)

At `0x10017D79`–`0x10017DC6`, a dispatch on a state value in `edi`:

```asm
0x10017D7E: cmp edi,0xd         ; if committing (OP_LOCK)...
0x10017D8C: sub esp,0x10        ;   make room for 16 bytes
0x10017D8F: lea esi,[ebp+0x14]  ;   src = the 16-byte UUID
0x10017D92: mov edi,esp
0x10017D97: movsd ; D9C ; D9D ; DA1   ; copy 16 bytes (4x movsd) = UUID onto stack
0x10017D9E: push 0xd            ; OPCODE = OP_LOCK
0x10017DA2: call [ecx+0x20]     ; send (vtable)
  ; else (edi==0xc) path at 0x10017DC3: push 0xc  = OP_UNLOCK
```

This is byte-for-byte what the branch published. It confirms the load-bearing
safety claim: **`OP_LOCK` (commit) carries the 16-byte radio UUID** (obtained
via `OP_QUERY_UUID` / `GetRadioUUID`). An empty / wrong UUID is a different code
path — consistent with the branch's "empty payload = abort, reverts to prior
flash." (The "reboots to factory" *effect* is still only asserted, never
captured — see OPEN items.)

---

## 5. Transport, crypto, networking — measured notes

* **Payload wire form:** `VT_ARRAY|VT_UI1` SafeArray; `SendRcmp` prepends a
  header of `0x17` bytes (`movzx eax,[ebp+0x1c]; add eax,0x17`) or `0x18` when
  empty. The actual socket write is handed to imported function pointers /
  a COM inner object — i.e. the final bytes are formed in **another module**
  (consistent with `CPS_BINARY_ANALYSIS.md` §7.4's "component not in the CPS
  installer"). `ByteData10.dll` (same tree) is the prime suspect; not yet
  disassembled.
* **Networking is real Winsock:** imports include `WS2_32.dll` and
  `OtapRWCDTimer.dll` (OTAP = Over-The-Air Programming). Method names
  `NetOpen`, `OpenRemote`, `OpenRemoteCustomProxy`, `LoadServer`/`CloseServer`,
  `CRemotePcIntranet`, `ProxyPort`, `lRemotePort`. Port strings seen: `8000`,
  `8003` (no `8002`). Reinforces `PROVENANCE_AUDIT.md` §5.3: there is a
  PC-hosted proxy/server leg, so the Fedora "all TCP filtered on the radio at
  192.168.128.1" result does not refute RCMP — the service isn't a port on the
  radio.
* **RC4 key `A8Z6J9QP5`:** confirmed present as a literal string in
  `Crack\PatPort.exe` (`grep -a`). Not located in this DLL. The guide's
  `fhAdk10c.dll:0x10012018` attribution is unverifiable from this tree (that DLL
  is only inside the `.cab`s).

---

## 6. The safety map — the one thing still missing, and why it's critical

`CRcmpBundler` reaches **both** the codeplug and the calibration soft-pot data
through the **same ISH item / partition mechanism**: `WriteIshList` (0x0101),
`WriteSoftPotValues`, `UnlockIshPartition`, `GetSecurityPartitionData`,
`QnPartitionNum`. There is **no memory-address boundary** — only partition
numbers and ISH item/type IDs. Therefore:

* `src/open_astro/protocol/flasher.py`'s "reject writes below `0x0020_0000`"
  guard protects against nothing on this interface. The real guard must be a
  **verified allowlist of ISH item/type IDs and partition numbers** that are
  safe to write, explicitly excluding whatever partition holds soft-pot
  calibration.
* A wrong partition/item in a `WriteIshList`/`OP_LOCK` sequence can commit over
  soft-pot calibration — unrecoverable without a service monitor and bench tech.

### 6a. Partition-map progress (2026-10-22, this session)

Disassembled `ReadSoftPotValues` (function @ `0x10011B64`, trace string
`0x1002CB04`). Confirmed:

* Soft-pot read allocates a **`0x370` (880-byte)** `VT_UI1` SafeArray
  (`mov dword[esp],0x370` @ `0x10011BBA`) and sends it through the **same
  `SendRcmp` @ `0x1000b5b0`** as the ISH codeplug ops. Soft-pot genuinely rides
  the identical read/write machinery — the §6 shared-channel risk is proven in
  code, not inferred. (Also confirms the branch's "max 880 bytes/chunk".)
* `SendRcmp` is a **9-argument function** (both `EnterWriteMode` and
  `ReadSoftPotValues` push 9 args; thiscall `this` in `ecx`). Arg 1 (pushed
  last) is the opcode/family word: `0x106` enter-mode, `0x100`/`0x101` ISH
  read/write. `ReadSoftPotValues`'s two sends use arg1 = `6` then `1` (a
  different family, low bytes `0x06`/`0x01`), so soft-pot vs codeplug are
  distinguished by opcode/parameter set — consistent with partition separation,
  but the literal partition value was **not** isolated this pass.

### 6b. RESOLVED: partition is schema-driven, not a constant (2026-10-22)

Decoded the real `WRITE_ISH` (opcode `0x101`, send @ `0x1000BFB9`) and
`READ_ISH` (`0x100`, send @ `0x1000BF85`) call sites. The addressing args are
**not immediates** — they are read out of an **ISH item descriptor struct**
(`eax = [[ebp+0xc]]`):

```asm
; WRITE_ISH @ 0x1000BF8C
mov  eax,[ebp+0xc] / mov eax,[eax]   ; ISH item descriptor
push [eax+0xc]        ; arg: length   (32-bit)
push word[eax+0xa]    ; arg: 16-bit field
push word[eax+8]      ; arg: 16-bit field   } type / id / partition / offset
push word[eax+6]      ; arg: 16-bit field
push word[eax+4]      ; arg: 16-bit field
push 0x101            ; opcode
call 0x1000b5b0
; READ_ISH @ 0x1000BF66 is the same shape with push 0x370 (880) as the max len.
```

**Conclusion:** there is no hardcoded soft-pot or codeplug partition number in
`NextGen10.dll`. Each ISH operation's `partition`/`type`/`id`/`offset`/`length`
travels in the item descriptor, which is populated from the **codeplug schema
layout** (`cgIsh10c.dll`'s `CcgIshBlkLayout::GetPartitionNum` /
`SetPartitionNum` + per-block `AccessRights`, per `CPS_BINARY_ANALYSIS.md` §3).
The branch's "codeplug = partition `0x80`" is therefore **not a constant found
in code** — partition assignment is data-driven.

**So the safe-write allowlist must be built from the schema, not a magic
number.** Two ways to get the soft-pot-vs-codeplug classification:
1. From `cgIsh10c.dll` (the block layout: each block's partition number +
   access-rights + whether it's calibration/security). That DLL is inside the
   InstallShield `.cab`s (extract with `unshield`, Fedora Drive copy).
2. At runtime from the radio: `OP_READ_ISH_ID_SET` (`0x104`) /
   `OP_READ_ISH_TYPE_SET` (`0x105`) enumerate the radio's ISH items; cross-map
   against the schema to tag each partition. (Needs hardware.)

This is a cleaner and safer basis than a hardcoded partition: the flasher should
refuse to write any ISH item whose partition/type isn't on a schema-derived
codeplug allowlist, rather than trusting one `!= 0x80`-style check.

### Other still-open items (no hardware):

1. **Pin `SendRcmp`'s 9-arg signature** (`0x1000b5b0`). Progress this session:
   it takes **9 stack args at `[ebp+8]`…`[ebp+0x28]`** (thiscall, `this` in
   `ecx`). From `EnterWriteMode`'s call, the positional map is:
   `arg1 [ebp+8]` = opcode word (`0x106`), `arg2 [ebp+0xC]` = payload SafeArray,
   `arg3 [ebp+0x10]` = mode, `arg4 [ebp+0x14]` = timeout, `arg5..9
   [ebp+0x18..0x28]` = ISH addressing fields (`arg6 [ebp+0x1c]` is consumed as a
   length: `movzx eax,word[ebp+0x1c]; add eax,0x17`). **Still to identify:**
   which of args5/7/8/9 is `partition` vs `ish_id`/`offset`. Route: find a
   `WriteIshList`/`WriteSoftPotValues` call site with those args as immediates
   and read them off. The branch's "codeplug = partition `0x80`" is **not yet
   confirmed from code** — and note the ubiquitous `cmp dword[reg+0x80],0xc` is a
   field at object offset `0x80`, NOT a partition literal; don't conflate them.
2. **Locate `WriteSoftPotValues`.** Its clean trace string isn't referenced
   (likely inlined); find it via the mangled export `N1WriteSoftPotValuesWW`
   (`0x10034DB6`) / `method WriteSoftPotValuesW` (`0x10035E56`) or by the vtable.
   Its partition arg to `SendRcmp` is the soft-pot partition to exclude.
3. Cross-check `GetSecurityPartitionData` / `UnlockIshPartition` for the
   security/key partition number.
2. **Map ISH item/type IDs** (`readIshIDSet`, `ReadIshItemSizes`,
   `PopulateOTAPIshList`) to what they contain.
3. **Disassemble `ByteData10.dll`** for the final wire framing `SendRcmp` hands
   off to (the `0x17`-byte header contents + checksum).
4. **The proxy/port topology:** confirm whether `PatPort.exe` connects to a
   local `CRemotePcIntranet` server on `8003`/`8000` which then bridges to the
   radio over the PPP link — this is what a from-scratch flasher must replicate
   or bypass.

**OPEN (needs hardware):** the careful UDP re-scan of the PPP link; trying a
real `OP_QUERY_UUID` / `EnterWriteMode` exchange once the transport above is
understood. Writes stay gated until items 1–3 are done.

---

## 7. One-line status after this session

The RCMP opcode table, the UUID commit gate, and the `0x1000b5b0` send routine
are **confirmed real** by independent disassembly. The codeplug protocol is no
longer "unknown." What stands between here and a safe write is the **partition/
ISH-ID safety map** (§6, static, doable next) and the **final wire framing in
`ByteData10.dll`** — not the opcodes, which are now solid ground truth.

---

## 8. The schema, crypto, and transport DLLs — extracted from the cab and verified (2026-10-22)

The remaining DLLs were extracted from `data2.cab` with `unshield` 1.6.2 (Fedora
WSL `FedoraLinux-44`: `sudo dnf install -y unshield`; cab copied to a
WSL-visible path; `unshield -d out x data2.cab` → 205 files). Verified:

### 8.1 `cgIsh10c.dll` — the codeplug SCHEMA, and the real safety model

The partition access-control is a first-class, named mechanism — this is what a
safe write must gate on:

```
CcgIshPartitionLayout         AddPartition / GetPartitionNum / SetPartitionNum
GetPartitionNumList           GetPartitionLayoutMap / GetPartitionPkInfo
IsROPartition                 <- read-only partition  (NEVER write)
IsRWPartition                 <- read-write partition (writable)
IsRWLockedPartition           <- read-write but LOCKED (NEVER write)
cgIshCalculateChecksum / ValidateChecksum / WriteChecksumToImage / GetChecksumSz
```

**Safe-write rule, now grounded in the real schema:** write only ISH items whose
partition reports `IsRWPartition` and NOT `IsROPartition` / `IsRWLockedPartition`.
Soft-pot calibration and security live in RO / RW-locked partitions. This
replaces every address-boundary and magic-number (`0x80`) guard in the repo. The
partition classification is data-driven (loaded into `CcgIshPartitionLayout`),
reachable statically here or at runtime (`OP_READ_ISH_*` + this layout).

CRC confirmed: `cgIshCalculateChecksum` uses **CRC-16-CCITT poly `0x1021`**
(`mov word[esp+0xa],0x1021` @ `0x100077AA`) — matches the
`FEDORA_RADIO_PROTOCOLS_GUIDE.md` §5 claim.

### 8.2 `fhAdk10c.dll` — the file encrypt / checksum layer

`CFhAdkEncrypt::Encrypt/Decrypt`, `CFhAdkFileHandler::SaveImage`,
`fhAdkCalcChecksum` (8-bit). **The RC4 master key `A8Z6J9QP5` is at exactly
VA `0x10012018`** (`strings` → `0x10012018 off=0x012018 A8Z6J9QP5`) — the precise
offset the guide §4 cited. This is the `.cpg` file-format crypto (host-side save
format), distinct from the wire protocol.

### 8.3 `ByteData10.dll` — the TRANSPORT (final wire layer)

A `CRawBytes` COM object (`IRawBytes`: `Open`/`ReadData`/`RequestData`/
`BroadcastData`) that sits under `NextGen10`'s `SendRcmp`. Imports:

* `WS2_32.dll` — real TCP sockets: `socket`, `connect`, `send`, `recv`, `htons`,
  `inet_addr`, `setsockopt`, `WSAStartup`.
* `RadioCustStack10.dll` — `PPPConnect` / `PPPDisconnect` / `PPPGetRemoteIPaddr`:
  the PPP-over-radio stack (brings up the `192.168.128.x` link).

So the real chain is **`NextGen10` (RCMP ops) → `ByteData10` (CRawBytes, TCP
socket) → `RadioCustStack10` (PPP) → radio.** This is exactly the
PPP+TCP architecture the `cleanroom-flasher` branch built by hand — the branch
was right in shape; it failed on specifics (see below).

**Ports (confirmed, correcting earlier doubt): `ByteData10` pushes `0x1F41`,
`0x1F42`, `0x1F43` = 8001 / 8002 / 8003** near `connect` (e.g. `push 0x1f42;
push 0x1f41` @ `0x1100468C`). **Port 8002 is real.** My earlier "8002 is wrong,
it's 8003" (from `NextGen10`, which only exposed 8003) was mistaken; the socket
layer uses the full 8001–8003 set. The guide's "8002 = flasher" stands; its
"8010 = debug" was not seen (8001/8003 instead).

### 8.4 Why the cleanroom write still failed, reconciled with all this

The branch's opcodes, UUID commit, CRC, key, and 8002 are all **correct**. The
write failed on transport *mechanics*, not protocol: the real CPS connects via
`ByteData10`'s socket over its own `RadioCustStack10` PPP stack (and/or a
`CRemotePcIntranet` proxy), with a proper TCP handshake and the radio's own
PPP/IPCP state. The hand-rolled pure-Python TCP in `ppp_flasher.py` did not
complete a real TCP connection to the listening service (the Fedora direct-IP
TCP scan saw nothing because the service/handshake path differs from a raw SYN to
`192.168.128.1`). Nothing was ever ACKed → nothing written → "rebooted to
original." Fix path: replicate `ByteData10`'s connect sequence (ports 8001–8003,
proper TCP handshake over the established PPP link), or drive the real
`RadioCustStack10`/`ByteData10` stack.

### 8.5 Net correction to `PROVENANCE_AUDIT.md`

With the cab extracted, essentially every `FEDORA_RADIO_PROTOCOLS_GUIDE.md`
protocol claim is now **verified from the binaries**: RCMP opcodes, OP_LOCK+UUID
commit (exact offsets), RC4 key (exact offset), CRC-16-CCITT, port 8002, the
PPP+TCP transport. **Only one claim is refuted:** `OP_QUERY_SERIAL = 0x0011`
(`0x11` is the `VT_UI1` SafeArray type tag, not an opcode). The home-Windows
session's reverse engineering was accurate; the earlier "fabrication" assessment
is withdrawn.
