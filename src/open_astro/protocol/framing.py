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

    # Authentic Motorola SB9600 CRC-8 Lookup Table (Polynomial 0xF3 / 0x1F reflected)
    SB9600_CRC_TABLE = [
        0x00, 0x99, 0xAD, 0x34, 0xC5, 0x5C, 0x68, 0xF1, 0x15, 0x8C, 0xB8, 0x21,
        0xD0, 0x49, 0x7D, 0xE4, 0x2A, 0xB3, 0x87, 0x1E, 0xEF, 0x76, 0x42, 0xDB,
        0x3F, 0xA6, 0x92, 0x0B, 0xFA, 0x63, 0x57, 0xCE, 0x54, 0xCD, 0xF9, 0x60,
        0x91, 0x08, 0x3C, 0xA5, 0x41, 0xD8, 0xEC, 0x75, 0x84, 0x1D, 0x29, 0xB0,
        0x7E, 0xE7, 0xD3, 0x4A, 0xBB, 0x22, 0x16, 0x8F, 0x6B, 0xF2, 0xC6, 0x5F,
        0xAE, 0x37, 0x03, 0x9A, 0xA8, 0x31, 0x05, 0x9C, 0x6D, 0xF4, 0xC0, 0x59,
        0xBD, 0x24, 0x10, 0x89, 0x78, 0xE1, 0xD5, 0x4C, 0x82, 0x1B, 0x2F, 0xB6,
        0x47, 0xDE, 0xEA, 0x73, 0x97, 0x0E, 0x3A, 0xA3, 0x52, 0xCB, 0xFF, 0x66,
        0xFC, 0x65, 0x51, 0xC8, 0x39, 0xA0, 0x94, 0x0D, 0xE9, 0x70, 0x44, 0xDD,
        0x2C, 0xB5, 0x81, 0x18, 0xD6, 0x4F, 0x7B, 0xE2, 0x13, 0x8A, 0xBE, 0x27,
        0xC3, 0x5A, 0x6E, 0xF7, 0x06, 0x9F, 0xAB, 0x32, 0xCF, 0x56, 0x62, 0xFB,
        0x0A, 0x93, 0xA7, 0x3E, 0xDA, 0x43, 0x77, 0xEE, 0x1F, 0x86, 0xB2, 0x2B,
        0xE5, 0x7C, 0x48, 0xD1, 0x20, 0xB9, 0x8D, 0x14, 0xF0, 0x69, 0x5D, 0xC4,
        0x35, 0xAC, 0x98, 0x01, 0x9B, 0x02, 0x36, 0xAF, 0x5E, 0xC7, 0xF3, 0x6A,
        0x8E, 0x17, 0x23, 0xBA, 0x4B, 0xD2, 0xE6, 0x7F, 0xB1, 0x28, 0x1C, 0x85,
        0x74, 0xED, 0xD9, 0x40, 0xA4, 0x3D, 0x09, 0x90, 0x61, 0xF8, 0xCC, 0x55,
        0x67, 0xFE, 0xCA, 0x53, 0xA2, 0x3B, 0x0F, 0x96, 0x72, 0xEB, 0xDF, 0x46,
        0xB7, 0x2E, 0x1A, 0x83, 0x4D, 0xD4, 0xE0, 0x79, 0x88, 0x11, 0x25, 0xBC,
        0x58, 0xC1, 0xF5, 0x6C, 0x9D, 0x04, 0x30, 0xA9, 0x33, 0xAA, 0x9E, 0x07,
        0xF6, 0x6F, 0x5B, 0xC2, 0x26, 0xBF, 0x8B, 0x12, 0xE3, 0x7A, 0x4E, 0xD7,
        0x19, 0x80, 0xB4, 0x2D, 0xDC, 0x45, 0x71, 0xE8, 0x0C, 0x95, 0xA1, 0x38,
        0xC9, 0x50, 0x64, 0xFD
    ]

    @classmethod
    def sb9600_crc(cls, data: bytes) -> int:
        """Calculate 8-bit Motorola SB9600 CRC over 4-byte message body."""
        crc = 0
        for b in data:
            crc = cls.SB9600_CRC_TABLE[(crc ^ b) & 0xFF]
        return crc

    @classmethod
    def build_sb9600_packet(cls, address: int, param1: int, param2: int, function: int) -> bytes:
        """Build 5-byte fixed SB9600 bus frame: [ADDR, PARAM1, PARAM2, FUNC, CRC]."""
        body = bytes([address & 0xFF, param1 & 0xFF, param2 & 0xFF, function & 0xFF])
        return body + bytes([cls.sb9600_crc(body)])

    @staticmethod
    def sbep_checksum(data: bytes) -> int:
        """Calculate SBEP 8-bit one's complement checksum: 0xFF - (sum(data) & 0xFF)."""
        return (0xFF - (sum(data) & 0xFF)) & 0xFF

    @classmethod
    def build_sbep_packet(cls, opcode: int, data: Optional[bytes] = None) -> bytes:
        """
        Build Motorola SBEP variable-length packet:
        - Opcode 0x10 (Exit SBEP, data=None): b'\\xf0\\x10'
        - Opcode 0x11 (Read Memory): [0xF5, 0x11, count, addr_hi, addr_mid, addr_lo, csum]
        - Opcode 0x17 (Write Memory): [hdr, 0x17, (ext_len...), addr_hi, addr_mid, addr_lo, payload..., csum]
        """
        if data is None:
            length = 0
        else:
            length = len(data) + 1

        hdr = (min(0x0F, opcode) << 4) | min(0x0F, length)
        pkt = bytearray([hdr])
        if opcode >= 0x0F:
            pkt.append(opcode & 0xFF)
        if length >= 0x0F:
            pkt.append((length >> 8) & 0xFF)
            pkt.append(length & 0xFF)
        if data is not None:
            pkt.extend(data)
            pkt.append(cls.sbep_checksum(pkt))
        return bytes(pkt)

    @classmethod
    def parse_sbep_packet(cls, raw_bytes: bytes) -> Optional[dict]:
        """Parse and validate a received SBEP packet."""
        if not raw_bytes:
            return None
        msn = (raw_bytes[0] >> 4) & 0x0F
        lsn = raw_bytes[0] & 0x0F

        if msn < 0x0F and lsn < 0x0F:
            if len(raw_bytes) < 1:
                return None
            opcode = msn
            length = lsn
            data_start = 1
        elif msn == 0x0F and lsn < 0x0F:
            if len(raw_bytes) < 2:
                return None
            opcode = raw_bytes[1]
            length = lsn
            data_start = 2
        elif msn < 0x0F and lsn == 0x0F:
            if len(raw_bytes) < 3:
                return None
            opcode = msn
            length = (raw_bytes[1] << 8) | raw_bytes[2] if len(raw_bytes) >= 3 else raw_bytes[1]
            data_start = 3
        else:
            if len(raw_bytes) < 4:
                return None
            opcode = raw_bytes[1]
            length = (raw_bytes[2] << 8) | raw_bytes[3]
            data_start = 4

        total_len = data_start + length
        if len(raw_bytes) < total_len:
            return None

        packet_slice = raw_bytes[:total_len]
        if length > 0:
            if (sum(packet_slice) & 0xFF) != 0xFF:
                return None
            payload = packet_slice[data_start:total_len - 1]
            checksum = packet_slice[total_len - 1]
        else:
            payload = b""
            checksum = 0

        return {
            "opcode": opcode,
            "payload": payload,
            "checksum": checksum,
            "raw": packet_slice
        }
