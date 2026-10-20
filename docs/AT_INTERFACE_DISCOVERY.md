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

## What open-astro-cps does with this

`src/open_astro/protocol/at_interface.py` implements this as a real,
ungated transport for native-USB radios (XTS 1500 / XTS 2500 / MT 1500 --
the ones that show up as `/dev/ttyACM0` with no cable involved, see
`HARDWARE_GROUND_TRUTH.md`). `AstroFlasher.get_radio_identity()` now tries
this path automatically for a port identified as a native Motorola USB
device, before falling back to the unverified placeholder SB9600 path.

Open questions, in order of likely value:
1. What is the full command set? `AT+CLAC` (list commands) isn't
   implemented, so there's no self-describing way to enumerate it --
   command names would need to come from disassembling `PatComm10.dll`/
   `RadioSerial10.dll` (now that `PatPort.exe` likely talks AT commands
   to this radio class specifically) or from careful, read-only-only probing.
2. Does this interface expose anything for reading/writing the codeplug
   itself, or is it limited to identity/config/PPP-data-session setup?
   Nothing tried so far suggests a codeplug read/write path through it.
3. What does `PROTOCOL:ALT` mean? Worth a targeted disassembly pass over
   `PatComm10.dll` for the string "ALT" in a protocol-selection context.
