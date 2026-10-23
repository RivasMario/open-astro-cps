"""Tests for the offline .cpg parser's verified crypto primitives.

These cover the pieces confirmed against the real binaries + known vectors:
the RC4 key derivation (fhAdk10c), RC4 itself, and CRC-16-CCITT (cgIsh10c).
The OLE/stream decoding is exercised separately once a sample .cpg exists.
"""
from open_astro.parsers.cpg_parser import derive_rc4_key, rc4, crc16_ccitt


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
    from open_astro.parsers.cpg_parser import parse_header, HDR_UUID_OFF, HDR_MODEL_OFF, HDR_SERIAL_OFF
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
