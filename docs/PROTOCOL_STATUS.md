> [!WARNING]
> **SUPERSEDED (historical).** Status here is out of date. Current state: [HANDOFF_RCMP_LIVE.md](HANDOFF_RCMP_LIVE.md); doc map: [README.md](README.md).

# Protocol Status: What We Actually Know

This repo's protocol layer is **unverified**. This file records the distinction
between what was measured and what was assumed, so that future work builds on
the former.

Last reviewed: 2026-10-20.

**Update, same day:** the real CPS installer has now been extracted and read.
See [`CPS_BINARY_ANALYSIS.md`](CPS_BINARY_ANALYSIS.md) for what that turned up —
short version: SB9600 is real (`RemoteProtocols01.dll`, COM class `RemSB9600`),
but every specific byte value, address, and the single-checksum story in the
sections below is still unconfirmed, and the `0x05` start byte specifically has
zero support in the disassembly. Read that document before this one for current
findings; this document's "what is known" section is superseded where the two
disagree.

**Second update, same day:** both paths this file originally listed under
"Getting to ground truth" have now actually been done, with real results —
see `CPS_BINARY_ANALYSIS.md` sections 7-8. Short version: real opcode names
and byte payloads were extracted from `PatPort.exe` by disassembly
(`MEMACS`, `RELEASE`, `EPREQ`, `TSTMOD`, ...), independently cross-confirmed
against a leaked official Motorola SB9600 manual and an unrelated
open-source CRC implementation sniffed from different hardware, and a real
`usbmon` capture of the actual software running under Wine recorded its
exact real connection sequence. The command *content* is no longer a
hypothesis. What's still unresolved: the real software itself fails partway
through that sequence (`AT+IPR=` errors at every baud rate tried, for both
the real app and this project's own test code), and running the original
Windows CPS under Wine on this machine turned out to be a dead end on its
own terms (broken rendering, repeated crashes) separate from that wall. See
`CPS_BINARY_ANALYSIS.md` and `docs/AT_INTERFACE_DISCOVERY.md` (the one
transport that *is* fully working today, for identity only) for the current
state in full.

---

## The problem

`src/open_astro/protocol/` implements a complete, internally consistent SB9600
programming protocol: `0x00`/`0x01` ping and ack, `0x10` enter-programming with a
`0xA5 0x5A` token, `0x11` reboot, `0x14`/`0x15` radio identity, `0x20`/`0x21`
block read, `0x30`/`0x31` block write, `0x32`/`0x33` CRC32 commit with a Bank A /
Bank B staging flip, and a partition map placing tuning at `0x0000_4000` and the
codeplug at `0x0020_0000`.

**None of it was derived from a radio, a capture, or Motorola's code.** The
documents presenting it as a "reverse-engineered opcode reference" and as
"chronological protocol traces captured between CPS and an XTS 5000" are
reconstructions of how the protocol plausibly works. They read as evidence and
are not.

The test suite does not catch this: `MockRadioSerialLink` in
`tests/test_models.py` answers with exactly the invented opcodes, so the tests
confirm the state machine agrees with itself.

Two specific claims in the docs deserve naming, because they are presented as
root-cause findings and were never observed:

* **The dual-bank rollback.** `AGENT_HANDOFF_AND_MISSION_BRIEF.md` and
  `radio_write_failure_diagnosis_and_flashing_engine.md` state that a previous
  write failed because opcode `0x32` was never sent and the bootloader rolled
  back to Bank A. The dual-bank architecture and opcode `0x32` are both
  inventions of the same session that wrote the diagnosis.
* **The 19,200 baud timing analysis.** The "128 KB should take 68 seconds"
  calculation assumes a UART. For the XTS 2500 the link is USB bulk transfer
  (see `HARDWARE_GROUND_TRUTH.md`), so the arithmetic does not describe this
  radio at all.

## Why this is dangerous rather than merely wrong

A guessed command set is usually inert — the radio rejects frames it does not
recognize. A guessed *address map* is not. If the real codeplug partition does
not begin at `0x0020_0000`, then the `target_bank < 0x0020_0000` boundary check
in `flasher.py` is guarding the wrong line, and a write that passes it can land
in the tuning partition. That destroys the factory soft-pot calibration unique to
this radio chassis: reference oscillator warp, PA power curves, front-end filter
alignment. There is no software fix. It needs a service monitor and a bench
technician.

So the single safety guarantee this project advertises — "it is physically
impossible for OpenAstro to touch the soft-pot partition" — currently rests on an
address nobody confirmed.

## Current state of the code

* `write_codeplug()` refuses to run unless the caller passes
  `allow_unverified_protocol=True`; the CLI exposes this as
  `--accept-unverified-protocol` on `open-astro write`. This still protects
  against something real: the REAL_COMMAND_BYTES in `commands.py` are
  confirmed command *content*, but the wire *frame* around them for this
  radio's USB interface (as opposed to the classic hardware-bus SB9600 the
  real CRC algorithm was built for) is still not confirmed to work at all —
  see `CPS_BINARY_ANALYSIS.md` section 7.5's negative test results.
* `probe` now has a real, working, ungated path for native-USB radios: the AT
  command interface (`at_interface.py`, `docs/AT_INTERFACE_DISCOVERY.md`).
  It returns real radio identity today. `read_codeplug()` and `reboot` are
  still only the unverified placeholder path and remain gated/expected to do
  nothing.
* The transport layer (port detection, CDC-ACM, permissions) **is** verified —
  see `HARDWARE_GROUND_TRUTH.md`. That part can be trusted.

## Getting to ground truth: done, with results

Both paths originally listed here have now actually been carried out:

1. **Disassembled the real CPS communication code** -- found the real DLL
   topology, the real `IRemoteProtocol` COM interface, and (the big one) the
   actual function in `PatPort.exe` that builds each named command's 4-byte
   payload, by cross-referencing debug-log strings to their code rather than
   disassembling the whole 24 MB binary. See `CPS_BINARY_ANALYSIS.md`
   sections 1-2 and 7.
2. **Captured a live session** -- got the real `PatPort.exe` running under
   Wine far enough to generate genuine USB traffic, and recorded it with
   `usbmon`. Got the real, exact connection sequence, and caught the real
   software failing at a specific, reproducible step. See
   `CPS_BINARY_ANALYSIS.md` section 8.
3. **Cross-checked against published work** -- found a leaked official
   Motorola SB9600 protocol manual and an independent, hardware-verified
   open-source CRC implementation (different radio, different author), both
   of which independently confirm the real packet field layout this
   project's own disassembly produced. See `CPS_BINARY_ANALYSIS.md`
   section 7.5.

**What remains:** the command content is real and triply cross-confirmed
(disassembly + official manual + independent hardware analysis). What's not
yet working is getting that content actually transmitted and acknowledged by
this specific radio over its native-USB interface -- every direct attempt
this session produced silence or `ERROR`, and the real software itself fails
partway through its own connection sequence in this environment. The honest
description of this project today: a working codeplug data model and
CSV/JSON toolchain, a verified USB transport, a real and working (if narrow)
identity-query command set, and a codeplug protocol whose *content* is now
solid ground truth but whose *transmission* is still unresolved.

**Third update, same day:** the `AT+IPR=` dead end above turned into the
session's biggest result. `ATD` (bare dial) is the missing precondition --
it returns `CONNECT`, and from that state the radio runs a real, standard
PPP stack: a from-scratch RFC 1661/1662 LCP negotiation came up clean
(FCS-verified frames both ways), followed by a real IPCP negotiation
assigning `192.168.128.2` (us) / `192.168.128.1` (radio) -- the same pair
`AT+WPNEI`/`AT+WV304` had already revealed as configured. Brought up a real
kernel `ppp0` with `pppd` against this and confirmed the radio answers ICMP
ping over it. **This is a live, working IP link to the radio**, not a
hypothesis. See `docs/AT_INTERFACE_DISCOVERY.md`'s last two sections and
`tools/ppp_probe.py`.

What's not yet found: the actual codeplug service riding on top of this IP
link. A full TCP port scan of `192.168.128.1` came back entirely filtered --
no TCP service. A UDP scan was started but the `pppd` link died mid-scan
(radio stayed on the USB bus throughout -- a link issue, not a radio fault)
and needs a retry with a narrower range / slower rate. If UDP also comes up
empty, consider a non-socket transport: a raw IP protocol number, multicast,
or a vendor-private PPP protocol field (the way LCP/IPCP occupy their own
protocol numbers) -- see the open question at the end of
`AT_INTERFACE_DISCOVERY.md`.

## Rule going forward

Any claim about opcodes, addresses or timing that enters this repo carries its
provenance: *measured* (with the command or capture that shows it), *from
Motorola's code* (with the binary and offset), or *hypothesis* (said plainly).
Nothing presented as a capture that is not one.
