import os
import csv
import tempfile
import unittest
import xml.etree.ElementTree as ET

from open_astro.models import RadioCodeplug, Zone, Channel
from open_astro.exporters import export_dsdfme, export_sdrtrunk


def _fixture():
    return RadioCodeplug(
        radio_model="Motorola XTS 2500 Model II",
        bandsplit="700/800 MHz",
        serial_number="205CFR2930",
        zones=[
            Zone(zone_number=1, name="TEAM OPS", channels=[
                Channel(1, "OPEN ASTRO", 851.51250, 851.51250,
                        voice_type="ASTRO P25", rx_nac="$293", tx_nac="$293", talkgroup_id=1),
                Channel(2, "TEAM ANALOG", 853.01250, 853.01250,
                        voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7),
                Channel(3, "ADP SECURE", 852.01250, 852.01250,
                        voice_type="ASTRO P25", talkgroup_id=2,
                        secure_strapping="Secure", key_id=1),
            ]),
        ],
    )


class TestDsdFmeExport(unittest.TestCase):
    def test_channel_map_is_hz_positional(self):
        with tempfile.TemporaryDirectory() as d:
            paths = export_dsdfme(_fixture(), d)
            rows = list(csv.reader(open(paths["channel_map"], newline="")))
        self.assertEqual(rows[0], ["Channel", "Frequency"])  # label row (DSD-FME skips it)
        # 3 channels, col0 = index, col1 = Hz
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1], ["1", "851512500"])   # 851.51250 MHz -> Hz
        self.assertEqual(rows[2][1], "853012500")
        self.assertEqual(rows[3][1], "852012500")

    def test_group_list_only_digital_tgs(self):
        with tempfile.TemporaryDirectory() as d:
            paths = export_dsdfme(_fixture(), d)
            rows = list(csv.reader(open(paths["group"], newline="")))
        body = rows[1:]
        tgs = {r[0]: (r[1], r[2]) for r in body}
        self.assertEqual(set(tgs), {"1", "2"})          # analog channel excluded
        self.assertEqual(tgs["1"][0], "A")              # clear
        self.assertEqual(tgs["2"][0], "DE")             # secure -> encrypted mode

    def test_csv_name_sanitized(self):
        cp = _fixture()
        cp.zones[0].channels[0].name = "BAD,NAME\nLINE"
        with tempfile.TemporaryDirectory() as d:
            paths = export_dsdfme(cp, d)
            # the comma/newline must not create extra columns/rows
            rows = list(csv.reader(open(paths["group"], newline="")))
        self.assertTrue(all(len(r) == 3 for r in rows))


class TestSdrTrunkExport(unittest.TestCase):
    def test_playlist_structure(self):
        with tempfile.TemporaryDirectory() as d:
            path = export_sdrtrunk(_fixture(), d)
            tree = ET.parse(path)
        root = tree.getroot()
        self.assertEqual(root.tag, "playlist")
        self.assertEqual(root.get("version"), "4")

        channels = root.findall("channel")
        self.assertEqual(len(channels), 3)
        # P25 channel -> P25_PHASE1 decode + Hz frequency
        p25 = channels[0]
        self.assertEqual(p25.find("decode_configuration").get("type"), "P25_PHASE1")
        self.assertEqual(p25.find("source_configuration/frequency").text, "851512500")
        self.assertEqual(p25.find("alias_list_name").text, "205CFR2930")
        # analog channel -> NBFM
        self.assertEqual(channels[1].find("decode_configuration").get("type"), "NBFM")

    def test_talkgroup_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            path = export_sdrtrunk(_fixture(), d)
            root = ET.parse(path).getroot()
        aliases = root.findall("alias")
        self.assertEqual(len(aliases), 2)               # 2 unique digital TGs
        ids = [a.find("id") for a in aliases]
        self.assertTrue(all(i.get("type") == "TALKGROUP" for i in ids))
        self.assertTrue(all(i.get("protocol") == "APCO25" for i in ids))
        self.assertEqual({i.get("value") for i in ids}, {"1", "2"})


if __name__ == "__main__":
    unittest.main()
