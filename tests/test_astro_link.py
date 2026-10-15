import unittest
from open_astro.protocol.astro_link import AstroRadioLink
from open_astro.protocol.framing import PacketFramer

class TestAstroRadioLink(unittest.TestCase):
    def test_link_constants(self):
        self.assertEqual(AstroRadioLink.OPCODE_STATUS_PING, 0x14)
        self.assertEqual(AstroRadioLink.OPCODE_PRGM_REQ, 0x01)
        self.assertEqual(AstroRadioLink.OPCODE_RADIO_INFO, 0x11)
        self.assertEqual(AstroRadioLink.OPCODE_RESTART, 0x15)

    def test_packet_framer_sb9600(self):
        # Ping packet: 0x05, length=1, opcode=0x14, checksum
        pkt = PacketFramer.build_packet(0x14)
        self.assertEqual(pkt[0], 0x05)
        self.assertEqual(pkt[1], 1)
        self.assertEqual(pkt[2], 0x14)
        # Checksum is (-sum) & 0xFF
        expected_cs = (- (1 + 0x14)) & 0xFF
        self.assertEqual(pkt[3], expected_cs)

        parsed = PacketFramer.parse_packet(pkt)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["opcode"], 0x14)
        self.assertEqual(parsed["payload"], b"")

if __name__ == "__main__":
    unittest.main()
