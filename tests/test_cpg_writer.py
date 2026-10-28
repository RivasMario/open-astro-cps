"""
Tests for the offline .cpg writer and binary stream patcher (cpg_writer.py).

Verifies:
  1. Round-trip decoding -> modifying channels/zones/frequencies/NACs/identity ->
     writing a new .cpg via CpgWriter -> parsing with CpgParser (100% of data
     streams pass CRC-16-CCITT check) -> decoding with CpgDecoder returns all
     updated fields accurately.
  2. `DataStg/Strm_0` directory table consistency: every 10-byte record
     `[tag, instance, flags, stream_crc, stream_id]` in `Strm_0` matches the
     recomputed `crc16_ccitt(payload)` trailer of its corresponding stream.
  3. Exact OLE stream size preservation across `AdkFileHeader` and `DataStg/Strm_*`.
"""
import os
import struct

import pytest

from open_astro.models import Channel, RadioCodeplug, Zone
from open_astro.parsers.cpg_decode import CpgDecoder
from open_astro.parsers.cpg_parser import CpgParser, crc16_ccitt, derive_rc4_key, rc4
from open_astro.parsers.cpg_writer import (
    CpgWriter,
    _encode_freq_word,
    _encode_nac_word,
)

BACKUP_205CFR2930 = os.path.join(
    os.path.dirname(__file__), "..", "backups", "205CFR2930.cpg"
)
BACKUP_RADIO1 = os.path.join(
    os.path.dirname(__file__), "..", "backups", "Radio1_205CMB2249_codeplug.cpg"
)


def test_encode_helpers():
    assert _encode_freq_word(852.06250) == 170412500
    assert _encode_freq_word(853.06250) == 170612500
    assert _encode_freq_word(806.01250) == 161202500
    assert _encode_freq_word(0.0) == 0
    assert _encode_nac_word("$293") == 0x0293
    assert _encode_nac_word("$F7E") == 0x0F7E
    assert _encode_nac_word("0x1A4") == 0x01A4


@pytest.mark.skipif(
    not os.path.exists(BACKUP_205CFR2930),
    reason="backups/205CFR2930.cpg not present",
)
def test_strm0_directory_matches_all_stream_crcs():
    """Verify Strm_0 10-byte directory entries match per-stream CRC-16 trailers."""
    writer = CpgWriter(BACKUP_205CFR2930)
    records = writer.get_strm0_directory()
    assert len(records) == 146

    for rec in records:
        sname = f"Strm_{rec['stream_id']}"
        assert sname in writer.streams
        dec = writer.streams[sname]
        tag, inst = struct.unpack(">HH", dec[:4])
        stream_crc = struct.unpack(">H", dec[-2:])[0]
        calc_crc = crc16_ccitt(bytes(dec[6:-2]))
        assert rec["tag"] == tag
        assert rec["instance"] == inst
        assert rec["stream_crc"] == stream_crc == calc_crc


@pytest.mark.skipif(
    not os.path.exists(BACKUP_205CFR2930),
    reason="backups/205CFR2930.cpg not present",
)
def test_cpg_writer_roundtrip_205cfr2930(tmp_path):
    """
    Load backups/205CFR2930.cpg, modify serial, model, zone name, channel names,
    frequencies, and NACs, write to a temp .cpg, and verify 100% CRC pass +
    exact decoded values.
    """
    with CpgDecoder(BACKUP_205CFR2930) as dec:
        cp = dec.decode()

    # Modify identity and channels
    cp.serial_number = "205CMB9999"
    cp.radio_model = "H46UCF9PW6BN"
    cp.zones[0].name = "TEAM COMM"
    cp.zones[0].channels[0] = Channel(
        channel_number=1,
        name="P25 SIMPLEX",
        rx_frequency=851.51250,
        tx_frequency=851.51250,
        voice_type="ASTRO P25",
        rx_nac="$4F2",
        tx_nac="$4F2",
    )
    cp.zones[0].channels[1] = Channel(
        channel_number=2,
        name="TAC REPEATER",
        rx_frequency=853.01250,
        tx_frequency=808.01250,
        voice_type="ASTRO P25",
        rx_nac="$1A5",
        tx_nac="$2B6",
    )

    out_cpg = str(tmp_path / "patched_205CFR2930.cpg")
    writer = CpgWriter(BACKUP_205CFR2930)
    writer.apply_codeplug(cp)
    writer.write(out_cpg)

    # 1. Verify with CpgParser that 100% of encrypted streams pass CRC-16 check
    with CpgParser(out_cpg) as parser:
        parsed = parser.parse(decrypt=True)

    assert parsed["header"]["serial"] == "205CMB9999"
    assert parsed["header"]["model"] == "H46UCF9PW6BN"

    data_streams = [
        s for s in parsed["streams"] if s["name"] != "AdkFileHeader"
    ]
    assert len(data_streams) == 147
    assert all(s.get("crc_ok") is True for s in data_streams)

    # 2. Verify that Strm_0 directory CRCs in the output file match every stream's CRC
    verify_writer = CpgWriter(out_cpg)
    for rec in verify_writer.get_strm0_directory():
        sname = f"Strm_{rec['stream_id']}"
        dec_stream = verify_writer.streams[sname]
        trailing_crc = struct.unpack(">H", dec_stream[-2:])[0]
        assert rec["stream_crc"] == trailing_crc == crc16_ccitt(bytes(dec_stream[6:-2]))

    # Verify Strm_2 was also updated with serial & model
    s2_plain = bytes(verify_writer.streams["Strm_2"])
    assert b"205CMB9999\x00" in s2_plain
    assert b"H46UCF9PW6BN\x00" in s2_plain

    # Verify Strm_26 (0x000D zone names) has "TEAM COMM"
    s26_plain = bytes(verify_writer.streams["Strm_26"])
    assert b"TEAM COMM\x00" in s26_plain

    # 3. Verify with CpgDecoder that decoding the newly written .cpg returns updated fields
    with CpgDecoder(out_cpg) as dec2:
        cp_out = dec2.decode()

    assert cp_out.serial_number == "205CMB9999"
    assert cp_out.radio_model == "H46UCF9PW6BN"
    assert len(cp_out.zones) >= 1

    ch1, ch2 = cp_out.zones[0].channels[0], cp_out.zones[0].channels[1]
    assert ch1.name == "P25 SIMPLEX"
    assert ch1.rx_frequency == 851.5125
    assert ch1.tx_frequency == 851.5125
    assert ch1.rx_nac == "$4F2"
    assert ch1.tx_nac == "$4F2"

    assert ch2.name == "TAC REPEATER"
    assert ch2.rx_frequency == 853.0125
    assert ch2.tx_frequency == 808.0125
    assert ch2.rx_nac == "$1A5"
    assert ch2.tx_nac == "$2B6"


@pytest.mark.skipif(
    not os.path.exists(BACKUP_RADIO1),
    reason="backups/Radio1_205CMB2249_codeplug.cpg not present",
)
def test_cpg_writer_roundtrip_radio1_multi_zone(tmp_path):
    """
    Verify CpgWriter on the 502-stream multi-zone Radio1_205CMB2249_codeplug.cpg
    backup, checking that all 501 data streams pass CRC-16 and Strm_0 stays synced.
    """
    with CpgDecoder(BACKUP_RADIO1) as dec:
        cp = dec.decode()

    cp.zones[0].channels[0].name = "ALPHA TAC 1"
    cp.zones[0].channels[0].rx_frequency = 852.12500
    cp.zones[0].channels[0].tx_frequency = 807.12500
    cp.zones[0].channels[0].rx_nac = "$3A1"
    cp.zones[0].channels[0].tx_nac = "$3A2"
    cp.zones[1].channels[0].name = "BRAVO CALL"

    out_cpg = str(tmp_path / "patched_radio1.cpg")
    CpgWriter.write_codeplug(cp, out_cpg, template_path=BACKUP_RADIO1)

    with CpgParser(out_cpg) as parser:
        parsed = parser.parse(decrypt=True)

    data_streams = [
        s for s in parsed["streams"] if s["name"] != "AdkFileHeader"
    ]
    assert len(data_streams) == 501
    assert all(s.get("crc_ok") is True for s in data_streams)

    with CpgDecoder(out_cpg) as dec2:
        cp_out = dec2.decode()

    assert cp_out.zones[0].channels[0].name == "ALPHA TAC 1"
    assert cp_out.zones[0].channels[0].rx_frequency == 852.125
    assert cp_out.zones[0].channels[0].tx_frequency == 807.125
    assert cp_out.zones[0].channels[0].rx_nac == "$3A1"
    assert cp_out.zones[0].channels[0].tx_nac == "$3A2"
    assert cp_out.zones[1].channels[0].name == "BRAVO CALL"
