import copy
import unittest

from open_astro.parsers.button_edit import (
    ButtonPatcher, ButtonPatchError, resolve_function, resolve_position,
    FUNCTION_TOKENS, BUTTON_POSITIONS, TAG_BTN_SHORT, TAG_BTN_LONG, HEADER_LEN,
)

# 7-button conventional table as flashed to 205CFR2930 (hardware-verified):
# header 00000001 0010 0007 + tokens 2c 1e 2b 29 1c 1a 8e
SHORT_HEX = "00000001001000072c1e2b291c1a8e"
LONG_HEX = "00000001001000072c1e2b291c1a8e"


def make_objects():
    return [
        {"tag": TAG_BTN_SHORT, "instance": 0, "partition": 0x80, "payload": bytes.fromhex(SHORT_HEX)},
        {"tag": TAG_BTN_LONG, "instance": 0, "partition": 0x80, "payload": bytes.fromhex(LONG_HEX)},
    ]


class TestResolvers(unittest.TestCase):
    def test_function_by_name(self):
        self.assertEqual(resolve_function("monitor"), 0x2b)
        self.assertEqual(resolve_function("scan"), 0x1e)
        self.assertEqual(resolve_function("light"), 0x2c)

    def test_function_by_hex(self):
        self.assertEqual(resolve_function("0x2b"), 0x2b)
        self.assertEqual(resolve_function("2b"), 0x2b)

    def test_function_unknown_raises(self):
        with self.assertRaises(ButtonPatchError):
            resolve_function("teleport")

    def test_position_and_aliases(self):
        self.assertEqual(resolve_position("side3")[1], 2)
        self.assertEqual(resolve_position("orange")[1], 3)
        self.assertEqual(resolve_position("top")[1], 3)       # alias
        self.assertEqual(resolve_position("purple")[1], 0)    # alias -> side1

    def test_position_unknown_raises(self):
        with self.assertRaises(ButtonPatchError):
            resolve_position("pinky")


class TestButtonPatcher(unittest.TestCase):
    def test_count_and_current(self):
        p = ButtonPatcher(make_objects())
        self.assertEqual(p.button_count(), 7)
        self.assertEqual(p.current_tokens("short"),
                         [0x2c, 0x1e, 0x2b, 0x29, 0x1c, 0x1a, 0x8e])

    def test_patch_side3_to_scan_short(self):
        objs = make_objects()
        p = ButtonPatcher(objs)
        p.patch_button("side3", "scan", press="short")
        self.assertEqual(p.current_tokens("short")[2], 0x1e)           # index 2 -> scan
        self.assertEqual(p.current_tokens("long")[2], 0x2b)            # long untouched
        edits = p.generate_edits(objs)
        self.assertEqual(len(edits), 1)
        self.assertTrue(edits[0].startswith("80:0016:0:"))

    def test_patch_both_press(self):
        objs = make_objects()
        p = ButtonPatcher(objs)
        p.patch_button("side2", "emergency", press="both")
        self.assertEqual(p.current_tokens("short")[1], 0x48)
        self.assertEqual(p.current_tokens("long")[1], 0x48)
        self.assertEqual(len(p.generate_edits(objs)), 2)              # both tables changed

    def test_orange_to_unprogrammed(self):
        objs = make_objects()
        p = ButtonPatcher(objs)
        p.patch_button("orange", "unprogrammed")
        self.assertEqual(p.current_tokens("short")[3], 0x26)

    def test_purple_backlight_warning(self):
        p = ButtonPatcher(make_objects())
        notes = p.patch_button("side1", "scan")
        self.assertTrue(any("backlight" in n.lower() for n in notes))

    def test_no_edit_when_unchanged(self):
        objs = make_objects()
        p = ButtonPatcher(objs)
        p.patch_button("side1", "light")   # already 0x2c at index 0
        self.assertEqual(p.generate_edits(objs), [])

    def test_index_out_of_range_raises(self):
        # 4-button table: count 4, front-select is index 6 -> out of range
        objs = [{"tag": TAG_BTN_SHORT, "instance": 0, "partition": 0x80,
                 "payload": bytes.fromhex("00000001001000042c1e2b29")}]
        p = ButtonPatcher(objs)
        with self.assertRaises(ButtonPatchError):
            p.patch_button("front-select", "scan")

    def test_missing_table_raises(self):
        with self.assertRaises(ButtonPatchError):
            ButtonPatcher([]).button_count()

    def test_set_button(self):
        objs = make_objects()
        p = ButtonPatcher(objs)
        p.set_button("orange", "monitor", long_press=False)
        self.assertEqual(p.current_tokens("short")[3], 0x2b)
        self.assertEqual(p.current_tokens("long")[3], 0x29)

        p.set_button("orange", "scan", long_press=True)
        self.assertEqual(p.current_tokens("long")[3], 0x1e)

        edits = p.generate_edits()
        self.assertEqual(len(edits), 2)

    def test_from_file_and_save_json(self):
        import tempfile
        import json
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            json.dump({"objects": [{"tag": TAG_BTN_SHORT, "instance": 0, "partition": 0x80, "payload": SHORT_HEX}]}, tf)
            tf_path = tf.name

        try:
            p = ButtonPatcher.from_file(tf_path)
            self.assertEqual(p.button_count(), 7)
            p.set_button("orange", "monitor")

            with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as out_tf:
                out_path = out_tf.name

            try:
                p.save_json(out_path)
                with open(out_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.assertIn("objects", saved)
                self.assertEqual(saved["objects"][0]["tag"], TAG_BTN_SHORT)
                self.assertIsInstance(saved["objects"][0]["payload"], str)
            finally:
                import os
                if os.path.exists(out_path):
                    os.remove(out_path)
        finally:
            import os
            if os.path.exists(tf_path):
                os.remove(tf_path)


if __name__ == "__main__":
    unittest.main()
