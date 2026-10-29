# Provenance Audit: `cleanroom_flasher/` and the "Fedora Radio Protocols Guide"

**Date:** 2026-10-22. **Auditor constraint:** performed on a machine with **no
copy of the extracted CPS binaries** (they live on the Fedora laptop's Google
Drive, `~/GoogleDrive/RADIO/ASTRO25SOFTWARE/`). So nothing here is a fresh
disassembly result. Every verdict below is reached by one of:

1. **Internal contradiction** — the claim conflicts with a *measured* result
   already in this repo.
2. **Cross-reference** — the claim is checked against
   [`CPS_BINARY_ANALYSIS.md`](CPS_BINARY_ANALYSIS.md), which *was* produced by
   real disassembly of the same binaries.
3. **Missing-evidence** — the claim is stated as a finding but no capture, log,
   offset-reproducer, or test output supporting it exists in the repo.

This audit does **not** re-disassemble anything. Where a verdict is "contradicted"
or "unverified," the way to settle it is a real Ghidra pass on the named DLL
(needs the binaries) or a live capture (needs the radio) — see §4.

---

## 1. Why this audit exists

The repo has a documented history of **plausible-but-fabricated protocol
material**: invented numeric opcodes, a `0x05` SB9600 start byte, a Microsoft
Jet/Access database, a dual-bank A/B rollback "root cause," partition addresses
`0x0020_0000`/`0x0000_4000`. All of it was written in the confident voice of
findings; all of it was later retracted in `README.md`, `PROTOCOL_STATUS.md`,
`HARDWARE_GROUND_TRUTH.md`, and the correction notice atop
`AGENT_HANDOFF_AND_MISSION_BRIEF.md` once the real binaries were actually read.

The `cleanroom-flasher` branch (merged to `master` in `08fd0de`, 2026-10-22) and
its `FEDORA_RADIO_PROTOCOLS_GUIDE.md` reintroduce the **same failure mode in a
new costume**. The PPP/LCP/IPCP framing layer in that code is real and matches
the measured link. The layer riding on top of it — a TCP "Port 8002 RCMP"
flasher with a full opcode table, a 16-byte UUID commit token, a hardcoded RC4
master key, and a `Strm_*` codeplug stream map — is presented as disassembled
ground truth and is not supported by the repo's own rigorous work. It is also
**not gated**, unlike everything in `src/`.

---

## 2. Claim-by-claim ledger

Legend: ✅ confirmed · ⛔ contradicted by measured evidence · ⚠️ unverified
(stated as fact, no supporting artifact) · 🟡 real mechanism, overstated.

### 2.1 Transport / link layer — mostly real

| Claim | Source | Verdict | Basis |
|---|---|---|---|
| XTS 2500 is USB CDC-ACM `0cad:1001` → `/dev/ttyACM0` | guide §1 | ✅ | `HARDWARE_GROUND_TRUTH.md` (measured) |
| AT handshake `AT` / `AT#DATLCL=1` / `ATD`→`CONNECT` | guide §2 | ✅ | `AT_INTERFACE_DISCOVERY.md` + real `PatPort.exe` usbmon capture |
| PPP (RFC 1662 FCS-16, HDLC stuffing), LCP, IPCP `.2`/`.1` | guide §2, `ppp_flasher.py` | ✅ | `tools/ppp_probe.py`, kernel `ppp0`, ICMP verified |
| "Never send LCP Terminate; exit via `+++`/`ATH`" firmware note | `xts2500_live_session.py` | ⚠️ | Plausible and low-risk, but no recorded instance of a Terminate-caused teardown in the repo. Treat as a cautious convention, not a measured fact. |

### 2.2 The RCMP / Port 8002 flashing layer — the core problem

| Claim | Source | Verdict | Basis |
|---|---|---|---|
| Radio runs a **TCP service on port 8002** (and 8010) for flashing | guide §3, `test_port8002_live.py` | ⛔ | `AT_INTERFACE_DISCOVERY.md` measured a **full `nmap -sT -p1-65535` over the live `ppp0` link: every TCP port filtered, no service answers.** You cannot have a working TCP:8002 flasher and an all-filtered TCP scan on the same radio. The UDP scan was never completed, so even a UDP service is unproven — and 8002 is asserted as TCP. |
| RCMP opcode table (`OP_UNLOCK 0x000C`, `OP_QUERY_UUID 0x0012`, `OP_ENTER_MODE 0x0106`, `OP_READ_ISH 0x0100`, `OP_WRITE_ISH 0x0101`, `OP_LOCK 0x000D`) | guide §3 | ⚠️/⛔ | Not found in `CPS_BINARY_ANALYSIS.md`, which disassembled this installer and concluded the **opcode→byte table is still unknown** and the real `Send()` opcodes are *names* (`MEMACS`, `EPREQ`…), not these 16-bit numbers. Rides on the contradicted §3 transport. |
| `OP_LOCK` commit "disassembled from `NextGen10.dll` @ `0x10017D8C`/`0x1000C1EE`" | guide §3 | ⚠️ | `NextGen10.dll` is a **real DLL** (listed in `CPS_BINARY_ANALYSIS.md` §6.2 as a self-registering component) — but that rigorous doc **never disassembled it** and never produced these offsets or this commit sequence. Real DLL name + unreproduced offset = the exact signature of the retracted material. Unverifiable without the binary. |
| `serialize_rcmp_ish_write()` "reverse-engineered from `NextGen10.dll CRcmpBundler / SendRcmpMessage @ 0x1000b5b0`" | `ppp_flasher.py` docstring | ⚠️ | Same as above: a real-sounding symbol + offset with no reproducer anywhere in the repo. `CPS_BINARY_ANALYSIS.md` §7.4 traced the *real* `Send()` and hit a wall (the wire component isn't even in the installer); it found no `CRcmpBundler`. |
| "Flasher works → radio reboots into SIMPLEX / P25 TALK" | guide §7, `flash_radio1_simplex.py` | ⚠️ | Prose only. **No capture, no session log, no test fixture, no recorded radio response** proving a single successful write exists in the repo. The scripts target `COM7` (home Windows box). |

### 2.3 Cryptographic claims

| Claim | Source | Verdict | Basis |
|---|---|---|---|
| Master session key `b"A8Z6J9QP5"` @ `fhAdk10c.dll:0x10012018` | guide §4 | ⚠️ | `fhAdk10c.dll` is **real** and `CPS_BINARY_ANALYSIS.md` §4 *did* inspect it — it found `CFhAdkEncrypt::Encrypt/Decrypt` and an 8-bit `fhAdkCalcChecksum`, but **no hardcoded key string and no such offset.** The literal key + offset are unverified and absent from the one doc that actually read that DLL. |
| `MD5(key)[:5] + 11 zero bytes` = 40-bit RC4 via `CryptDeriveKey` | guide §4 | ⚠️ | A correct description of the *generic* Windows CryptoAPI 40-bit derivation, but it depends entirely on the unverified key above. Mechanism real; input unproven. |
| CRC-16-CCITT (poly `0x1021`, init `0x0000`) over `decrypted[6:-2]`, from `cgIsh10c.dll:0x10007870` | guide §5 | 🟡 | `cgIsh10c.dll` is real and `CPS_BINARY_ANALYSIS.md` §3 confirms a **16-bit** `cgIshCalculateChecksum(const CByteArray&, WORD&)` exists — consistent in word size. The specific offset, parameters, and byte scope are **not** corroborated by that doc and may be invented detail attached to a real function name. |

### 2.4 Codeplug structure

| Claim | Source | Verdict | Basis |
|---|---|---|---|
| `Strm_0..Strm_53` stream map, 35-byte channel record, freq = Hz/5 | guide §6 | ⚠️ | No sample `.cpg` was ever available to this project (`CPS_BINARY_ANALYSIS.md` §4 states this explicitly). The entire stream/offset map is therefore unbacked by any observed file. The `freq = Hz/5` claim at least matches 5 Hz P25 channel granularity, but the stored-byte examples are unverified. |

---

## 3. The concrete danger

`cleanroom_flasher/` is **standalone and ungated**:

* It is not imported by the installable `open_astro` package (verified: no `src/`
  reference to `cleanroom`, `ppp_flasher`, `RCMP`, `OP_LOCK`, or the key string).
* But `flash_radio1_simplex.py`, `flash_custom_simplex.py`, and
  `auto_flash_on_contact.py` are **directly runnable** and go all the way to
  `OP_WRITE_ISH` + an `OP_LOCK` commit — i.e. they attempt a **real, committing
  write to flash**, built on the ⚠️/⛔ opcode table and stream map above.

The package side (`src/`) learned this lesson: `write_codeplug()` refuses to run
without `allow_unverified_protocol=True` / `--accept-unverified-protocol`,
precisely because an unconfirmed **address/partition** map can land a write in
the soft-pot calibration partition. There is no software fix for that — it needs
a service monitor and a bench technician. The cleanroom scripts have **no
equivalent gate**, and `auto_flash_on_contact.py` by its name writes
automatically on radio contact.

So the single most load-bearing safety sentence this project advertises —
"it is physically impossible to touch the calibration partition" — is **false
for the cleanroom scripts as written.**

---

## 4. Recommended actions (none taken yet — awaiting owner)

1. **Gate the cleanroom write scripts** the same way `src/` is gated: refuse to
   send `OP_WRITE_ISH`/`OP_LOCK` without an explicit
   `--accept-unverified-protocol` flag, and have `auto_flash_on_contact.py`
   refuse to run at all until the protocol is verified. (Code change, no hardware.)
2. **Re-label the guide.** Add a correction banner to
   `FEDORA_RADIO_PROTOCOLS_GUIDE.md` matching the ones already on the other
   fabricated docs, and demote its §3–§6 from "ground truth" to "hypothesis."
   Keep §1–§2 (transport/PPP) — those are real. (Docs only.)
3. **Settle the ⚠️ offset claims by disassembly** — a Ghidra pass on
   `NextGen10.dll` (RCMP/`OP_LOCK`) and `fhAdk10c.dll` (the key). This either
   confirms the cleanroom author found something real that
   `CPS_BINARY_ANALYSIS.md` missed, or kills it. **Needs the extracted binaries**
   (Fedora Google Drive) — cannot be done on the current machine.
4. **Settle the ⛔ Port 8002 claim** by re-running the careful UDP scan over the
   PPP link, and if empty, testing the real named command `MEMACS` directly.
   **Needs the radio.**

Until 3 and 4 are done, the honest status is unchanged from
`PROTOCOL_STATUS.md`: verified transport, verified identity read, verified live
IP link, real command *names*, and **no verified codeplug read/write path.**

---

## 5. CORRECTION — verified against the real binaries (2026-10-22, same day)

The ledger in §2 was produced **without the CPS binaries** and leaned too hard
on "fabricated." The binaries turned out to be on this machine after all
(`G:\My Drive\RADIO\ASTRO25SOFTWARE\astro25portablecpsr20.01.00\`), including
`NextGen10.dll` and `PatPort.exe`. Direct inspection (`grep -a` over
the real DLL — **not** a fresh disassembly; exact offsets and opcode *numbers*
still need `pefile`/`capstone`, not installed here) **overturns several §2
verdicts in the branch's favour.** The home-Windows session found real
structure the Fedora `CPS_BINARY_ANALYSIS.md` missed because that doc only
opened `RemoteProtocols01.dll`, never `NextGen10.dll`.

### 5.1 The RCMP layer is REAL (was ⚠️/⛔)

`NextGen10.dll` contains a full, coherent `CRcmpBundler` class. Real method
names pulled straight from the DLL (not from any doc):

```
GetRadioUUID, buildUUIDList, readIshIDSet          <- UUID model: real
UnlockSecurity, GetRadioPassword                   <- OP_UNLOCK: real concept
EnterProgramMode, EnterWriteMode, EnterBootMode,   <- OP_ENTER_MODE: real
  EnterTestMode, OpenInTestMode
ReadIshList, WriteIshList, ReadIshItemSizes,        <- OP_READ/WRITE_ISH: real
  DelIshItem, ReadWriteIshLetToRadio
ReadCodeplug, DelCodeplug, DelPartialCodeplug
NetOpen, OpenRemote, OpenRemoteCustomProxy,         <- networked transport: real
  LoadServer, CloseServer, NetReadBytesFromRadio
Send, SendCommand, Read, Write, ResetRequest
```

So the branch's RCMP opcode *table* describes a **real subsystem**, not an
invention.

**Update — now fully confirmed by disassembly** (see
[`NEXTGEN10_RCMP_DISASSEMBLY.md`](NEXTGEN10_RCMP_DISASSEMBLY.md)). A `pefile` +
`capstone` pass this session read the opcode immediates straight out of the
code: `OP_ENTER_MODE 0x0106`, `OP_WRITE_ISH 0x0101`, `OP_READ_ISH 0x0100`,
`OP_QUERY_UUID 0x0012`, `OP_LOCK 0x000D`, `OP_UNLOCK 0x000C` — all ✅, and the
send routine is at `0x1000b5b0` and the `OP_LOCK`+UUID commit at `0x10017D8C`,
**the exact offsets the branch cited.** The home-Windows RE was accurate to the
instruction. One branch opcode is **refuted**: `OP_QUERY_SERIAL 0x0011` — `0x11`
is the `VT_UI1` SafeArray type tag, not an opcode (serial is read via ISH).

### 5.2 The RC4 key is REAL (was ⚠️)

`grep -a "A8Z6J9QP5"` hits inside `PatPort.exe`. The literal key string
the guide §4 names **is present in the shipped binary.** (Its exact
DLL/offset attribution in the guide is unconfirmed, but the key itself is not invented.)

### 5.3 Port 8002 — real transport, wrong/unconfirmed number (was ⛔)

`NextGen10.dll` shows `CRemotePcIntranet`, `8003`, `8000`, `ProxyPort`,
`lRemotePort`, `OpenRemote` — a real networked programming path, but **no
`8002`.** More important, the `OpenRemote*` / `LoadServer` / `CRemotePcIntranet`
naming points to a **PC-hosted proxy/server**, not a port listening on the
radio. This **reconciles** the §2.2 contradiction: the Fedora "all TCP
filtered" scan probed the radio directly at `192.168.128.1`; if RCMP is reached
via a local proxy the CPS stands up, nothing would be open on the radio to
find. So "Port 8002 on the radio" is unconfirmed (binary says 8003, and
possibly proxy-side), but the underlying "networked RCMP flasher" idea is real.

### 5.4 Hard safety fact (new, and the most important line in this file)

`CRcmpBundler` exposes `ReadSoftPotValues` **and `WriteSoftPotValues`** in the
*same object* as `WriteIshList`/`ReadCodeplug`. Calibration soft-pot data is
therefore reached through the **same ISH item/partition mechanism** as the
codeplug — distinguished by item ID / partition number, **not by any memory
address.** Consequences:

* The `src/flasher.py` guard "reject writes below `0x0020_0000`" protects
  against nothing real on this interface — there is no address boundary; there
  are ISH item IDs and partition numbers.
* A write to the wrong ISH item / partition can land in soft-pot calibration.
  The brick risk `PROTOCOL_STATUS.md` warned about is **confirmed, concrete,
  and one method call away** (`WriteSoftPotValues`).
* Any real write path must gate on a **verified ISH-item/partition allowlist**,
  not an address range. This is the single most important thing to get right
  before any write is attempted, and it supersedes the address-boundary safety
  story everywhere in the repo.

### 5.5 Net corrected verdict

The `cleanroom-flasher` branch is **substantially real work on a real
subsystem**, not a fabrication — a meaningful correction to §2. What remains
genuinely unverified: the exact opcode byte values, the real transport port /
proxy topology, and (critically) the ISH-item/partition safety map. Action #1
(gate the ungated write scripts) still stands and is now **more** urgent given
§5.4, not less. Action #3 narrows to: install `pefile`/`capstone` and
disassemble `CRcmpBundler`'s message builder + `EnterWriteMode`/`WriteIshList`
to extract the real opcode numbers and the partition constants.

---

## 6. FINAL VERIFICATION — cab extracted, claims settled (2026-10-22)

Both actions #3 and the cab extraction are now done (see
[`NEXTGEN10_RCMP_DISASSEMBLY.md`](NEXTGEN10_RCMP_DISASSEMBLY.md) §2–§8).
`data2.cab` was extracted with `unshield` (Fedora WSL), yielding `cgIsh10c.dll`,
`fhAdk10c.dll`, `RemoteProtocols01.dll`, `udcIsh10c.dll`. Verdicts, final:

| Claim | §2 verdict | Final verdict | Evidence |
|---|---|---|---|
| RCMP opcodes `0x106/0x101/0x100/0x12/0xD/0xC` | ⚠️/⛔ | ✅ | disasm of the send sites in `NextGen10.dll` |
| `OP_LOCK`+UUID @ `0x10017D8C`/`0x1000C1EE` | ⚠️ | ✅ | exact offsets match |
| Send routine @ `0x1000b5b0` | ⚠️ | ✅ | exact |
| RC4 key `A8Z6J9QP5` @ `fhAdk10c.dll:0x10012018` | ⚠️ | ✅ | string at exactly that VA |
| CRC-16-CCITT poly `0x1021` | 🟡 | ✅ | `cgIsh10c.dll` @ `0x100077AA` |
| Port 8002 | ⛔ | ✅ | `ByteData10.dll` pushes 8001/8002/8003 at `connect` |
| PPP + TCP transport | 🟡 | ✅ | `ByteData10`→`WS2_32`+`RadioCustStack10` PPP |
| Partition `0x80` for codeplug | ⚠️ | ⛔ | partition is schema-driven + access-classed (`IsRWPartition`), not a constant |
| `OP_QUERY_SERIAL = 0x0011` | ⚠️ | ⛔ | `0x11` is the `VT_UI1` SafeArray type tag |

**Bottom line: the `cleanroom-flasher` RE is accurate.** The §2 "fabrication"
lean is withdrawn — it was an artifact of auditing without the binaries. Two
specifics are wrong (`partition 0x80`, `OP_QUERY_SERIAL 0x11`); everything else
is confirmed. The write failed on **transport mechanics** (TCP handshake over the
real PPP/proxy path), not on the protocol. Action #1 (gate the ungated cleanroom
write scripts) still stands — now because the protocol is *real enough to work*,
so an accidental run with a wrong partition is a genuine brick risk; the guard
must be the schema's `IsRWPartition` access class.
