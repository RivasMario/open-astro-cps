"""
Motorola ASTRO 25 / SB9600 Serial Packet Framing and Checksum utilities.
"""
from typing import List, Optional

START_BYTE = 0x05
ESCAPE_BYTE = 0x10

class PacketFramer:
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """Calculate 8-bit two's complement checksum (standard Motorola SB9600)."""
        total = sum(data) & 0xFF
        return (-total) & 0xFF

    @staticmethod
    def build_packet(opcode: int, payload: bytes = b"") -> bytes:
        """
        Builds a standard packet: [START] [LEN] [OPCODE] [PAYLOAD...] [CHECKSUM]
        """
        length = len(payload) + 1  # opcode + payload
        packet_body = bytes([length, opcode]) + payload
        checksum = PacketFramer.calculate_checksum(packet_body)
        return bytes([START_BYTE]) + packet_body + bytes([checksum])

    @staticmethod
    def parse_packet(raw_bytes: bytes) -> Optional[dict]:
        """
        Validates and unpacks a framed packet.
        """
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
        return {
            "opcode": opcode,
            "payload": payload,
            "raw": raw_bytes[:length + 3]
        }
