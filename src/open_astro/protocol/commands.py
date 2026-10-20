"""
Command vocabulary for the real Motorola transport, as far as it is known.

Source: static analysis of the real ASTRO 25 Portable CPS R20.01.00 installer.
See docs/CPS_BINARY_ANALYSIS.md for the full writeup. Short version of what is
and isn't established here:

  CONFIRMED (via Wine's own oleaut32 parsing the DLL's embedded type library,
  and via literal ASCII strings inside the real PatPort.exe):
    * Commands are dispatched by NAME, not by a raw numeric opcode byte.
      `RemoteProtocols01.dll`'s real COM interface is:
          Send(opcodeName: BSTR, tPacket: VARIANT,
               lAddress: I4, lDeviceMajor: I4, lDeviceMinor: I4, lGroup: I4)
      i.e. every command is (name, payload, device-address-tuple).
    * Two real command names exist as literal strings in PatPort.exe:
      "EPREQ" (almost certainly Enter Programming REQuest) and "TSTMODREQ"
      (almost certainly Test Mode REQuest).
    * The payload is a VARIANT (in practice presumably a byte array), and a
      command is addressed to one device via the same four-integer tuple
      PortManager10.dll uses to enumerate devices.

  NOT CONFIRMED:
    * What bytes "EPREQ" (or anything else) actually puts on the wire. The
      string->bytes mapping was not found statically inside
      RemoteProtocols01.dll (it has no readable opcode-name strings at all),
      so it is either injected at runtime via SetConfiguration() from a data
      file, or lives somewhere this analysis hasn't reached.
    * Any command name for reading or writing codeplug memory. Nothing in the
      real installer corresponds to the old fabricated "READ_MEMORY_BLOCK
      (0x20)" / "WRITE_MEMORY_BLOCK (0x30)" / "COMMIT_CODEPLUG (0x32)" story.
      There may be real names for these operations; none has been found yet.

This module exists so the rest of open-astro-cps can be written against the
real *shape* of the protocol (name + payload + device address) instead of the
fabricated flat opcode-byte story the project started with. It does not, and
cannot yet, provide a correct wire encoding -- see protocol/framing.py and the
allow_unverified_protocol gates in serial_link.py / flasher.py for that.
"""
from typing import NamedTuple, Optional


class DeviceAddress(NamedTuple):
    """The four-integer tuple IRemoteProtocol.Send/Receive use to address a
    device on the bus. Matches PortManager10.dll's DeviceList fields
    (lAddress, lDeviceMajor, lDeviceMinor, lGroup), confirmed via the real
    typelib (see docs/CPS_BINARY_ANALYSIS.md section 6.1).

    For a radio plugged in directly over USB (as opposed to a vehicular
    multi-drop SB9600 bus with a control head, siren, etc.), all-zeros is the
    only value this project has ever had reason to try. Unconfirmed whether
    that is correct or merely inert.
    """
    address: int = 0
    device_major: int = 0
    device_minor: int = 0
    group: int = 0


# Real command names, confirmed as literal ASCII strings inside PatPort.exe.
ENTER_PROGRAMMING = "EPREQ"
TEST_MODE = "TSTMODREQ"
TRANSPARENT = "TRANSPARENT"  # pure passthrough mode, no fixed payload bytes

# Real command names + real 4-byte payloads, extracted 2026-10-20 by locating
# and disassembling PatPort.exe's own command-table function (file offset
# 0x914605-0x914870) -- see docs/CPS_BINARY_ANALYSIS.md section 7. These are
# the literal bytes that function writes for each name; NOT inferred, NOT
# placeholders. What remains unknown is the WIRE FRAME around these bytes
# (start byte, length prefix, checksum, addressing) -- RemoteProtocols01.dll's
# Send() takes this payload as a VARIANT and does its own framing internally,
# which has not been disassembled. Do not confuse these real payload bytes
# with "ready to transmit" -- they are the command's content, not its frame.
#
# RADIO_EP_REQ and SRIB_EP_REQ share opcode byte [3]=0x06 and sub-code
# byte[1]=0x12, differing only in byte[0]/[2] (0,1) vs (0x1A,0x1A) -- a
# source/destination bus-address pair, the first real evidence for the
# "SB9600 is a multi-drop bus" claim. SRIB_EP_REQ's bytes independently match
# a *second*, separately-found hardcoded "EPREQ" code path (the one logging
# "SB9600: Sending EPREQ") -- that path is specifically the cable/SRIB
# variant, not a generic "EPREQ" as this project assumed before this analysis.
REAL_COMMAND_BYTES = {
    "TSTMOD":       bytes((0x01, 0x02, 0x01, 0x40)),
    "MEMACS":       bytes((0x00, 0x09, 0x01, 0x08)),  # plausibly: open a memory-access session
    "RELEASE":      bytes((0x00, 0x00, 0x01, 0x08)),  # plausibly: close one (shares opcode 0x08 with MEMACS)
    "RADIO_EP_REQ": bytes((0x00, 0x12, 0x01, 0x06)),  # enter-programming, direct radio connection
    "SRIB_EP_REQ":  bytes((0x1A, 0x12, 0x1A, 0x06)),  # enter-programming, via SRIB cable adapter
    # TRANSPARENT: deliberately omitted -- the real code writes no fixed
    # bytes for it (true passthrough of whatever payload the caller supplies).
}

# Everything below has no real-name evidence at all. These are the project's
# own placeholder identifiers for operations we believe some real command must
# exist for (reading/writing codeplug memory), used only by the still-gated
# placeholder wire encoding in framing.py. Treat the leading UNKNOWN_ as load
# bearing: unlike ENTER_PROGRAMMING/TEST_MODE, these are not Motorola strings.
UNKNOWN_PING = "UNKNOWN_PING"
UNKNOWN_GET_RADIO_INFO = "UNKNOWN_GET_RADIO_INFO"
UNKNOWN_READ_BLOCK = "UNKNOWN_READ_BLOCK"
UNKNOWN_WRITE_BLOCK = "UNKNOWN_WRITE_BLOCK"
UNKNOWN_COMMIT = "UNKNOWN_COMMIT"
UNKNOWN_REBOOT = "UNKNOWN_REBOOT"


class CommandResponse(NamedTuple):
    """A reply to a named command. `command_name` echoes back whatever name
    resolution the placeholder transport used; it is not a real field from
    any confirmed response format."""
    command_name: str
    payload: bytes
    device: DeviceAddress
    ok: bool
