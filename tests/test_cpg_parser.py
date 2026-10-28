"""Tests for the offline .cpg parser's verified crypto primitives, directory
index (Strm_0), and .tun file distinction.
"""
import os

import pytest

from open_astro.parsers.cpg_parser import (
    CpgParser,
    crc16_ccitt,
    derive_rc4_key,
    parse_directory,
    parse_header,
    rc4,
    HDR_UUID_OFF,
    HDR_MODEL_OFF,
    HDR_SERIAL_OFF,
)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")
CPG_205CFR2930 = os.path.join(BACKUP_DIR, "205CFR2930.cpg")
CPG_205CMB2249 = os.path.join(BACKUP_DIR, "Radio1_205CMB2249_codeplug.cpg")
TUN_205CMB2249 = os.path.join(BACKUP_DIR, "Radio1_205CMB2249_restored_tuning.tun")
TUN_205CFR2930 = os.path.join(BACKUP_DIR, "Radio3_205CFR2930_tuning.tun")


def test_rc4_key_matches_documented_value():
    # MD5("A8Z6J9QP5")[:5] == 29 26 65 82 0D, then padded to 16 bytes with zeros.
    key = derive_rc4_key()
    assert key[:5].hex() == "292665820d"
    assert key == bytes.fromhex("292665820d") + b"\x00" * 11
    assert len(key) == 16


def test_rc4_is_involutive():
    key = derive_rc4_key()
    for pt in (b"", b"A", b"HELLO ASTRO 25 CODEPLUG STREAM", bytes(range(256))):
        assert rc4(key, rc4(key, pt)) == pt


def test_parse_header_extracts_fields_at_mapped_offsets():
    # Build an 800-byte cleartext header with a UUID, model, serial at the mapped offsets.
    blob = bytearray(800)
    uuid = bytes(range(16))
    blob[HDR_UUID_OFF:HDR_UUID_OFF + 16] = uuid
    blob[HDR_MODEL_OFF:HDR_MODEL_OFF + 12] = b"H66KDD9PW5BN"
    blob[HDR_SERIAL_OFF:HDR_SERIAL_OFF + 10] = b"407CNR2572"
    h = parse_header(bytes(blob))
    assert h["uuid"] == uuid.hex()
    assert h["model"] == "H66KDD9PW5BN"
    assert h["serial"] == "407CNR2572"


def test_crc16_ccitt_known_vector():
    # Standard CRC-16/CCITT-FALSE check value for "123456789" is 0x29B1,
    # but this implementation is init=0x0000 (as in cgIsh10c) -> 0x31C3.
    assert crc16_ccitt(b"123456789") == 0x31C3
    assert crc16_ccitt(b"") == 0x0000


def test_stream_framing_payload_crc():
    # Stream format verified 2026-10-23:
    # 2B tag, 2B instance, 2B payload length, payload, 2B big-endian CRC16 over payload
    payload = b"SITE 1" + b"\x00" * 10
    crc = crc16_ccitt(payload)
    stream = (
        (0x0FDC).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + len(payload).to_bytes(2, "big")
        + payload
        + crc.to_bytes(2, "big")
    )
    assert crc16_ccitt(stream[6:-2]) == int.from_bytes(stream[-2:], "big")


def test_parse_directory_synthetic_records():
    # 10-byte records: [tag:u16, inst:u16, flags:u16, stream_crc:u16, stream_id:u16]
    rec1 = bytes.fromhex("1005000000810e3b0001")
    rec2 = bytes.fromhex("1004000000812b6e0002")
    trailer = bytes.fromhex("05a7")
    records = parse_directory(rec1 + rec2 + trailer)
    assert len(records) == 2
    assert records[0] == {
        "tag": "0x1005",
        "instance": 0,
        "flags": 0x0081,
        "stream_crc": 0x0E3B,
        "stream_id": 1,
    }
    assert records[1] == {
        "tag": "0x1004",
        "instance": 0,
        "flags": 0x0081,
        "stream_crc": 0x2B6E,
        "stream_id": 2,
    }


@pytest.mark.skipif(not os.path.exists(CPG_205CFR2930), reason="205CFR2930.cpg not present")
def test_parse_real_cpg_directory_and_crc_205cfr2930():
    with CpgParser(CPG_205CFR2930) as parser:
        data = parser.parse()
    assert data["header"]["model"] == "H46UCF9PW6AN"
    assert data["header"]["serial"] == "205CFR2930"
    assert data["directory"] is not None
    assert data["directory"]["record_count"] == 146
    assert data["directory"]["matched_streams"] == 146
    assert data["directory"]["all_matched"] is True
    data_streams = [s for s in data["streams"] if s["name"] != "AdkFileHeader"]
    assert len(data_streams) == 147
    assert all(s.get("crc_ok") is True for s in data_streams)


@pytest.mark.skipif(not os.path.exists(CPG_205CMB2249), reason="Radio1_205CMB2249_codeplug.cpg not present")
def test_parse_real_cpg_directory_and_crc_205cmb2249():
    with CpgParser(CPG_205CMB2249) as parser:
        data = parser.parse()
    assert data["header"]["model"] == "H46UCF9PW6BN"
    assert data["header"]["serial"] == "205CMB2249"
    assert data["directory"] is not None
    assert data["directory"]["record_count"] == 500
    assert data["directory"]["matched_streams"] == 500
    assert data["directory"]["all_matched"] is True
    data_streams = [s for s in data["streams"] if s["name"] != "AdkFileHeader"]
    assert len(data_streams) == 501
    assert all(s.get("crc_ok") is True for s in data_streams)


@pytest.mark.skipif(not os.path.exists(TUN_205CMB2249), reason=".tun backup not present")
def test_tun_files_are_raw_mfc_carchive_not_ole():
    # .tun files are raw MFC CArchive streams (CSaveValues), not OLE compound files.
    with pytest.raises(ValueError, match="not an OLE compound file"):
        CpgParser(TUN_205CMB2249)

    with open(TUN_205CMB2249, "rb") as f:
        raw1 = f.read()
    assert len(raw1) == 4686
    assert raw1[0] == 10 and raw1[1:11] == b"205CMB2249"
    assert raw1[11] == 12 and raw1[12:24] == b"H46UCF9PW6BN"
    assert b"CSaveValues" in raw1

    if os.path.exists(TUN_205CFR2930):
        with open(TUN_205CFR2930, "rb") as f:
            raw3 = f.read()
        assert len(raw3) == 4686
        assert raw3[0] == 10 and raw3[1:11] == b"205CFR2930"
        assert raw3[11] == 12 and raw3[12:24] == b"H46UCF9PW6AN"
        assert b"CSaveValues" in raw3
