import unittest
import os
import tempfile
from open_astro.models import Channel, Zone, RadioCodeplug, EncryptionKey
from open_astro.parsers import JsonParser, CsvParser
from open_astro.protocol import PacketFramer, AstroFlasher

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

class MockRadioSerialLink:
    def __init__(self):
        self.sent_packets = []
        self.responses = []

    def ping(self):
        return True

    def send_command(self, opcode: int, payload: bytes = b""):
        self.sent_packets.append((opcode, payload))
        if opcode == 0x14:  # GET_RADIO_INFO
            return {"opcode": 0x15, "payload": b"H46KDH9PW7BN\x00422CHB0123\x00500008-000488-4\x00R20.01.00\x00"}
        elif opcode == 0x10:  # ENTER_PROGRAMMING
            return {"opcode": 0x01, "payload": b""}
        elif opcode == 0x11:  # EXIT_PROGRAMMING
            return {"opcode": 0x01, "payload": b""}
        elif opcode == 0x20:  # READ_MEMORY_BLOCK
            # Return status 0x00 + 256 dummy bytes
            chunk_len = payload[3] if len(payload) > 3 else 256
            return {"opcode": 0x21, "payload": bytes([0x00]) + (b"\xAA" * chunk_len)}
        elif opcode == 0x30:  # WRITE_MEMORY_BLOCK
            return {"opcode": 0x31, "payload": bytes([0x00])}
        elif opcode == 0x32:  # COMMIT_CODEPLUG
            return {"opcode": 0x33, "payload": bytes([0x00])}
        return {"opcode": 0x01, "payload": b""}

    def reboot_radio(self):
        self.sent_packets.append((0x11, bytes([0x01])))
        return True

class TestAstroFlasher(unittest.TestCase):
    def test_boundary_lock(self):
        mock_link = MockRadioSerialLink()
        flasher = AstroFlasher(mock_link)
        # Attempt to write into Tuning Partition (0x0000_4000)
        with self.assertRaises(ValueError):
            flasher.write_codeplug(b"\x00" * 512, target_bank=0x0000_4000,
                                   allow_unverified_protocol=True)

    def test_write_and_commit(self):
        mock_link = MockRadioSerialLink()
        flasher = AstroFlasher(mock_link)
        test_data = b"\x12\x34\x56\x78" * 64  # 256 bytes
        
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_backup = flasher.backup_tuning_partition
            flasher.backup_tuning_partition = lambda: os.path.join(tmpdir, "backup.bin")
            
            success = flasher.write_codeplug(test_data, target_bank=0x0022_0000,
                                             allow_unverified_protocol=True)
            self.assertTrue(success)

            # Check that 0x10 (enter prog), 0x30 (write), 0x32 (commit), and 0x11 (reboot) were sent
            opcodes_sent = [op for op, _ in mock_link.sent_packets]
            self.assertIn(0x10, opcodes_sent)
            self.assertIn(0x30, opcodes_sent)
            self.assertIn(0x32, opcodes_sent)
            self.assertIn(0x11, opcodes_sent)

class TestUnverifiedProtocolGate(unittest.TestCase):
    def test_write_blocked_without_opt_in(self):
        """The invented-opcode write path must refuse to run by default."""
        flasher = AstroFlasher(MockRadioSerialLink())
        with self.assertRaises(RuntimeError) as ctx:
            flasher.write_codeplug(b"\x00" * 256, target_bank=0x0022_0000)
        self.assertIn("unverified", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
