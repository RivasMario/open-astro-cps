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
