"""Regression test for the JSON->CSV->JSON edit workflow.

Covers the bug where a channel with no talkgroup (e.g. an analog channel) wrote
an empty Talkgroup cell that CSV import then crashed on (int('')). The
spreadsheet round-trip must preserve channels exactly, including None fields.
"""
from open_astro.models import RadioCodeplug, Zone, Channel
from open_astro.parsers import CsvParser


def _sample() -> RadioCodeplug:
    return RadioCodeplug(
        radio_model="Motorola XTS 2500 Model II",
        bandsplit="700/800 MHz (764-870 MHz)",
        zones=[
            Zone(zone_number=1, name="TEAM COMM", channels=[
                # P25 channel: has a talkgroup, NACs, no PL
                Channel(1, "P25 TALK", 851.51250, 851.51250, voice_type="ASTRO P25",
                        rx_nac="$293", tx_nac="$293", talkgroup_id=1),
                # analog channel: explicit None talkgroup (as real JSON plugs have),
                # has PL tones -- the empty-cell crash case
                Channel(2, "ANALOG", 853.01250, 853.01250, voice_type="Analog",
                        rx_pl_tone=156.7, tx_pl_tone=156.7, talkgroup_id=None),
            ]),
        ],
    )


def _key(cp):
    return [(z.name, c.channel_number, c.name, c.rx_frequency, c.tx_frequency,
             c.voice_type, c.talkgroup_id, c.rx_pl_tone, c.tx_pl_tone)
            for z in cp.zones for c in z.channels]


def test_csv_roundtrip_preserves_channels(tmp_path):
    original = _sample()
    csv_path = tmp_path / "cp.csv"
    CsvParser.export_csv(original, str(csv_path))
    restored = CsvParser.import_csv(str(csv_path), radio_model=original.radio_model)
    assert _key(restored) == _key(original)


def test_csv_import_handles_empty_talkgroup(tmp_path):
    # An analog channel has an empty Talkgroup cell; import must not raise and
    # must yield talkgroup_id == None (not a default like 1).
    csv_path = tmp_path / "cp.csv"
    CsvParser.export_csv(_sample(), str(csv_path))
    restored = CsvParser.import_csv(str(csv_path))
    analog = [c for z in restored.zones for c in z.channels if c.voice_type == "Analog"][0]
    assert analog.talkgroup_id is None
