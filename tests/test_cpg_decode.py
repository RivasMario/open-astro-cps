"""Tests for the typed .cpg -> RadioCodeplug decoder.

The record-table decoders are tested on synthetic payloads built to the
calibrated layout (docs/CPG_FILE_FORMAT.md + cpg_decode.py docstring), plus an
end-to-end decode of a real backup when one is present in backups/.
"""
import os

import pytest

from open_astro.parsers.cpg_decode import (
    CpgDecoder,
    TAG_CHANNEL_NAMES,
    TAG_CHANNEL_FREQS,
    FREQ_REC_LEN,
    _band_from_model,
    _band_from_freqs,
    _resolve_bandsplit,
)

BACKUP = os.path.join(
    os.path.dirname(__file__), "..", "backups", "205CFR2930.cpg"
)


def _name_table(names):
    body = b"".join(n.encode("latin1").ljust(17, b"\x00") for n in names)
    return b"\x00\x00\x00\x00" + len(names).to_bytes(2, "big") + body


def _freq_rec(rx_hz, tx_hz, nac_rx, nac_tx):
    rec = bytearray(FREQ_REC_LEN)
    rec[6:8] = nac_rx.to_bytes(2, "big")
    rec[8:10] = nac_tx.to_bytes(2, "big")
    rec[12:16] = (rx_hz // 5).to_bytes(4, "big")
    rec[16:20] = (tx_hz // 5).to_bytes(4, "big")
    return bytes(rec)


def _freq_table(recs):
    return b"\x00\x00\x00\x00" + len(recs).to_bytes(2, "big") + b"".join(recs)


def test_name_table_decodes_slots():
    names = CpgDecoder._name_table(_name_table(["CHAN 1", "CHAN 2"]))
    assert names == ["CHAN 1", "CHAN 2"]


def test_freq_record_decodes_freq_and_nac():
    rec = _freq_rec(852_062_500, 807_062_500, 0x293, 0x293)
    d = CpgDecoder._decode_freq_rec(rec)
    assert d["rx_frequency"] == 852.0625
    assert d["tx_frequency"] == 807.0625
    assert d["rx_nac"] == "$293"
    assert d["tx_nac"] == "$293"


def test_zeroed_record_is_rejected():
    assert CpgDecoder._decode_freq_rec(bytes(FREQ_REC_LEN)) is None


def test_tag_constants():
    assert TAG_CHANNEL_NAMES == 0x0FFF
    assert TAG_CHANNEL_FREQS == 0x0FFD


def _ish_list(names, stride=17):
    body = b"".join(n.encode("latin1").ljust(stride, b"\x00") for n in names)
    return (b"\x00\x00" + stride.to_bytes(2, "big") + b"\x00\x32"
            + len(names).to_bytes(2, "big") + body)


def test_ish_name_list_decodes_header():
    # Header differs from the 0x0FFF table: stride @ [2:4], count @ [6:8].
    out = CpgDecoder._ish_name_list(_ish_list(["TG 00002"]))
    assert out == ["TG 00002"]


def test_ish_name_list_multi():
    out = CpgDecoder._ish_name_list(_ish_list(["SEATTLE", "EPSCA", "KCVC"]))
    assert out == ["SEATTLE", "EPSCA", "KCVC"]


def test_channel_ref_decodes_personality_pointer():
    pl = bytes.fromhex("0001002300ff000a0ffd0002000001")
    ref = CpgDecoder._channel_ref(pl)
    assert ref == {"ref_tag": 0x0FFD, "ref_inst": 2}


@pytest.mark.skipif(not os.path.exists(BACKUP), reason="real .cpg backup not present")
def test_decode_real_backup_205cfr2930():
    try:
        import olefile  # noqa: F401
    except ImportError:
        pytest.skip("olefile not installed")
    with CpgDecoder(BACKUP) as dec:
        cp = dec.decode()
    assert cp.serial_number == "205CFR2930"
    assert cp.total_channels() == 2
    ch = cp.zones[0].channels
    assert ch[0].name == "CHAN 1"
    assert ch[0].rx_frequency == 852.0625
    assert ch[1].rx_frequency == 853.0625
    assert all(c.rx_nac == "$293" for c in ch)
    # ISH name-list tables: 205CFR2930 has one talkgroup "TG 00002".
    assert any(t.name == "TG 00002" and t.tg_id == 2 for t in cp.talkgroups)


def test_band_from_model_letter():
    # XTS 2500 band letter at model index 3: K/Q/S/U/W.
    assert _band_from_model("H46KDF9PW6BN")[0] == "VHF (136-174 MHz)"
    assert _band_from_model("H46QDH9PW7BN")[0] == "UHF Range 1 (380-470 MHz)"
    assert _band_from_model("H46SDC9PW5AN")[0] == "UHF Range 2 (450-520 MHz)"
    assert _band_from_model("H46UCF9PW6BN")[0] == "700/800 MHz (764-870 MHz)"
    assert _band_from_model("H46WCD9PW5BN")[0] == "900 MHz (896-941 MHz)"


def test_band_from_model_rejects_unknown():
    assert _band_from_model("") is None
    assert _band_from_model("XYZ123") is None
    assert _band_from_model("H46ZDC9PW5AN") is None  # no 'Z' band


def test_band_from_freqs_fallback():
    assert _band_from_freqs([154.4, 155.58, 158.94])[0] == "VHF (136-174 MHz)"
    assert _band_from_freqs([852.0625, 853.0625])[0] == "700/800 MHz (764-870 MHz)"
    assert _band_from_freqs([]) is None


def test_resolve_bandsplit_prefers_model_over_freqs():
    # Model letter wins even if a stray decoded freq lands in another band.
    assert _resolve_bandsplit("H46KDF9PW6BN", [764.0]) == "VHF (136-174 MHz)"
    # No model -> fall back to frequencies.
    assert _resolve_bandsplit("", [852.0625]) == "700/800 MHz (764-870 MHz)"
    # Neither -> Unknown, never a wrong hardcoded default.
    assert _resolve_bandsplit("", []) == "Unknown"


BACKUP_407 = os.path.join(os.path.dirname(__file__), "..", "backups", "407CHT0214.cpg")


@pytest.mark.skipif(not os.path.exists(BACKUP_407), reason="407CHT0214 backup not present")
def test_decode_all_channels_407():
    try:
        import olefile  # noqa: F401
    except ImportError:
        pytest.skip("olefile not installed")
    with CpgDecoder(BACKUP_407) as dec:
        cp = dec.decode()
    assert cp.serial_number == "407CHT0214"
    assert cp.bandsplit == "VHF (136-174 MHz)"
    # Every one of the 48 channels now resolves a frequency (was 3 before).
    chans = [c for z in cp.zones for c in z.channels]
    assert len(chans) == 48
    assert all(c.rx_frequency for c in chans)
    # Spot-check against published NIFOG national VHF interop frequencies.
    by_name = {c.name: c for z in cp.zones for c in z.channels}
    assert by_name["V FIRE 23"].rx_frequency == 154.295
    assert by_name["V MED 29"].rx_frequency == 155.3475
    assert by_name["V LAW 31"].rx_frequency == 155.475
    assert by_name["MARINE 16"].rx_frequency == 156.8
    # Repeater pair keeps split rx/tx; LAW is 158.940 / 154.400.
    assert by_name["LAW"].rx_frequency == 158.94 and by_name["LAW"].tx_frequency == 154.4
    # CTCSS: NIFOG national interop channels carry 156.7 Hz PL (validated).
    assert by_name["V TAC 11"].rx_pl_tone == 156.7
    assert by_name["V FIRE 23"].tx_pl_tone == 156.7
    assert by_name["LAW"].rx_pl_tone == 210.7  # local repeater, different PL
    # DPL channels have no CTCSS tone but a (best-effort) DPL code.
    assert by_name["OPS 5"].rx_pl_tone is None and by_name["OPS 5"].rx_dpl_code is not None
    # Carrier-squelch channels: no tone, modulation left Unknown (not "digital").
    assert by_name["MRA"].rx_pl_tone is None and by_name["MRA"].voice_type == "Unknown"
    assert by_name["V TAC 11"].voice_type == "Analog"
