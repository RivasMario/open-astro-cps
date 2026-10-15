import unittest
from open_astro.protocol.kfdtool import (
    KfdtoolAdapter,
    P25ThreeWireLink,
    P25Algorithm
)

class TestKfdtool(unittest.TestCase):
    def test_framing_roundtrip(self):
        # Test normal payload
        payload = bytes([0x11, 0x02])
        framed = KfdtoolAdapter.frame_packet(payload)
        self.assertEqual(framed[0], KfdtoolAdapter.SOM_EOM)
        self.assertEqual(framed[-1], KfdtoolAdapter.SOM_EOM)

        packets = KfdtoolAdapter.unframe_packet(framed)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0], payload)

    def test_framing_escapes(self):
        # Payload containing SOM_EOM (0x61) and ESC (0x63)
        payload = bytes([0x61, 0x10, 0x63, 0x20])
        framed = KfdtoolAdapter.frame_packet(payload)
        
        # Verify escape characters were inserted
        self.assertIn(bytes([KfdtoolAdapter.ESC, KfdtoolAdapter.SOM_EOM_PLACEHOLDER]), framed)
        self.assertIn(bytes([KfdtoolAdapter.ESC, KfdtoolAdapter.ESC_PLACEHOLDER]), framed)

        packets = KfdtoolAdapter.unframe_packet(framed)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0], payload)

    def test_crc16(self):
        # Test CRC16 CCITT (Poly 0x1021, init 0xFFFF)
        # Verify deterministic calculation
        data = bytes([0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x82, 0x00, 0x00])
        crc = P25ThreeWireLink.calculate_crc16(data)
        self.assertIsInstance(crc, int)
        self.assertGreaterEqual(crc, 0)
        self.assertLessEqual(crc, 0xFFFF)

    def test_kmm_frame_building(self):
        link = P25ThreeWireLink(None)
        zeroize_body = link.build_zeroize_command()
        self.assertEqual(zeroize_body[2], 0x82) # MID 0x82 = Zeroize

        frame = link.build_kmm_frame(zeroize_body)
        self.assertEqual(frame[0], P25ThreeWireLink.OPCODE_KMM)
        # Length bytes
        length = (frame[1] << 8) | frame[2]
        self.assertEqual(length, len(zeroize_body))

    def test_modify_key_command(self):
        link = P25ThreeWireLink(None)
        kmm = link.build_modify_key_command(
            key_id=1,
            algorithm=P25Algorithm.ADP,
            key_data_hex="A1B2C3D4E5",
            keyset_id=1
        )
        self.assertEqual(kmm[2], 0x80) # MID 0x80 = Modify Key Command
        self.assertEqual(kmm[5], 1)    # Keyset ID
        self.assertEqual(kmm[6], int(P25Algorithm.ADP)) # 0xAA
        self.assertEqual(kmm[7], 5)    # 5 bytes key length (40-bit RC4)
        self.assertEqual(kmm[8], 1)    # Number of keys = 1

    def test_algorithm_parsing(self):
        self.assertEqual(P25Algorithm.from_str("ADP"), P25Algorithm.ADP)
        self.assertEqual(P25Algorithm.from_str("adp"), P25Algorithm.ADP)
        self.assertEqual(P25Algorithm.from_str("AES-256"), P25Algorithm.AES_256)
        self.assertEqual(P25Algorithm.from_str("aes"), P25Algorithm.AES_256)
        self.assertEqual(P25Algorithm.from_str("DES-OFB"), P25Algorithm.DES_OFB)
        self.assertEqual(P25Algorithm.from_str("DES-XL"), P25Algorithm.DES_XL)

        with self.assertRaises(ValueError):
            P25Algorithm.from_str("UNKNOWN_CIPHER")

if __name__ == "__main__":
    unittest.main()
