import unittest
import os
import tempfile
from open_astro.models import Channel, Zone, RadioCodeplug
from open_astro.parsers import JsonParser, CsvParser
from open_astro.protocol import PacketFramer

class TestOpenAstro(unittest.TestCase):
    def test_channel_offsets(self):
        simplex = Channel(1, "SIMP", 446.0, 446.0)
        self.assertTrue(simplex.is_simplex())
        self.assertEqual(simplex.repeater_offset(), 0.0)

        repeater = Channel(2, "RPT", 449.1, 444.1)
        self.assertFalse(repeater.is_simplex())
        self.assertEqual(repeater.repeater_offset(), -5.0)

    def test_json_roundtrip(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500",
            bandsplit="UHF 380-470 MHz",
            zones=[
                Zone(1, "TEST", [
                    Channel(1, "CH1", 446.0, 446.0, rx_pl_tone=100.0, tx_pl_tone=100.0)
                ])
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            JsonParser.save_file(cp, tmp_path)
            loaded = JsonParser.load_file(tmp_path)
            self.assertEqual(loaded.radio_model, "Motorola XTS 2500")
            self.assertEqual(len(loaded.zones), 1)
            self.assertEqual(loaded.zones[0].channels[0].rx_pl_tone, 100.0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_csv_roundtrip(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500",
            bandsplit="UHF 380-470 MHz",
            zones=[
                Zone(1, "ZONE A", [
                    Channel(1, "ALPHA", 446.0, 446.0, voice_type="Analog", rx_pl_tone=67.0, tx_pl_tone=67.0),
                    Channel(2, "DIGI", 441.0, 441.0, voice_type="ASTRO P25", rx_nac="$293", tx_nac="$293")
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
            self.assertEqual(loaded.zones[0].channels[0].rx_pl_tone, 67.0)
            self.assertEqual(loaded.zones[0].channels[1].voice_type, "ASTRO P25")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_packet_framer(self):
        # Build packet: Start=0x05, Length=2 (opcode + 1 byte), Opcode=0x14, Payload=b'\x01'
        packet = PacketFramer.build_packet(opcode=0x14, payload=b"\x01")
        self.assertEqual(packet[0], 0x05)
        parsed = PacketFramer.parse_packet(packet)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["opcode"], 0x14)
        self.assertEqual(parsed["payload"], b"\x01")

if __name__ == "__main__":
    unittest.main()
