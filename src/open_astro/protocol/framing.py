"""
PLACEHOLDER wire encoding for named commands.

This is NOT a confirmed Motorola wire format. It was authored from reasoning
about how a Motorola-style protocol might look, before the real CPS installer
had been read. Static disassembly of the real transport DLL
(RemoteProtocols01.dll, see docs/CPS_BINARY_ANALYSIS.md) found zero use of the
START_BYTE this module sends, anywhere in that DLL's code. One real-world test
against a connected XTS 2500 confirms the predictable consequence: the radio
times out and never responds -- not harmful, just useless.

It is kept, gated behind allow_unverified_protocol everywhere it's used,
because the project needs *some* concrete byte encoding to exercise the rest
of the stack (serial_link.py, flasher.py) against until the real one is
captured. Treat every byte value in here as a placeholder to be deleted, not
as a fact about the radio.

See protocol/commands.py for the real, confirmed command vocabulary (names,
not opcodes) this placeholder maps onto.
"""
from typing import Optional

START_BYTE = 0x05

# Maps real/placeholder command names (protocol/commands.py) to a small
# integer, purely so this placeholder framing has *something* to put in the
# OPCODE byte. These integers are this project's own invention, not anything
# read from Motorola's code.
_NAME_TO_PLACEHOLDER_OPCODE = {
    "UNKNOWN_PING": 0x00,
    "UNKNOWN_GET_RADIO_INFO": 0x14,
    "EPREQ": 0x10,
    "TSTMODREQ": 0x12,
    "UNKNOWN_READ_BLOCK": 0x20,
    "UNKNOWN_WRITE_BLOCK": 0x30,
    "UNKNOWN_COMMIT": 0x32,
    "UNKNOWN_REBOOT": 0x11,
}
_PLACEHOLDER_OPCODE_TO_NAME = {v: k for k, v in _NAME_TO_PLACEHOLDER_OPCODE.items()}
_ACK_OPCODE = 0x01


class PacketFramer:
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """Placeholder 8-bit two's complement sum. Not confirmed as anything
        the radio actually computes -- see module docstring."""
        total = sum(data) & 0xFF
        return (-total) & 0xFF

    @staticmethod
    def build_packet(command_name: str, payload: bytes = b"") -> bytes:
        """Builds a placeholder packet: [START] [LEN] [OPCODE] [PAYLOAD...] [CHECKSUM]."""
        opcode = _NAME_TO_PLACEHOLDER_OPCODE.get(command_name)
        if opcode is None:
            raise KeyError(
                f"No placeholder opcode registered for command {command_name!r}. "
                f"Add one to _NAME_TO_PLACEHOLDER_OPCODE in framing.py, or use a "
                f"name from protocol/commands.py."
            )
        length = len(payload) + 1  # opcode + payload
        packet_body = bytes([length, opcode]) + payload
        checksum = PacketFramer.calculate_checksum(packet_body)
        return bytes([START_BYTE]) + packet_body + bytes([checksum])

    @staticmethod
    def parse_packet(raw_bytes: bytes) -> Optional[dict]:
        """Validates and unpacks a placeholder-framed packet."""
        if len(raw_bytes) < 4:
            return None
        if raw_bytes[0] != START_BYTE:
            return None
        length = raw_bytes[1]
        if len(raw_bytes) < length + 3:
            return None

        body = raw_bytes[1:1 + length + 1]
        expected_checksum = raw_bytes[1 + length + 1]

        if PacketFramer.calculate_checksum(body) != expected_checksum:
            return None

        opcode = body[1]
        payload = body[2:]
        command_name = _PLACEHOLDER_OPCODE_TO_NAME.get(opcode)
        is_ack = opcode == _ACK_OPCODE
        return {
            "opcode": opcode,
            "command_name": command_name,
            "is_ack": is_ack,
            "payload": payload,
            "raw": raw_bytes[:length + 3],
        }
