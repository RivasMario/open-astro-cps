"""
Unit tests for AstroPppFlasher, RFC 1661 PPP framing, and TCP packet builders.
"""
import unittest
import struct
from open_astro.protocol.ppp_flasher import (
    ppp_fcs16,
    ppp_escape,
    ppp_unescape,
    parse_ppp_frames,
    ip_checksum,
    AstroPppFlasher
)


class TestAstroPppFlasher(unittest.TestCase):
    def test_ppp_fcs16(self):
        # Known test vector for FCS-16
        data = b"\xff\x03\xc0\x21\x01\x01\x00\x04"
        fcs = ppp_fcs16(data)
        self.assertEqual(len(fcs), 2)
        # Re-verifying checksum property
        self.assertIsInstance(fcs, bytes)

    def test_ppp_escape_and_unescape(self):
        # 0x7E, 0x7D, and bytes < 0x20 must be escaped
        original = bytes([0x7E, 0x01, 0x7D, 0x10, 0x41, 0x42, 0xFF])
        escaped = ppp_escape(original)
        self.assertNotIn(0x7E, escaped)
        self.assertIn(0x7D, escaped)
        unescaped = ppp_unescape(escaped)
        self.assertEqual(unescaped, original)

    def test_parse_ppp_frames(self):
        body = b"\xff\x03\xc0\x21\x01\x01\x00\x04"
        fcs = ppp_fcs16(body)
        raw_stream = b"\x7e" + ppp_escape(body + fcs) + b"\x7e"
        frames = parse_ppp_frames(raw_stream)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], body)

    def test_ip_checksum(self):
        # RFC 1071 standard IP header checksum test
        ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40, 1, 0, 64, 6, 0, bytes([192, 168, 128, 2]), bytes([192, 168, 128, 1]))
        csum = ip_checksum(ip_hdr)
        self.assertGreater(csum, 0)
        # Header with checksum included must sum to 0xFFFF or verify as 0
        ip_hdr_with_csum = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40, 1, 0, 64, 6, csum, bytes([192, 168, 128, 2]), bytes([192, 168, 128, 1]))
        self.assertEqual(ip_checksum(ip_hdr_with_csum), 0)

    def test_build_tcp_packet(self):
        flasher = AstroPppFlasher(port="COM99")
        pkt = flasher.build_tcp_packet(dst_port=8002, flags=0x02) # SYN
        self.assertEqual(len(pkt), 40) # 20 bytes IPv4 + 20 bytes TCP
        # Check source and dest IP
        self.assertEqual(pkt[12:16], bytes([192, 168, 128, 2]))
        self.assertEqual(pkt[16:20], bytes([192, 168, 128, 1]))
        # Check dest port
        dst_p = struct.unpack("!H", pkt[22:24])[0]
        self.assertEqual(dst_p, 8002)

    def test_serialize_rcmp_ish_write(self):
        from open_astro.protocol.ppp_flasher import serialize_rcmp_ish_write
        test_data = b"Hello Astro 25"
        payload = serialize_rcmp_ish_write(partition=0x80, item_id=22, offset=0, length=len(test_data), data=test_data)
        # Check header structure
        self.assertEqual(payload[0], 1) # Tag 1
        self.assertEqual(payload[1], 0x80) # Partition
        self.assertEqual(payload[2], 0) # Tag 0
        self.assertEqual(struct.unpack("!H", payload[3:5])[0], 22) # Item ID
        self.assertEqual(payload[5], 0) # Tag 0
        self.assertEqual(struct.unpack("!H", payload[6:8])[0], 0) # Offset
        self.assertEqual(payload[8], 0) # Tag 0
        self.assertEqual(struct.unpack("!H", payload[9:11])[0], len(test_data)) # Length
        self.assertTrue(payload.endswith(test_data))

    def test_serialize_rcmp_mode(self):
        from open_astro.protocol.ppp_flasher import serialize_rcmp_mode
        payload = serialize_rcmp_mode(mode=4, timeout_sec=120)
        self.assertEqual(payload[0], 1) # Tag 1
        self.assertEqual(payload[1], 4) # Mode 4 (Write Mode)
        self.assertEqual(payload[2], 0) # Tag 0
        self.assertEqual(struct.unpack("!H", payload[3:5])[0], 120) # 120 sec


if __name__ == "__main__":
    unittest.main()
