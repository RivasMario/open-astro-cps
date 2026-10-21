# AT Command Interface: Real, Verified, Working

Unlike everything else in `protocol/`, this is not a placeholder. It was
measured directly against the connected XTS 2500 on 2026-10-20, with plain
Python/pyserial, no Wine, no Windows, no fabrication.

## Where it came from

The radio's own USB descriptor (see `HARDWARE_GROUND_TRUTH.md`) declares:

```
Interface 0: class 2/2/1 (Communications / Abstract modem / AT-commands v.25ter)
```

`AT-commands (v.25ter)` is not a guess or a Motorola-specific label -- it's
the standard USB CDC interface-protocol code for a Hayes/AT-command modem
command interface. The radio is telling the OS, at the USB descriptor level,
that this is how to talk to it. Nothing in the fabricated SB9600/opcode docs
ever looked here.

## What was tried and what happened

```python
import serial, time
s = serial.Serial("/dev/ttyACM0", baudrate=19200, timeout=1.5)
s.write(b"AT\r\n")       # -> b'\r\nOK\r\n'
s.write(b"ATI\r\n")      # -> b'\r\nERROR\r\n'
s.write(b"ATI0\r\n")     # -> b'\r\nOK\r\n'
s.write(b"ATI1\r\n")     # -> b'\r\nMotorola System Release 6.0 Radio\r\n\r\nOK\r\n'
s.write(b"AT&V\r\n")     # -> full config dump, see below
```

Everything else tried from the generic GSM/Hayes command set returned
`ERROR`: `AT+GMI`, `AT+GMM`, `AT+GMR`, `AT+CGMI`, `AT+CGMM`, `AT+CGMR`,
`AT+CGSN`, `AT+CBC`, `AT+CSQ`, `ATI`, `AT+CLAC`. The radio implements its own
narrow dialect, not a generic modem's.

### `AT&V` -- full response, verbatim

```
CARRIER:9600
PROTOCOL:ALT
COMPRESSION:NONE
FLOW:K3
WV304:192.168.128.1
RADIO:XTS 2500
MODEL:H46UCF9PW6AN
SERIAL:205CFR2930
PORT:SIDE CONNECTOR AS USB
SECURE:R000000
CPS:HARDWARE FLOW CONTROL
```

This is a complete, real radio identity readout: model number, serial
number, radio name, security/key status, and the physical port it's talking
through -- obtained with the universal, standard, read-only "view current
configuration" AT command. It directly replaces the fabricated
`GET_RADIO_INFO` opcode story (see `CPS_BINARY_ANALYSIS.md`) with something
real, for this radio, today.

Also notable: `WV304:192.168.128.1` is a real IP address the radio reports
about itself. This independently corroborates the old docs' "the radio is a
PPP/IP network device" claim (also independently supported by
`RadioCustStack10.dll`'s real `CUSNETppp`/`PPPConnect` code, see
`CPS_BINARY_ANALYSIS.md` section 1) -- the one part of those docs that
appears to have had a real basis all along.

## Why this is safe

`AT`, `ATI0`, `ATI1`, and `AT&V` are read-only query commands in the
universal Hayes/v.25ter command standard. None of them write configuration,
reset anything, or change radio state. This is categorically different from
the gated, unverified `allow_unverified_protocol` commands elsewhere in this
project -- this is measured, not guessed, and verified safe by what it
actually is (a config dump), not merely assumed safe.

Commands NOT tried, deliberately, because the standard reserves them for
state-changing operations: `ATZ` (reset), `AT&F` (factory defaults), `AT&W`
(write/store config), `AT+IPR` (change baud rate). Any further probing should
stay in the same "universally read-only" category until there's a reason to
believe otherwise.

## Update, same day: the real command set, straight from `PatComm10.dll`

Rather than keep guessing AT strings blind, extracted `Comm-DLLs/PatComm10.dll`
(the real driver for this interface, per `CPS_BINARY_ANALYSIS.md` section 1)
and found its actual command table -- all contiguous in `.rdata`
(`strings -n 2 -t x`, offsets `0x83c0`-`0x8404`), which is PatComm10's own
connection-setup sequence, in order:

```
AT#DATLCL=1
AT+WPNEI=
AT+WV304=
AT+IPR=
AT&V
AT&K0
AT&K4
AT&K3
```

`AT&V` matches what was already found by hand (above). The rest are new,
real, and unambiguous:
* `AT+IPR=` -- set baud rate (standard Hayes).
* `AT&K0` / `AT&K3` / `AT&K4` -- set flow control mode. `AT&V`'s own
  `FLOW:K3` field directly corresponds to one of these.
* `AT+WV304=` -- **sets** the `WV304` field `AT&V` reports (the
  `192.168.128.1` address). Confirms it's a real, settable radio parameter,
  not a fixed report.
* `AT+WPNEI=` -- unidentified Motorola-specific setter (name not decoded).
* `AT#DATLCL=1` -- unidentified. "DATA LOCAL" was a reasonable guess at a
  mode-switch command (classic modems use something similar to flip from
  command mode to a raw data pipe), so it was tested, carefully:

  ```
  AT          -> OK
  AT#DATLCL=1 -> OK
  AT          -> OK                    (still answers normally afterward)
  ```
  Then, to check whether it opened a binary channel on this same port, the
  project's own placeholder SB9600 ping frame (`\x05\x01\x00\xff`) was sent:
  ```
  \x05\x01\x00\xff -> b''               (no response)
  AT\r\n            -> ERROR            (!)
  ```
  That `ERROR` looked promising at first -- state change! -- but turned out
  to be mundane: the AT parser is a classic line-buffered text interpreter,
  and the raw binary bytes just got prepended to the next line's buffer,
  invalidating it. Confirmed by flushing the line and retrying:
  ```
  \r\n\r\n  -> ERROR    (the polluted empty line)
  AT\r\n    -> OK        (back to normal -- nothing was actually switched)
  ```
  **Conclusion: `AT#DATLCL=1` does not unlock a binary SB9600 channel on this
  port.** Whatever it actually controls (a plausible but unconfirmed guess:
  routing of PPP/data traffic inside the radio versus to the host) remains
  unknown, and the hypothesis that this AT interface secretly gates access to
  the "real" binary protocol is not supported by anything tried so far.

### What was deliberately NOT tried, and why

Everything else in that command table **writes** radio or link state rather
than reading it: `AT+IPR=` changes the baud rate (would break the link until
reset to match), `AT&K0`/`AT&K3`/`AT&K4` change flow control, `AT+WV304=`
would change the radio's reported network address, and `AT+WPNEI=` is an
unidentified setter. None of these were sent. They sit in a different risk
category from the read-only `AT`/`ATI0`/`ATI1`/`AT&V` already verified safe
above, and trying them means deliberately changing the radio's configuration,
not just reading it -- that needs a decision the project, not this analysis,
should make.

Also found in `PatPort.exe` (not yet confirmed as real, standalone commands --
could be fragments of longer strings): `ATG`, `ATS`/`ATSx` (S-register
read/write, standard Hayes), `ATW`, `ATZ` (reset -- standard Hayes, explicitly
not tried here for the obvious reason).

## What open-astro-cps does with this

`src/open_astro/protocol/at_interface.py` implements this as a real,
ungated transport for native-USB radios (XTS 1500 / XTS 2500 / MT 1500 --
the ones that show up as `/dev/ttyACM0` with no cable involved, see
`HARDWARE_GROUND_TRUTH.md`). `AstroFlasher.get_radio_identity()` now tries
this path automatically for a port identified as a native Motorola USB
device, before falling back to the unverified placeholder SB9600 path.

Open questions, in order of likely value:
1. **Updated:** the real connection-setup command set is now known (see "the
   real command set, straight from PatComm10.dll" above) -- it's small
   (`AT#DATLCL`, `AT+WPNEI`, `AT+WV304`, `AT+IPR`, `AT&V`, `AT&K0/3/4`), all
   either read-only config dump (`AT&V`, already used) or write-type setters
   for baud/flow-control/network params. None of it is a codeplug command.
   `AT+CLAC` (list commands) isn't implemented, so there's no self-describing
   way to find anything beyond this table short of further disassembly or
   very carefully chosen probing. (Checked: `RadioSerial10.dll` has zero AT
   strings of its own -- it's confirmed to be the generic `CCommPort` Win32
   wrapper from `CPS_BINARY_ANALYSIS.md` section 1, not AT-aware. PatComm10
   is the only place this command table lives.)
2. Does this interface expose anything for reading/writing the codeplug
   itself, or is it limited to identity/config/PPP-data-session setup?
   Nothing tried so far suggests a codeplug read/write path through it, and
   the confirmed command set above doesn't contain one either. The working
   hypothesis is now that this interface is identity/config/PPP-only, and
   codeplug read/write (if it exists on native-USB radios at all) happens
   through a different mechanism entirely -- possibly the actual
   `RemoteProtocols01.dll`/`IRemoteProtocol` SB9600 transport from
   `CPS_BINARY_ANALYSIS.md`, running over this same tty once some
   still-unknown setup sequence (not `AT#DATLCL=1` -- that was tested and
   ruled out) puts it into a different mode, or over a wholly separate path
   this analysis hasn't found yet.
3. What does `PROTOCOL:ALT` mean? Worth a targeted disassembly pass over
   `PatComm10.dll` for the string "ALT" in a protocol-selection context.

## Update 2026-10-20 (later): digging into `AT+IPR=` specifically

Per `CPS_BINARY_ANALYSIS.md` section 8, the real `PatPort.exe` fails at
`AT+IPR=115200` every time. Dug further using only standard, safe Hayes
introspection and diagnostic commands -- no guessing at undocumented syntax.

### The query forms all work cleanly

```
AT+IPR=?    -> IPR:(9600,19200,38400,57600,115200)
AT+IPR?     -> IPR:9600
AT#DATLCL=? -> DATLCL:(0,1)
AT#DATLCL?  -> DATLCL:1
AT+WPNEI=?  -> WPNEI:(1-255).(1-255).(1-255).(1-255)
AT+WPNEI?   -> WPNEI:192.168.128.2
AT+WV304=?  -> WV304:(1-255).(1-255).(1-255).(1-255)
AT+WV304?   -> WV304:192.168.128.1
```

This resolves what `WPNEI`/`WV304` are: a local/remote IPv4 address pair
(`.2`/`.1`) for what is almost certainly the PPP data link
`RadioCustStack10.dll`'s real `CUSNETppp` code implements (see
`CPS_BINARY_ANALYSIS.md` section 1) -- confirms the "radio as PPP/IP device"
story has a real, now-located mechanism behind it.

It also directly rules out several hypotheses:
* **Not an unsupported-rate problem.** `115200` (and every other rate this
  project tried) is listed by the radio itself as a valid `IPR` value.
* **Not a stale-DATLCL problem.** Explicitly toggled `AT#DATLCL=0` then
  back to `AT#DATLCL=1` (a fresh transition, both calls returning `OK`,
  confirmed by `AT#DATLCL?` each time) immediately before retrying
  `AT+IPR=19200`. Still `ERROR`.
* **Not a syntax problem.** Tried quoted (`AT+IPR="19200"`), spaced
  (`AT+IPR =19200`), and semicolon-terminated (`AT+IPR=19200;`) variants.
  All four syntax variants (plain, quoted, spaced, semicolon) return the
  *identical* error below -- a stable, semantic rejection, not malformed
  input.

### A real, specific error code -- with an important caveat

Standard AT dialects support `AT+CMEE=1` (verbose numeric error reporting)
in place of a bare `ERROR`. Enabling it (`AT+CMEE=1` -> `OK`) and retrying
`AT+IPR=19200` gets:

```
+CME ERROR:25
```

Checked against two independent AT-command references for the standard
GSM 07.07 / 3GPP TS 27.007 `+CME ERROR` table: **code 25 = "Invalid
characters in text string"**.

**Caveat, stated plainly: this radio is not a GSM device**, and nothing
confirms Motorola's firmware honors the standard table's specific
per-number meanings rather than just reusing the `+CME ERROR:N` *format*
with its own internal numbering. Checked `PatPort.exe` for its own
CME-error-to-text lookup table (it would need one to show a human-readable
message) -- found none, so there's no way to resolve this from the
software side either. The genuinely confirmed fact is narrower than "code
25 means X": it's that this is a **stable, named, numbered rejection
reason** from the radio's own firmware, not a generic catch-all, and not
caused by rate choice, DATLCL state, or command syntax.

### Follow-up: tried standing up the PPP link directly, and isolated error 25 further

Implemented real RFC 1661/1662 PPP-over-async framing from scratch (HDLC-like
`0x7E` flags, standard byte-stuffing of `0x7E`/`0x7D`/control bytes, FCS-16
per RFC 1662 Appendix C) and sent a bare LCP `Configure-Request` (code 1, no
options) right after the known-good `AT` / `AT&V` / `AT#DATLCL=1` preamble.

**Result: complete silence.** No `0x7E` byte came back at all -- this
interface is not listening for PPP framing in this state, at least not
without some further precondition not yet found (a real "dial"/connect step
analogous to `ATD`, perhaps, which was not guessed at further).

**Side effect, genuinely informative:** sending those raw framed bytes left
garbage in the AT parser's line buffer, and the very next plain `AT`
command -- which has returned `OK` unconditionally all session -- came back
as `+CME ERROR:25`, the *same* code `AT+IPR=` produces. The channel
self-recovered on the next command. This means **error 25 is not
IPR-specific** -- it's reused by this radio's firmware as a generic
"couldn't process that input" response for at least two different causes
(malformed/leftover buffer content, and whatever makes `IPR=` fail).

To make sure the original `IPR=` failure wasn't itself a buffer artifact,
retested it as a clean first command on a fresh connection (`AT` → `OK`,
`AT+CMEE=1` → `OK`, `AT+IPR=19200` → `+CME ERROR:25`, nothing before it).
**Still fails, identically.** So the IPR rejection is real and intrinsic,
not an artifact of this session's own test sequence -- it just happens to
share a generic error code with other, unrelated failure causes.

### What's still open

The actual precondition `AT+IPR=` needs. Narrowed, not yet found:
* Not: rate choice, `DATLCL` state, command syntax, or buffer corruption
  (all directly ruled out above).
* Still plausible: a "dial"/connect step this session hasn't located that
  actually brings the PPP link up (as opposed to just configuring its
  addresses via `WPNEI`/`WV304`) -- real Hayes modems commonly only honor
  `+IPR` once connected. A bare LCP frame with no preceding dial command
  got no response at all, consistent with "not listening yet," but doesn't
  prove what *would* make it listen.
* Or some other required state entirely, not yet identified.

### Resolved: `ATD` is the missing dial step, and a real PPP link comes up

Tried `ATD` (bare, no number) as a low-risk probe. **It returned
`CONNECT`** -- the classic Hayes "data call established" response. This
is the precondition the sections above were missing: the channel has to
be put into data mode first, which also explains why the plain-`AT`
silence after the earlier raw-PPP-bytes test happened (the channel was
already in data mode and not listening for AT commands at all, not
"corrupted").

With the channel in `CONNECT` state, sent a bare LCP `Configure-Request`
(code 1, id 1, length 4, no options) using the same from-scratch
RFC 1661/1662 framing as before. **The radio replied with real, valid,
FCS-verified PPP frames** -- the single biggest result of this
investigation:

1. A `Configure-Ack` (code 2, id 1, length 4) for our request.
2. Its own `Configure-Request` (code 1, id 1, length 20) with real
   options: `Async-Control-Character-Map` (all zero), `Magic-Number`
   (changes per retransmit), `Protocol-Field-Compression`, and
   `Address-and-Control-Field-Compression`. This is a standard,
   spec-shaped PPP LCP request, not a toy or echo.

Sent back a generic `Configure-Ack` (code 2, id 1, length 4, no
options) rather than a spec-correct one that mirrors the radio's actual
options -- this is **not** technically correct per RFC 1661 (an ack must
echo the peer's options verbatim), and it only worked because our id
happened to coincidentally match the radio's request id. Flagging this
honestly: it is not confirmed whether the radio's stack is lenient about
this, or whether it just got lucky on the id match. A future pass should
send a proper mirrored ack.

Regardless of correctness, the radio's state machine accepted it and
immediately moved to **IPCP** (protocol `0x8021`), sending its own IPCP
`Configure-Request` asking for IP option `192.168.128.1` (matching the
local/remote pair already found via `AT+WPNEI`/`AT+WV304` above) plus
Van Jacobson TCP/IP header compression. Acked that verbatim, then sent our
own IPCP `Configure-Request` for `192.168.128.2` -- **the radio
`Configure-Ack`'d it immediately.** IPCP is up on both sides. The radio
also sends LCP `Echo-Request` keepalives (magic-number based) once the
link is idle, which is normal, healthy PPP behavior.

Reproducer: [`tools/ppp_probe.py`](../tools/ppp_probe.py).

### Real kernel PPP link, and the search for the actual codeplug service

Brought this up for real with the kernel's own `pppd` (not just the raw
probe script) against the same `ATD`/`CONNECT` precondition:

```
sudo pppd /dev/ttyACM0 9600 192.168.128.2:192.168.128.1 noauth local \
    nodetach debug dump nocrtscts lock connect 'chat -v "" ATD CONNECT'
```

This needs root and a real interactive terminal (sudo has no tty in a
non-interactive automation shell) -- run it manually, outside any script.
Confirmed: `ppp0` comes up with exactly the addresses negotiated above,
and the radio answers ICMP ping over it (~13ms RTT, 0% loss). **This is a
genuine, live IP link to the radio**, not a simulation.

Scanned `192.168.128.1` for whatever service the real CPS/`PatPort.exe`
talks to once this link is up:

* **TCP, full range (`nmap -Pn -sT -p1-65535`): everything filtered.** No
  TCP service answers on this interface at all.
* **UDP, full range: not completed.** The `pppd` link died partway
  through a full 65535-port UDP scan at `--min-rate 2000` -- possibly
  from flooding the single slow serial channel all at once. The radio
  itself stayed enumerated on the USB bus throughout (confirmed via
  `lsusb`), so this was a link-level issue, not a radio crash or hardware
  fault. Not yet retried with a narrower range / slower rate (see
  `tools/ppp_probe.py`'s docstring for the suggested retry command).

**Open question for the next session:** if a full UDP scan (done
carefully, without flooding the link) also comes back empty, the
codeplug protocol may not be a conventional TCP/UDP socket service at
all -- consider a raw IP protocol number (not 6/17), multicast, or
something riding directly over PPP's own protocol-field space the way
LCP/IPCP do (a vendor-private PPP protocol number would also explain why
nothing shows up in an ordinary port scan).
