import unittest
import os
import tempfile
from open_astro.models import Channel, Zone, RadioCodeplug, EncryptionKey
from open_astro.parsers import JsonParser, CsvParser
from open_astro.protocol import PacketFramer, AstroFlasher
from open_astro.protocol import at_interface

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
        packet = PacketFramer.build_packet("UNKNOWN_GET_RADIO_INFO", payload=b"\x01")
        self.assertEqual(packet[0], 0x05)
        parsed = PacketFramer.parse_packet(packet)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["command_name"], "UNKNOWN_GET_RADIO_INFO")
        self.assertEqual(parsed["payload"], b"\x01")

    def test_packet_framer_unknown_name_rejected(self):
        with self.assertRaises(KeyError):
            PacketFramer.build_packet("NOT_A_REAL_COMMAND")

class MockRadioSerialLink:
    """Mock for the named-command transport shape (see protocol/commands.py).
    Response opcodes are this test's own placeholders, same as framing.py's --
    they do not represent anything confirmed about the real radio."""
    def __init__(self):
        self.sent_commands = []  # list of (command_name, payload)
        self.responses = []
        self.port = None  # no real port -> AstroFlasher skips the AT interface path
        self.connection = None

    def ping(self, allow_unverified_protocol: bool = False):
        return True

    def send_command(self, command_name: str, payload: bytes = b"", device=None,
                     allow_unverified_protocol: bool = False):
        self.sent_commands.append((command_name, payload))
        if command_name == "UNKNOWN_GET_RADIO_INFO":
            return {"command_name": command_name, "is_ack": False,
                    "payload": b"H46KDH9PW7BN\x00422CHB0123\x00500008-000488-4\x00R20.01.00\x00"}
        elif command_name == "EPREQ":
            return {"command_name": command_name, "is_ack": True, "payload": b""}
        elif command_name == "UNKNOWN_READ_BLOCK":
            chunk_len = payload[3] if len(payload) > 3 else 256
            return {"command_name": command_name, "is_ack": False,
                    "payload": bytes([0x00]) + (b"\xAA" * chunk_len)}
        elif command_name == "UNKNOWN_WRITE_BLOCK":
            return {"command_name": command_name, "is_ack": False, "payload": bytes([0x00])}
        elif command_name == "UNKNOWN_COMMIT":
            return {"command_name": command_name, "is_ack": False, "payload": bytes([0x00])}
        return {"command_name": command_name, "is_ack": True, "payload": b""}

    def reboot_radio(self, allow_unverified_protocol: bool = False):
        self.sent_commands.append(("UNKNOWN_REBOOT", bytes([0x01])))
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
            flasher.backup_tuning_partition = lambda allow_unverified_protocol=False: os.path.join(tmpdir, "backup.bin")

            success = flasher.write_codeplug(test_data, target_bank=0x0022_0000,
                                             allow_unverified_protocol=True)
            self.assertTrue(success)

            # Check that EPREQ (enter programming), the write, the commit, and the
            # reboot were all sent, by name.
            names_sent = [name for name, _ in mock_link.sent_commands]
            self.assertIn("EPREQ", names_sent)
            self.assertIn("UNKNOWN_WRITE_BLOCK", names_sent)
            self.assertIn("UNKNOWN_COMMIT", names_sent)
            self.assertIn("UNKNOWN_REBOOT", names_sent)

class FakeATConnection:
    """Fake pyserial connection replaying the exact transcript measured
    against a real XTS 2500 on 2026-10-20 (docs/AT_INTERFACE_DISCOVERY.md).
    Not a simulation of the protocol in general -- just this one real
    exchange, so the parser is tested against real bytes."""
    _RESPONSES = {
        "AT": b"\r\nOK\r\n",
        "ATI1": b"\r\nMotorola System Release 6.0 Radio\r\n\r\nOK\r\n",
        "AT&V": (
            b"\r\nCARRIER:9600\r\n\r\nPROTOCOL:ALT\r\n\r\nCOMPRESSION:NONE\r\n\r\n"
            b"FLOW:K3\r\n\r\nWV304:192.168.128.1\r\n\r\nRADIO:XTS 2500\r\n\r\n"
            b"MODEL:H46UCF9PW6AN\r\n\r\nSERIAL:205CFR2930\r\n\r\n"
            b"PORT:SIDE CONNECTOR AS USB\r\n\r\nSECURE:R000000\r\n\r\n"
            b"CPS:HARDWARE FLOW CONTROL\r\n\r\nOK\r\n"
        ),
    }

    def __init__(self):
        self._pending = b""
        self.in_waiting = 0

    def reset_input_buffer(self):
        self._pending = b""

    def write(self, data: bytes):
        cmd = data.decode("ascii").strip()
        self._pending = self._RESPONSES.get(cmd, b"\r\nERROR\r\n")
        self.in_waiting = len(self._pending)

    def flush(self):
        pass

    def read(self, n):
        out, self._pending = self._pending[:n], self._pending[n:]
        self.in_waiting = len(self._pending)
        return out


class TestATInterface(unittest.TestCase):
    """Tests the parser against the real captured transcript, not a model of
    the protocol -- see FakeATConnection."""

    def test_ping(self):
        self.assertTrue(at_interface.ping(FakeATConnection()))

    def test_get_radio_identity(self):
        info = at_interface.get_radio_identity(FakeATConnection())
        self.assertEqual(info["RADIO"], "XTS 2500")
        self.assertEqual(info["MODEL"], "H46UCF9PW6AN")
        self.assertEqual(info["SERIAL"], "205CFR2930")
        self.assertEqual(info["WV304"], "192.168.128.1")

    def test_get_firmware_banner(self):
        banner = at_interface.get_firmware_banner(FakeATConnection())
        self.assertEqual(banner, "Motorola System Release 6.0 Radio")

    def test_identity_raises_on_no_response(self):
        class DeadConnection(FakeATConnection):
            def write(self, data):
                self._pending = b""  # radio never answers

        with self.assertRaises(at_interface.ATInterfaceError):
            at_interface.get_radio_identity(DeadConnection())


class TestUnverifiedProtocolGate(unittest.TestCase):
    def test_write_blocked_without_opt_in(self):
        """The invented-opcode write path must refuse to run by default."""
        flasher = AstroFlasher(MockRadioSerialLink())
        with self.assertRaises(RuntimeError) as ctx:
            flasher.write_codeplug(b"\x00" * 256, target_bank=0x0022_0000)
        self.assertIn("unverified", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
