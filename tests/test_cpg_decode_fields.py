"""Tests for field-level decoding schema and PersonalityRecord decoding.

Covers:
1. schema/field_layouts.json loading and structural validation.
2. Synthetic 35-byte 0x0FFB record decoding across all field types.
3. Strict vs non-strict decoding modes.
4. Container table (0x0FFD) decoding with decode_table_with_schema.
5. End-to-end field verification against real codeplugs:
   - backups/205CFR2930.cpg
   - backups/407CHT0214.cpg
   - backups/Radio1_205CMB2249_codeplug.cpg
"""
import os
from pathlib import Path
import pytest

from open_astro.parsers.cpg_decode import (
    CpgDecoder,
    TAG_CHANNEL_FREQS,
    TAG_PERSONALITY_REC,
    FREQ_REC_LEN,
    SIMPLEX_BIT,
    DPL_CODES,
    CTCSS_EIA,
    load_field_layouts,
    validate_field_layouts,
    get_schema_layout,
    normalize_tag,
    decode_record_with_schema,
    decode_table_with_schema,
    PersonalityRecord,
    SquelchValue,
    NacValue,
)

BACKUP_DIR = Path(__file__).resolve().parents[1] / "backups"
BACKUP_205 = BACKUP_DIR / "205CFR2930.cpg"
BACKUP_407 = BACKUP_DIR / "407CHT0214.cpg"
BACKUP_RADIO1 = BACKUP_DIR / "Radio1_205CMB2249_codeplug.cpg"


def make_0ffb_buffer(
    tag: int = 0x0FFB,
    reserved_2: int = 0x00,
    flag_3: int = 0x01,
    personality_type: int = 0x322F,
    nac_rx: int = 0x0293,
    nac_tx: int = 0x0293,
    nac_alt: int = 0x0293,
    freq_rx_mhz: float = 852.0625,
    freq_tx_mhz: float = 807.0625,
    freq_alt_mhz: float = 807.0625,
    squelch_rx: int = 0x1A,  # 156.7 Hz
    squelch_mid: int = 0x1A,
    squelch_tx: int = 0x1A,
    flags: int = 0x80,       # simplex
    reserved_tail: bytes = b"\x00" * 6,
    rec_terminator: int = 0x01,
) -> bytes:
    """Build a 35-byte 0x0FFB record buffer for testing."""
    buf = bytearray(FREQ_REC_LEN)
    buf[0:2] = tag.to_bytes(2, "big")
    buf[2] = reserved_2 & 0xFF
    buf[3] = flag_3 & 0xFF
    buf[4:6] = personality_type.to_bytes(2, "big")
    buf[6:8] = nac_rx.to_bytes(2, "big")
    buf[8:10] = nac_tx.to_bytes(2, "big")
    buf[10:12] = nac_alt.to_bytes(2, "big")
    buf[12:16] = int(round(freq_rx_mhz * 1_000_000 / 5)).to_bytes(4, "big")
    buf[16:20] = int(round(freq_tx_mhz * 1_000_000 / 5)).to_bytes(4, "big")
    buf[20:24] = int(round(freq_alt_mhz * 1_000_000 / 5)).to_bytes(4, "big")
    buf[24] = squelch_rx & 0xFF
    buf[25] = squelch_mid & 0xFF
    buf[26] = squelch_tx & 0xFF
    buf[27] = flags & 0xFF
    buf[28:34] = reserved_tail[:6].ljust(6, b"\x00")
    buf[34] = rec_terminator & 0xFF
    return bytes(buf)


# ---------------------------------------------------------------------------
# 1. Schema Loading and Validation Tests
# ---------------------------------------------------------------------------

def test_load_field_layouts_default():
    schema = load_field_layouts()
    assert isinstance(schema, dict)
    assert "0x0FFB" in schema
    assert "0x0FFD" in schema
    assert schema["0x0FFB"]["_record_len"] == FREQ_REC_LEN


def test_validate_field_layouts_valid():
    schema = load_field_layouts()
    assert validate_field_layouts(schema) is True


def test_validate_field_layouts_rejects_non_dict():
    with pytest.raises(ValueError, match="must be a dictionary"):
        validate_field_layouts(["not", "a", "dict"])  # type: ignore


def test_validate_field_layouts_rejects_missing_0x0ffb():
    with pytest.raises(ValueError, match="missing mandatory '0x0FFB'"):
        validate_field_layouts({"0x0FFD": {}})


def test_validate_field_layouts_rejects_bad_record_length():
    bad_schema = {
        "0x0FFB": {
            "_record_len": 40,
            "fields": [
                {"name": "record_tag", "offset": 0, "length": 2, "type": "u16be"}
            ]
        }
    }
    with pytest.raises(ValueError, match="_record_len must be 35"):
        validate_field_layouts(bad_schema)


def test_validate_field_layouts_rejects_field_gap():
    bad_schema = {
        "0x0FFB": {
            "_record_len": 35,
            "fields": [
                {"name": "f1", "offset": 0, "length": 2, "type": "u16be"},
                {"name": "f2", "offset": 3, "length": 1, "type": "u8"},  # gap at offset 2
            ]
        }
    }
    with pytest.raises(ValueError, match="offset mismatch: expected 2, got 3"):
        validate_field_layouts(bad_schema)


def test_get_schema_layout_variants():
    l1 = get_schema_layout("0x0FFB")
    l2 = get_schema_layout(0x0FFB)
    l3 = get_schema_layout("0x0ffb")
    l4 = get_schema_layout("0xFFB")
    assert l1 == l2 == l3 == l4
    assert l1["_name"] == "Conventional personality / channel record"


def test_get_schema_layout_unknown_tag():
    with pytest.raises(KeyError, match="not defined"):
        get_schema_layout("0x9999")


def test_normalize_tag():
    assert normalize_tag(0x0FFB) == "0x0FFB"
    assert normalize_tag("0x0ffb") == "0x0FFB"
    assert normalize_tag("0xFFB") == "0x0FFB"
    assert normalize_tag(15) == "0x000F"


# ---------------------------------------------------------------------------
# 2. Sample 35-Byte Buffer Decoding Tests
# ---------------------------------------------------------------------------

def test_decode_record_with_schema_fields():
    buf = make_0ffb_buffer(
        tag=0x0FFB,
        reserved_2=0x00,
        flag_3=0x01,
        personality_type=0x322F,
        nac_rx=0x0293,
        nac_tx=0x0293,
        nac_alt=0x0293,
        freq_rx_mhz=852.0625,
        freq_tx_mhz=807.0625,
        freq_alt_mhz=807.0625,
        squelch_rx=0x1A,
        squelch_mid=0x1A,
        squelch_tx=0x1A,
        flags=0x80,
        reserved_tail=b"\x00" * 6,
        rec_terminator=0x01,
    )

    rec = decode_record_with_schema(buf, tag="0x0FFB", strict=True)
    assert isinstance(rec, PersonalityRecord)

    # Schema field checks
    assert rec.record_tag == 0x0FFB
    assert rec.reserved_2 == 0x00
    assert rec.flag_3 == 0x01
    assert rec.personality_type == 0x322F
    assert rec.nac_rx == "$293"
    assert rec.nac_rx.raw == 0x0293
    assert rec.nac_tx == "$293"
    assert rec.nac_tx.raw == 0x0293
    assert rec.nac_alt == "$293"
    assert rec.freq_rx == 852.0625
    assert rec.freq_tx == 807.0625
    assert rec.freq_alt == 807.0625
    assert rec.squelch_rx == 0x1A
    assert rec.squelch_rx.kind == "CTCSS"
    assert rec.squelch_rx.pl_tone == 156.7
    assert rec.squelch_mid == 0x1A
    assert rec.squelch_tx == 0x1A
    assert rec.squelch_tx.pl_tone == 156.7
    assert rec.flags == 0x80
    assert rec.simplex is True
    assert rec.reserved_tail == b"\x00" * 6
    assert rec.rec_terminator == 0x01

    # Backwards compatibility channel aliases
    assert rec["rx_frequency"] == 852.0625
    assert rec["tx_frequency"] == 807.0625
    assert rec["rx_nac"] == "$293"
    assert rec["tx_nac"] == "$293"
    assert rec["rx_pl_tone"] == 156.7
    assert rec["tx_pl_tone"] == 156.7
    assert rec["voice_type"] == "Analog"


def test_repeater_pair_flags():
    buf = make_0ffb_buffer(
        freq_rx_mhz=158.940,
        freq_tx_mhz=154.400,
        flags=0x00,  # repeater / non-simplex
    )
    rec = decode_record_with_schema(buf, strict=True)
    assert rec.simplex is False
    assert rec["simplex"] is False
    assert rec.freq_rx == 158.940
    assert rec.freq_tx == 154.400


def test_csq_channel():
    buf = make_0ffb_buffer(
        squelch_rx=0,
        squelch_tx=0,
        flags=0x80,
    )
    rec = decode_record_with_schema(buf, strict=True)
    assert rec.squelch_rx == 0
    assert rec.squelch_rx.kind == "CSQ"
    assert rec.squelch_rx.pl_tone is None
    assert rec.squelch_rx.dpl_code is None
    assert rec.voice_type == "Unknown"


def test_dpl_channel():
    # DPL code at index 10 (octal 54)
    dpl_idx = 10
    dpl_byte = 0x80 | dpl_idx
    buf = make_0ffb_buffer(squelch_rx=dpl_byte, squelch_tx=dpl_byte)
    rec = decode_record_with_schema(buf, strict=True)
    assert rec.squelch_rx == dpl_byte
    assert rec.squelch_rx.kind == "DPL"
    assert rec.squelch_rx.pl_tone is None
    assert rec.squelch_rx.dpl_code == DPL_CODES[dpl_idx]
    assert rec.voice_type == "Analog"


def test_strict_mode_validations():
    # Too short
    short_buf = b"\x0f\xfb\x00"
    assert decode_record_with_schema(short_buf, strict=False) is None
    with pytest.raises(ValueError, match="Buffer length"):
        decode_record_with_schema(short_buf, strict=True)

    # Tag mismatch
    wrong_tag = make_0ffb_buffer(tag=0x1234)
    assert decode_record_with_schema(wrong_tag, strict=False) is not None
    with pytest.raises(ValueError, match="Record tag mismatch"):
        decode_record_with_schema(wrong_tag, strict=True)

    # Terminator mismatch
    wrong_term = make_0ffb_buffer(rec_terminator=0x00)
    with pytest.raises(ValueError, match="Record terminator mismatch"):
        decode_record_with_schema(wrong_term, strict=True)


def test_personality_record_dict_and_attr_access():
    buf = make_0ffb_buffer()
    rec = decode_record_with_schema(buf, strict=True)

    # Dict access equals attribute access
    assert rec["freq_rx"] == rec.freq_rx
    assert rec["rx_frequency"] == rec.rx_frequency
    assert rec["simplex"] == rec.simplex
    assert rec["record_tag"] == rec.record_tag
    assert rec["reserved_tail"] == rec.reserved_tail

    # to_dict conversion
    d = rec.to_dict()
    assert isinstance(d, dict)
    assert d["record_tag"] == 0x0FFB
    assert d["reserved_tail"] == b"\x00" * 6

    # to_dict with hex_bytes
    d_hex = rec.to_dict(hex_bytes=True)
    assert d_hex["reserved_tail"] == "000000000000"
    assert isinstance(d_hex["squelch_rx"], dict)
    assert d_hex["squelch_rx"]["kind"] == "CTCSS"


def test_decode_table_with_schema():
    r1 = make_0ffb_buffer(freq_rx_mhz=852.0625, freq_tx_mhz=852.0625)
    r2 = make_0ffb_buffer(freq_rx_mhz=853.0625, freq_tx_mhz=853.0625)
    # 0x0FFD table payload: 4 bytes reserved + 2 bytes count (2) + records
    payload = b"\x00\x00\x00\x00\x00\x02" + r1 + r2

    recs = decode_table_with_schema(payload, tag="0x0FFD", strict=True)
    assert len(recs) == 2
    assert recs[0].freq_rx == 852.0625
    assert recs[1].freq_rx == 853.0625


# ---------------------------------------------------------------------------
# 3. Real Codeplug Verification Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not BACKUP_205.exists(), reason="205CFR2930.cpg backup not found")
def test_real_backup_205cfr2930_fields():
    with CpgDecoder(str(BACKUP_205)) as dec:
        streams = dec._decoded_streams()
        freq_streams = [(inst, pl) for tag, inst, pl in streams if tag == TAG_CHANNEL_FREQS]
        # Instance 1 contains the conventional personality table
        inst1_pl = next(pl for inst, pl in freq_streams if inst == 1)
        recs = decode_table_with_schema(inst1_pl, strict=True)

        assert len(recs) == 2
        # CHAN 1
        ch1 = recs[0]
        assert ch1.record_tag == 0x0FFB
        assert ch1.rec_terminator == 0x01
        assert ch1.freq_rx == 852.0625
        assert ch1.freq_tx == 852.0625
        assert ch1.freq_alt == 852.0625
        assert ch1.nac_rx == "$293"
        assert ch1.nac_tx == "$293"
        assert ch1.flags == 0x80
        assert ch1.simplex is True
        assert ch1.squelch_rx == 0  # CSQ
        assert ch1.squelch_tx == 0
        assert ch1.flag_3 == 0x01
        assert ch1.personality_type == 0x322F
        assert ch1.reserved_tail == b"\x00" * 6

        # CHAN 2
        ch2 = recs[1]
        assert ch2.record_tag == 0x0FFB
        assert ch2.rec_terminator == 0x01
        assert ch2.freq_rx == 853.0625
        assert ch2.freq_tx == 853.0625
        assert ch2.nac_rx == "$293"
        assert ch2.flags == 0x80
        assert ch2.simplex is True
        assert ch2.squelch_rx == 0
        assert ch2.personality_type == 0x642A
        assert ch2.reserved_tail == b"\x00" * 6


@pytest.mark.skipif(not BACKUP_407.exists(), reason="407CHT0214.cpg backup not found")
def test_real_backup_407cht0214_fields():
    with CpgDecoder(str(BACKUP_407)) as dec:
        streams = dec._decoded_streams()
        all_recs = []
        for tag, inst, pl in streams:
            if tag == TAG_CHANNEL_FREQS:
                recs = decode_table_with_schema(pl, strict=True)
                all_recs.extend(recs)

        # 407CHT0214 has 48 conventional channels across instances 0..5
        assert len(all_recs) == 48

        # Invariant checks for every record in the codeplug
        for r in all_recs:
            assert r.record_tag == 0x0FFB
            assert r.rec_terminator == 0x01
            assert r.reserved_2 == 0x00
            assert r.reserved_tail == b"\x00" * 6
            assert r.freq_rx > 136.0 and r.freq_rx < 174.0

        # Spot check LAW repeater channel (instance 0, record 0)
        law = all_recs[0]
        assert law.freq_rx == 158.940
        assert law.freq_tx == 154.400
        assert law.flags == 0x00
        assert law.simplex is False
        assert law.squelch_rx == 0x23  # index 35 = 210.7 Hz
        assert law.squelch_rx.pl_tone == 210.7
        assert law.squelch_tx == 0x23
        assert law.voice_type == "Analog"

        # Spot check V TAC 11 (instance 1, record 0)
        vtac11 = all_recs[10]
        assert vtac11.freq_rx == 154.010  # V TAC 11
        assert vtac11.freq_tx == 154.010
        assert vtac11.flags == 0x80
        assert vtac11.simplex is True
        assert law.squelch_rx.kind == "CTCSS"


@pytest.mark.skipif(not BACKUP_RADIO1.exists(), reason="Radio1_205CMB2249_codeplug.cpg backup not found")
def test_real_backup_radio1_205cmb2249_fields():
    with CpgDecoder(str(BACKUP_RADIO1)) as dec:
        streams = dec._decoded_streams()
        ffb_records = []
        for tag, inst, pl in streams:
            if tag == TAG_CHANNEL_FREQS:
                # Conventional records within the stream
                raw_recs = dec._freq_records(pl)
                for r in raw_recs:
                    if int.from_bytes(r[:2], "big") == TAG_PERSONALITY_REC:
                        rec = decode_record_with_schema(r, strict=True)
                        assert rec is not None
                        ffb_records.append((inst, rec))

        assert len(ffb_records) > 0

        # All 0x0FFB records must obey schema invariants
        for inst, r in ffb_records:
            assert r.record_tag == 0x0FFB
            assert r.rec_terminator == 0x01
            assert r.reserved_tail == b"\x00" * 6

        # Check split channels (flag 0x40 observed on 800 MHz repeater channels)
        split_channels = [r for inst, r in ffb_records if r.flags == 0x40]
        assert len(split_channels) > 0
        for r in split_channels:
            assert r.simplex is False
            assert r.freq_rx != r.freq_tx

        # Check direct/simplex channels (flag 0x80)
        simplex_channels = [r for inst, r in ffb_records if r.flags == 0x80]
        assert len(simplex_channels) > 0
        for r in simplex_channels:
            assert r.simplex is True
            assert r.freq_rx == r.freq_tx


@pytest.mark.skipif(not BACKUP_RADIO1.exists(), reason="Radio1_205CMB2249_codeplug.cpg backup not found")
def test_radio1_aggregates_all_0ffd_instances():
    """The conventional personalities span MANY 0x0FFD instances, not just inst 1.

    The full flashed fleet codeplug carries 43 0x0FFB records across 19 instances
    (even=10-rec tables, odd=6-rec tables, last short). An earlier reader looked at
    a single instance and saw only 2; personality_records() must walk them all.
    """
    with CpgDecoder(str(BACKUP_RADIO1)) as dec:
        recs = dec.personality_records()

    # NOT 2 (the single-instance count) -- all 43 across every 0x0FFD instance.
    assert len(recs) == 43

    # Every aggregated record is a real 0x0FFB personality obeying schema invariants.
    for r in recs:
        assert isinstance(r, PersonalityRecord)
        assert r.record_tag == 0x0FFB
        assert r.rec_terminator == 0x01
        assert r.reserved_tail == b"\x00" * 6


@pytest.mark.skipif(not BACKUP_RADIO1.exists(), reason="Radio1_205CMB2249_codeplug.cpg backup not found")
def test_radio1_adp_secure_channel_present():
    """The 800 MHz ADP SECURE channel (851.5125) lives in later 0x0FFD instances.

    Two forms exist: a duplex/repeater pair (806.5125 rx / 851.5125 tx, flags 0x40)
    and a simplex/talkaround channel (851.5125 rx==tx, flags 0x80). Both are absent
    from a single-instance read; aggregation across all instances surfaces them.
    """
    # freq_x5hz encoding: stored value = Hz / 5 as a 4-byte big-endian word.
    def mhz(value_hz_over_5: int) -> float:
        return round(value_hz_over_5 * 5 / 1_000_000, 5)

    rx_806 = mhz(806_512_500 // 5)  # 806.5125 MHz
    tx_851 = mhz(851_512_500 // 5)  # 851.5125 MHz
    assert rx_806 == 806.5125
    assert tx_851 == 851.5125

    with CpgDecoder(str(BACKUP_RADIO1)) as dec:
        recs = dec.personality_records()

    tol = 1e-4
    # Duplex ADP repeater pair: distinct rx/tx on the standard 45 MHz 800 split.
    duplex = [
        r for r in recs
        if abs(r.freq_rx - rx_806) < tol and abs(r.freq_tx - tx_851) < tol
    ]
    assert duplex, "ADP duplex channel (806.5125 rx / 851.5125 tx) not found"
    for r in duplex:
        assert r.flags == 0x40
        assert r.simplex is False
        assert r.freq_rx != r.freq_tx

    # Simplex/talkaround ADP channel: rx == tx == 851.5125, flags 0x80.
    simplex = [
        r for r in recs
        if abs(r.freq_rx - tx_851) < tol and abs(r.freq_tx - tx_851) < tol
    ]
    assert simplex, "ADP simplex channel (851.5125 rx==tx) not found"
    for r in simplex:
        assert r.flags == 0x80
        assert r.simplex is True
        assert abs(r.freq_rx - r.freq_tx) < tol
