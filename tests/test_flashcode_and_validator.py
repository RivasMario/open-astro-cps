import unittest
from open_astro.models import (
    RadioCodeplug,
    Zone,
    Channel,
    EncryptionKey,
    FlashcodeDecoder,
    CodeplugValidator
)

class TestFlashcodeAndValidator(unittest.TestCase):
    def test_flashcode_decoder(self):
        flashcode = "500008-000488-4"
        features = FlashcodeDecoder.decode(flashcode)
        codes = [f.code for f in features]
        self.assertIn("Q806/G806", codes)
        self.assertIn("Q53", codes)
        self.assertIn("H869", codes)
        self.assertIn("Q507", codes)

    def test_flashcode_decoder_invalid(self):
        with self.assertRaises(ValueError):
            FlashcodeDecoder.decode("INVALID")

    def test_validator_valid_codeplug(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500 Model II",
            bandsplit="700/800 MHz (764-870 MHz)",
            encryption_keys=[
                EncryptionKey(key_id=1, name="TEAM_ADP", algorithm="ADP", key_data="A1B2C3D4E5")
            ],
            zones=[
                Zone(1, "SECURE", [
                    Channel(1, "CLEAR", 851.5125, 851.5125, voice_type="ASTRO P25"),
                    Channel(2, "ENC", 852.0125, 852.0125, voice_type="ASTRO P25", secure_strapping="Secure", key_id=1),
                    Channel(3, "PS MONITOR", 851.8875, 851.8875, voice_type="ASTRO P25", rx_only=True)
                ])
            ]
        )
        issues = CodeplugValidator.validate(cp)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertEqual(len(errors), 0)

    def test_validator_detects_public_safety_violation(self):
        # A control channel without rx_only=True
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500",
            bandsplit="700/800 MHz (764-870 MHz)",
            zones=[
                Zone(1, "SAFETY", [
                    Channel(1, "PSERN CTRL 1", 851.8875, 851.8875, rx_only=False)
                ])
            ]
        )
        issues = CodeplugValidator.validate(cp)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("SAFETY VIOLATION" in e.message for e in errors))

    def test_validator_detects_unregistered_key(self):
        cp = RadioCodeplug(
            radio_model="Motorola XTS 2500",
            bandsplit="700/800 MHz (764-870 MHz)",
            encryption_keys=[], # Empty keys table
            zones=[
                Zone(1, "SECURE", [
                    Channel(1, "ENC", 852.0125, 852.0125, secure_strapping="Secure", key_id=99)
                ])
            ]
        )
        issues = CodeplugValidator.validate(cp)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertTrue(any("Key ID 99" in e.message for e in errors))

if __name__ == "__main__":
    unittest.main()
