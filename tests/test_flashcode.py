import unittest
from open_astro.models import FlashcodeDecoder
from open_astro.models.flashcode import (
    luhn_check_digit, format_flashcode, verify_flashcode, set_feature,
    feature_bits, ADP_Q667, FEATURE_FLAGS, HARDWARE_GATED, PROFILES,
    software_feature_slugs,
)

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


class TestFlashcodeCheckDigit(unittest.TestCase):
    """VERIFIED-BIN Luhn mod-10 (PatPort.exe conCalculateFlashcode @0xa0b631)."""

    def test_known_fleet_pair(self):
        # Stamped on fleet radios 205CFR2930 / 205CMB2249.
        self.assertEqual(luhn_check_digit("000008002410"), "2")
        self.assertEqual(format_flashcode("000008002410"), "000008-002410-2")
        self.assertTrue(verify_flashcode("000008-002410-2"))

    def test_bad_check_digit_rejected(self):
        self.assertFalse(verify_flashcode("000008-002410-9"))

    def test_q667_adp_upgrade(self):
        # Flip nibble 8 bit 4 -> Q667; check digit recomputes to 3.
        upgraded = set_feature("000008002410", *ADP_Q667)
        self.assertEqual(upgraded, "000008006410")
        self.assertEqual(format_flashcode(upgraded), "000008-006410-3")
        self.assertIn("Q667", [f.code for f in FlashcodeDecoder.decode(format_flashcode(upgraded))])

    def test_kitchen_sink_check_digit(self):
        self.assertEqual(luhn_check_digit("FFFFFFFFFFFF"), "6")
        self.assertEqual(len(list(feature_bits("FFFFFFFFFFFF"))), 48)

    def test_roundtrip_verifies(self):
        for payload in ("000008002410", "000008006410", "FFFFFFFFFFFF", "500008000488"):
            self.assertTrue(verify_flashcode(format_flashcode(payload)))

    def test_set_feature_idempotent_and_clear(self):
        self.assertEqual(set_feature("000008002410", 8, 4), "000008006410")
        self.assertEqual(set_feature("000008006410", 8, 4), "000008006410")  # already set
        self.assertEqual(set_feature("000008006410", 8, 4, on=False), "000008002410")

    def test_bad_length_raises(self):
        with self.assertRaises(ValueError):
            luhn_check_digit("0008")
        with self.assertRaises(ValueError):
            set_feature("000008002410", 12, 4)   # nibble out of range
        with self.assertRaises(ValueError):
            set_feature("000008002410", 8, 3)    # bit not 1/2/4/8


class TestFlashcodeKnownAnswers(unittest.TestCase):
    """Known-answer vectors: real stamped flashcodes (classic numeric format),
    validated by two independent harvests (local repo/.cpg + online blankcp).

    Sources: in-repo fleet radios (stamped), AstroP25/blankcp model-name filenames
    (`MODEL_AAAAAA-BBBBBB-C`), and CPS/Depot tool codes in-repo. Every one must
    verify under the Luhn algorithm. A–F group exercises the tens-digit path.
    """
    # Real stamped / harvested codes (all must verify True).
    REAL = [
        "000008-002410-2",   # fleet 205CFR2930/205CMB2249 (stamped)
        "140001-000000-3",   # fleet 407CHT0214 radio3 (stamped)
        "180001-001002-5",   # blankcp H18KEC9PW5AN
        "100004-000002-2",   # blankcp H18KEF9PW6AN
        "500008-000482-8",   # blankcp H18UCF9PW6AN
        "500008-000488-2",   # blankcp H66KDD9PW5BN
        "100008-000480-9",   # blankcp M20KTS9PW1AN
        "500008-000480-0",   # blankcp M21URM9PW1AN
        "103040-815000-5",   # blankcp M25KTS9PW1AN
    ]
    # Codes whose payload carries hex letters A–F (tens-digit path).
    REAL_HEX = [
        "508048-00148C-0",   # blankcp M28KSS9PW1AN (C)
        "500008-00048C-7",   # CPS kitchen-sink tool code (C)
        "540408-00078C-6",   # flash_radio_adp (C)
        "540409-00078C-5",   # test_fc_clean (C)
        "54940F-E0078D-8",   # test_kitchen_sink_depot (F, E, D)
        "589108-101E87-0",   # test_flashcode_0 (E)
        "599108-101E87-9",   # test_flashcode_9 (E)
    ]
    # Fabricated / typo check digits — must be rejected (negative tests).
    BAD = [
        "500008-000488-4",   # repo template default — WRONG (correct check = 2)
        "100008-000488-4",   # comm_pair_radio2.json — WRONG
        "599108-101E87-3",   # test typo (correct = 9)
    ]

    def test_real_world_known_answers(self):
        for fc in self.REAL + self.REAL_HEX:
            with self.subTest(flashcode=fc):
                self.assertTrue(verify_flashcode(fc), f"{fc} should verify")

    def test_fabricated_check_digits_rejected(self):
        for fc in self.BAD:
            with self.subTest(flashcode=fc):
                self.assertFalse(verify_flashcode(fc), f"{fc} should NOT verify")

    def test_repo_template_default_is_corrected(self):
        # Guard against regressing the fixed seed flashcode (was -4, correct -2).
        self.assertEqual(luhn_check_digit("500008000488"), "2")

    def test_extended_alphabet_unsupported(self):
        # Newer H98/H51/M22/M25-SS/M37 families use an extended alphabet
        # (G/L/Q/R/S/Y beyond hex). The verified hex-Luhn does not cover them
        # and must raise rather than silently mis-handle.
        with self.assertRaises(ValueError):
            luhn_check_digit("9G10A8811490")


class TestFeatureFlagsAndProfiles(unittest.TestCase):
    def test_adp_is_software(self):
        self.assertEqual(FEATURE_FLAGS["adp"], ADP_Q667)
        self.assertNotIn(ADP_Q667, HARDWARE_GATED)

    def test_hardware_features_tagged(self):
        for slug in ("aes-256", "des", "hw-multikey", "multikey-48", "ask"):
            self.assertIn(FEATURE_FLAGS[slug], HARDWARE_GATED, f"{slug} should be UCM-gated")

    def test_software_slugs_exclude_gated(self):
        slugs = software_feature_slugs()
        self.assertIn("adp", slugs)
        for slug in slugs:
            self.assertNotIn(FEATURE_FLAGS[slug], HARDWARE_GATED)

    def test_recommended_profile_is_all_software(self):
        for slug in PROFILES["recommended"]:
            self.assertIn(slug, FEATURE_FLAGS)
            self.assertNotIn(FEATURE_FLAGS[slug], HARDWARE_GATED,
                             f"recommended profile should not include UCM feature {slug}")

    def test_feature_flags_cover_matrix_positions_uniquely(self):
        # No two slugs map to the same (nibble,bit); all are valid positions.
        vals = list(FEATURE_FLAGS.values())
        self.assertEqual(len(vals), len(set(vals)))
        for n, b in vals:
            self.assertTrue(0 <= n <= 11 and b in (1, 2, 4, 8))


if __name__ == "__main__":
    unittest.main()
