"""Tests for P25 / Type II trunking decoder (0x0FD0..0x0FDF).

Verifies:
1. 800 MHz channel ID <-> Frequency math (6.25 kHz step grid).
2. Synthetic control-channel, talkgroup, and system table decoding.
3. End-to-end decoding against backups/Radio1_205CMB2249_codeplug.cpg.
"""
from pathlib import Path
import pytest

from open_astro.parsers.cpg_parser import CpgParser
from open_astro.parsers.trunking_decode import (
    BASE_FREQ_HZ,
    STEP_SIZE_HZ,
    TrunkingControlChannel,
    TrunkingDecoder,
    TrunkingSystem,
    TrunkingTalkgroup,
    channel_id_to_freq_hz,
    channel_id_to_freq_mhz,
    freq_hz_to_channel_id,
)

BACKUP_RADIO1 = Path(__file__).resolve().parents[1] / "backups" / "Radio1_205CMB2249_codeplug.cpg"


def test_freq_conversion_math():
    """Verify channel ID to frequency calculations on verified King County channels."""
    # 0x033a = 826 -> 856.1625 MHz
    assert channel_id_to_freq_hz(826) == 856_162_500
    assert pytest.approx(channel_id_to_freq_mhz(826)) == 856.1625

    # 0x05e6 = 1510 -> 860.4375 MHz
    assert channel_id_to_freq_hz(1510) == 860_437_500
    assert pytest.approx(channel_id_to_freq_mhz(1510)) == 860.4375

    # 0x06ee = 1774 -> 862.0875 MHz
    assert channel_id_to_freq_hz(1774) == 862_087_500
    assert pytest.approx(channel_id_to_freq_mhz(1774)) == 862.0875


def test_freq_roundtrip():
    """Verify round-trip frequency conversion."""
    for ch in [0, 100, 826, 1510, 2500, 4000]:
        hz = channel_id_to_freq_hz(ch)
        assert freq_hz_to_channel_id(hz) == ch


def test_invalid_freq_unaligned():
    """Verify error on frequency not on 6.25 kHz grid."""
    with pytest.raises(ValueError):
        freq_hz_to_channel_id(851_000_100)  # 100 Hz offset is unaligned


def test_decode_synthetic_control_channels():
    """Verify decoding synthetic 0x0FD2 buffer."""
    # Header: 4 bytes zero + count=2 (u16)
    # Rec 1: flags=0x00, rx=826, tx=826
    # Rec 2: flags=0x80, rx=1510, tx=1510
    raw = (
        b"\x00\x00\x00\x00\x00\x02"
        b"\x00\x03\x3a\x03\x3a"
        b"\x80\x05\xe6\x05\xe6"
    )
    ccs = TrunkingDecoder.decode_control_channels(raw)
    assert len(ccs) == 2
    assert ccs[0].flags == 0x00
    assert ccs[0].rx_channel_id == 826
    assert pytest.approx(ccs[0].rx_freq_mhz) == 856.1625

    assert ccs[1].flags == 0x80
    assert ccs[1].rx_channel_id == 1510
    assert pytest.approx(ccs[1].rx_freq_mhz) == 860.4375


def test_decode_synthetic_talkgroups():
    """Verify decoding synthetic 0x0FDF buffer."""
    # Header: 4 bytes zero + count=2 (u16)
    # Rec 1: flags=0x00, tgid=1188 (0x04a4), prio=0x0000
    # Rec 2: flags=0x00, tgid=930 (0x03a2), prio=0x0001
    raw = (
        b"\x00\x00\x00\x00\x00\x02"
        b"\x00\x04\xa4\x00\x00"
        b"\x00\x03\xa2\x00\x01"
    )
    tgs = TrunkingDecoder.decode_talkgroups(raw)
    assert len(tgs) == 2
    assert tgs[0].tgid == 1188
    assert tgs[0].priority_flags == 0
    assert tgs[1].tgid == 930
    assert tgs[1].priority_flags == 1


def test_decode_synthetic_system_names_and_ids():
    """Verify decoding synthetic 0x0FDC and 0x0FDD tables."""
    # 0x0FDC: 4 bytes marker, name_len=50, count=2
    # Rec 1: "SEATTLE" padded to 16 bytes + \x00
    # Rec 2: "EPSCA" padded to 16 bytes + \x00
    name_buf = (
        b"\x00\x00\x00\x11\x00\x32\x00\x02"
        b"SEATTLE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"EPSCA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    names = TrunkingDecoder.decode_system_names(name_buf)
    assert names == ["SEATTLE", "EPSCA"]

    # 0x0FDD: 4 bytes zero, count=2
    # Rec 1: sys_id=1, 7 bytes zero
    # Rec 2: sys_id=3, 7 bytes zero
    id_buf = (
        b"\x00\x00\x00\x00\x00\x02"
        b"\x00\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x03\x00\x00\x00\x00\x00\x00\x00"
    )
    ids = TrunkingDecoder.decode_system_ids(id_buf)
    assert ids == [1, 3]


def test_real_codeplug_trunking_decode():
    """End-to-end verification against real Seattle / King County codeplug backup."""
    if not BACKUP_RADIO1.exists():
        pytest.skip("backups/Radio1_205CMB2249_codeplug.cpg not present")

    cpg = CpgParser.load_file(str(BACKUP_RADIO1))
    systems = TrunkingDecoder.decode_all_systems(cpg.objects)

    assert len(systems) == 15
    assert systems[0].name == "SEATTLE"
    assert systems[0].system_id == 1
    assert len(systems[0].control_channels) == 15

    # Check first control channel of SEATTLE system: 860.4375 MHz
    assert pytest.approx(systems[0].control_channels[0].rx_freq_mhz) == 860.4375

    # Check EPSCA system
    assert systems[2].name == "EPSCA"
    assert systems[2].system_id == 3

    # Check Master Fleet talkgroup list (0x0FDF:0)
    master_tg_data = cpg.objects.get((128, 0x0FDF, 0))
    assert master_tg_data is not None
    talkgroups = TrunkingDecoder.decode_talkgroups(master_tg_data)
    assert len(talkgroups) == 28

    # First few known Seattle talkgroups
    tgids = [tg.tgid for tg in talkgroups]
    assert 1188 in tgids
    assert 930 in tgids
    assert 1192 in tgids
    assert 1742 in tgids
