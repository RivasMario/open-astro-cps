import unittest
import os
import tempfile
from open_astro.models import Channel, Zone, RadioCodeplug, EncryptionKey
from open_astro.parsers import JsonParser, CsvParser
from open_astro.protocol import PacketFramer

class TestOpenAstro(unittest.TestCase):
    def test_channel_offsets(self):
        simplex = Channel(1, "SIMP", 851.5125, 851.5125)
        self.assertTrue(simplex.is_simplex())
        self.assertEqual(simplex.repeater_offset(), 0.0)

        repeater = Channel(2, "RPT", 851.0125, 806.0125)
        self.assertFalse(repeater.is_simplex())
        self.assertEqual(repeater.repeater_offset(), -45.0)

    def test_encryption_models(self):
        key = EncryptionKey(key_id=1, name="TEAM_KEY", algorithm="ADP", key_data="A1B2C3D4E5")
        self.assertEqual(key.key_id, 1)
        self.assertEqual(key.algorithm, "ADP")

        ch = Channel(1, "ENC_CH", 852.0, 852.0, secure_strapping="Secure", key_id=1, key_name="TEAM_KEY")
        self.assertEqual(ch.secure_strapping, "Secure")
        self.assertEqual(ch.key_id, 1)

    def test_json_roundtrip(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500 Model II",
            bandsplit="700/800 MHz (764-870 MHz)",
            encryption_keys=[
                EncryptionKey(key_id=1, name="TEAM_ADP", algorithm="ADP", key_data="A1B2C3D4E5")
            ],
            zones=[
                Zone(1, "TEAM", [
                    Channel(1, "SECURE1", 851.5125, 851.5125, voice_type="ASTRO P25", secure_strapping="Secure", key_id=1, key_name="TEAM_ADP")
                ])
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            JsonParser.save_file(cp, tmp_path)
            loaded = JsonParser.load_file(tmp_path)
            self.assertEqual(loaded.radio_model, "Motorola XTS 2500 Model II")
            self.assertEqual(len(loaded.encryption_keys), 1)
            self.assertEqual(loaded.encryption_keys[0].name, "TEAM_ADP")
            self.assertEqual(loaded.zones[0].channels[0].secure_strapping, "Secure")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_csv_roundtrip(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500",
            bandsplit="700/800 MHz",
            zones=[
                Zone(1, "ZONE A", [
                    Channel(1, "ALPHA", 851.5125, 851.5125, voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7),
                    Channel(2, "DIGI", 852.0125, 852.0125, voice_type="ASTRO P25", secure_strapping="Secure", key_id=1, key_name="TEAM1", rx_nac="$293", tx_nac="$293")
                ])
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            CsvParser.export_csv(cp, tmp_path)
            loaded = CsvParser.import_csv(tmp_path)
            self.assertEqual(len(loaded.zones), 1)
            self.assertEqual(len(loaded.zones[0].channels), 2)
            self.assertEqual(loaded.zones[0].channels[0].rx_pl_tone, 156.7)
            self.assertEqual(loaded.zones[0].channels[1].secure_strapping, "Secure")
            self.assertEqual(loaded.zones[0].channels[1].key_id, 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_packet_framer(self):
        packet = PacketFramer.build_packet(opcode=0x14, payload=b"\x01")
        self.assertEqual(packet[0], 0x05)
        parsed = PacketFramer.parse_packet(packet)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["opcode"], 0x14)
        self.assertEqual(parsed["payload"], b"\x01")

if __name__ == "__main__":
    unittest.main()
