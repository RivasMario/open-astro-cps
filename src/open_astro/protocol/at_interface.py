"""
AT command interface for native-USB Motorola radios (XTS 1500 / XTS 2500 /
MT 1500 -- the ones that enumerate as USB CDC-ACM, see serial_link.py and
docs/HARDWARE_GROUND_TRUTH.md).

Unlike the rest of protocol/, this is REAL and VERIFIED, not a placeholder.
The radio's own USB descriptor declares interface protocol "AT-commands
(v.25ter)" -- a standard Hayes/AT modem command interface -- and it was
measured working directly against a connected XTS 2500 on 2026-10-20 with
nothing but plain pyserial. See docs/AT_INTERFACE_DISCOVERY.md for the full
transcript and reasoning.

Only read-only, universally-standard query commands are implemented here
(AT, ATI0, ATI1, ATI2, ATI3, ATI4, AT&V). Nothing that writes configuration, resets the radio,
or changes state (ATZ, AT&F, AT&W, AT+IPR, ...) is implemented, and none
should be added without a specific, verified reason to believe it's safe --
see the safety note in docs/AT_INTERFACE_DISCOVERY.md.
"""
import time
from typing import Dict, Optional


class ATInterfaceError(Exception):
    pass


def _send_and_read(connection, command: str, settle_time: float = 0.4) -> str:
    """Writes one AT command line and reads back whatever arrives within
    settle_time. Not framed/length-delimited -- this interface's responses
    are plain CRLF-terminated text, so a short fixed settle window is the
    simplest thing that has actually been observed to work."""
    connection.reset_input_buffer()
    connection.write(command.encode("ascii") + b"\r\n")
    connection.flush()
    time.sleep(settle_time)
    raw = connection.read(connection.in_waiting or 1024)
    return raw.decode("latin1", errors="replace")


def ping(connection) -> bool:
    """Sends the bare AT command. Returns True if the radio answers OK."""
    resp = _send_and_read(connection, "AT")
    return "OK" in resp


def get_radio_identity(connection) -> Dict[str, str]:
    """
    Sends AT&V (the standard, read-only "view current configuration"
    command) and parses the radio's real identity/config block.

    Verified response shape from a real XTS 2500 (docs/AT_INTERFACE_DISCOVERY.md):
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
        OK

    Returns a dict of every KEY:VALUE line found. Raises ATInterfaceError if
    the radio doesn't answer OK at all (wrong port, not this radio family).
    """
    resp = _send_and_read(connection, "AT&V", settle_time=0.6)
    if "OK" not in resp:
        raise ATInterfaceError(
            f"Radio did not respond OK to AT&V (got: {resp!r}). "
            f"This radio may not support the AT interface, or the port is wrong."
        )

    info: Dict[str, str] = {}
    for line in resp.splitlines():
        line = line.strip()
        if not line or line in ("OK", "ERROR"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            info[key.strip()] = value.strip()
    return info


def get_firmware_banner(connection) -> Optional[str]:
    """Sends ATI1, which returns a one-line firmware/model banner (verified:
    "Motorola System Release 6.0 Radio" on a real XTS 2500). Returns None if
    the radio doesn't answer OK."""
    resp = _send_and_read(connection, "ATI1")
    if "OK" not in resp:
        return None
    for line in resp.splitlines():
        line = line.strip()
        if line and line != "OK":
            return line
    return None


def get_host_version(connection) -> Optional[str]:
    """Sends ATI2, which returns host processor firmware version (e.g., 'Host Version: R09.00.41')."""
    resp = _send_and_read(connection, "ATI2")
    if "OK" not in resp:
        return None
    for line in resp.splitlines():
        line = line.strip()
        if line and line != "OK":
            return line
    return None


def get_dsp_version(connection) -> Optional[str]:
    """Sends ATI3, which returns DSP firmware version (e.g., 'DSP Version: R16.00.01')."""
    resp = _send_and_read(connection, "ATI3")
    if "OK" not in resp:
        return None
    for line in resp.splitlines():
        line = line.strip()
        if line and line != "OK":
            return line
    return None
