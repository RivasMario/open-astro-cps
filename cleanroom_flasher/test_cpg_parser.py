import unittest
import os
from open_astro.parsers.cpg_parser import CpgArchive, AdkLcgCipher, rc4_crypt

class TestCpgParser(unittest.TestCase):
    def setUp(self):
        self.radio1_cpg = os.path.join(os.path.dirname(__file__), "..", "backups", "Radio1_205CMB2249_codeplug.cpg")
        self.radio3_cpg = os.path.join(os.path.dirname(__file__), "..", "backups", "205CFR2930.cpg")

    def test_rc4_crypt_symmetry(self):
        key = b"TEST_KEY_12345"
        data = b"HELLO MOTOROLA ASTRO 25"
        encrypted = rc4_crypt(key, data)
        self.assertNotEqual(encrypted, data)
        decrypted = rc4_crypt(key, encrypted)
        self.assertEqual(decrypted, data)

    def test_adk_lcg_step(self):
        # next = (seed * 85 + 25) & 0xFF
        seed = 0
        next_seed = AdkLcgCipher.lcg_step(seed)
        self.assertEqual(next_seed, 25)
        next_next = AdkLcgCipher.lcg_step(next_seed)
        self.assertEqual(next_next, (25 * 85 + 25) & 0xFF)

    def test_radio1_cpg_load_and_decrypt(self):
        if not os.path.exists(self.radio1_cpg):
            self.skipTest("Radio 1 backup cpg not present")
        with CpgArchive(self.radio1_cpg) as archive:
            self.assertEqual(archive.model_number, "H46UCF9PW6BN")
            self.assertEqual(archive.serial_number, "205CMB2249")
            self.assertEqual(archive.agency_tag, "LURS")
            self.assertEqual(archive.encryption_type, 1) # CFhAdkSdkCrypto
            self.assertEqual(len(archive.session_key_9), 9)
            self.assertEqual(len(archive.rc4_key_16), 16)
            self.assertGreater(len(archive.decrypted_streams), 100)

            # Check Strm_1 decryption
            strm1 = archive.get_stream("Strm_1")
            self.assertIsNotNone(strm1)
            # Record signature magic (Motorola ADK item magic: 0x6d 0x35 0xf1)
            self.assertEqual(strm1[2:5], b"\x6d\x35\xf1")

    def test_radio3_cpg_load_and_decrypt(self):
        if not os.path.exists(self.radio3_cpg):
            self.skipTest("Radio 3 backup cpg not present")
        with CpgArchive(self.radio3_cpg) as archive:
            self.assertEqual(archive.model_number, "H46UCF9PW6AN")
            self.assertEqual(archive.serial_number, "205CFR2930")
            self.assertEqual(archive.encryption_type, 1)
            self.assertGreater(len(archive.decrypted_streams), 100)

    def test_find_streams_and_patch_in_place(self):
        if not os.path.exists(self.radio3_cpg):
            self.skipTest("Radio 3 backup cpg not present")
        import tempfile
        with CpgArchive(self.radio3_cpg) as archive:
            matches = archive.find_streams_containing(b"\x6d\x35\xf1")
            self.assertGreater(len(matches), 50)

            # Test modifying a stream in-place
            orig_strm1 = archive.get_stream("Strm_1")
            modified_payload = bytearray(orig_strm1)
            modified_payload[10] ^= 0xAA
            archive.set_stream("Strm_1", bytes(modified_payload))

            with tempfile.NamedTemporaryFile(suffix=".cpg", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                archive.patch_in_place(tmp_path)
                with CpgArchive(tmp_path) as patched_archive:
                    reloaded_strm1 = patched_archive.get_stream("Strm_1")
                    self.assertEqual(reloaded_strm1, bytes(modified_payload))
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
