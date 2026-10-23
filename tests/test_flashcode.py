import unittest
from open_astro.models import FlashcodeDecoder

class TestFlashcode(unittest.TestCase):
    def test_decode_standard_astro25(self):
        flashcode = "500008-000488-4"
        features = FlashcodeDecoder.decode(flashcode)
        codes = [f.code for f in features]
        self.assertIn("Q806/G806", codes)
        self.assertIn("Q53", codes)
        self.assertIn("H869", codes)
        self.assertIn("Q507", codes)

    def test_decode_real_radio_flashcode(self):
        # Connected XTS 2500 radio 205CFR2930 flashcode
        flashcode = "000008-002410-2"
        features = FlashcodeDecoder.decode(flashcode)
        codes = [f.code for f in features]
        self.assertIn("Q53", codes)   # Front Panel Programming
        self.assertIn("Q888", codes)  # Software System Key
        self.assertIn("H869", codes)  # AES-256 Encryption
        self.assertIn("Q362", codes)  # ASTRO 25 TDMA Phase 2

    def test_invalid_flashcode(self):
        with self.assertRaises(ValueError):
            FlashcodeDecoder.decode("INVALID")

if __name__ == "__main__":
    unittest.main()
