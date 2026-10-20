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
  `--accept-unverified-protocol` on `open-astro write`.
* `read_codeplug()`, `probe` and `reboot` are **not** gated. They are expected to
  do nothing useful, and they are the natural first-contact tests once the
  framing is known.
* The transport layer (port detection, CDC-ACM, permissions) **is** verified —
  see `HARDWARE_GROUND_TRUTH.md`. That part can be trusted.

## Getting to ground truth

In rough order of cost:

1. **Disassemble the real CPS communication code.** Extract the installer with
   `unshield`, find the module that drives the serial port, and read its framing
   and opcode dispatch. This is the authoritative answer and needs no radio.
2. **Capture a live session.** Run CPS R20.01.00 under Wine or in a Windows VM
   with the radio passed through, and record the USB traffic with `usbmon`
   (`modprobe usbmon; cat /sys/kernel/debug/usb/usbmon/3u`) or Wireshark's
   USB capture. This gives the exact byte sequence for read and write, including
   whatever handshake precedes it.
3. **Cross-check against published work.** Other projects have documented parts
   of Motorola's serial protocols; treat them as leads to verify against (1) or
   (2), not as sources to copy into this repo as fact.

Until one of those lands, the honest description of this project is: a working
codeplug data model and CSV/JSON toolchain, a verified USB transport, and a
protocol layer that is a hypothesis.

## Rule going forward

Any claim about opcodes, addresses or timing that enters this repo carries its
provenance: *measured* (with the command or capture that shows it), *from
Motorola's code* (with the binary and offset), or *hypothesis* (said plainly).
Nothing presented as a capture that is not one.
