"""Verify the RCMP codec against bytes captured from a real CPS <-> radio
session (docs/RCMP_WIRE_PROTOCOL.md). The hex anchors below are copied verbatim
from captures/cps_20261023_082619.pcap (codeplug Read), so these tests pin the
codec to ground truth with no hardware."""
from open_astro.protocol import rcmp


# Exact framed records observed at the start of the codeplug-read OUT stream.
CAP_SESSION = bytes.fromhex("0003010600")                     # len 0003, 010600
CAP_READ_0047 = bytes.fromhex("000b0100800047000000100000")   # read obj 0x0047 len 0x0010
CAP_READ_0073 = bytes.fromhex("000b0100800073000003700000")   # read obj 0x0073 len 0x0370


def test_frame_length_prefix():
    assert rcmp.frame(b"\x01\x06\x00") == CAP_SESSION
    assert rcmp.frame(b"") == b"\x00\x00"


def test_build_read_matches_capture():
    # These must reproduce the real CPS read requests byte-for-byte.
    assert rcmp.build_read(rcmp.PART_CODEPLUG, 0x0047, 0x0010) == CAP_READ_0047
    assert rcmp.build_read(rcmp.PART_CODEPLUG, 0x0073, 0x0370) == CAP_READ_0073


def test_build_session_matches_capture():
    assert rcmp.build_session_open() == CAP_SESSION


def test_iter_records_splits_concatenated_stream():
    stream = CAP_SESSION + CAP_READ_0047 + CAP_READ_0073
    recs = list(rcmp.iter_records(stream))
    assert [r.hex() for r in recs] == [
        "010600", "0100800047000000100000", "0100800073000003700000",
    ]


def test_iter_records_stops_on_truncation():
    # A trailing partial record (claims 8 bytes, only 2 present) is dropped.
    stream = CAP_SESSION + bytes.fromhex("00080102")
    assert len(list(rcmp.iter_records(stream))) == 1


def test_parse_read_record_header():
    rec = rcmp.parse_record(bytes.fromhex("0100800047000000100000"))
    assert rec["op"] == "READ"
    assert rec["partition"] == 0x80
    assert rec["object"] == 0x0047
    assert rec["instance"] == 0
    assert rec["length"] == 0x0010


def test_response_opcode_naming():
    assert rcmp.op_name(rcmp.OP_READ | rcmp.RESP_FLAG) == "READ_ACK"
    assert rcmp.op_name(rcmp.OP_WRITE | rcmp.RESP_FLAG) == "WRITE_ACK"


# Exact write record captured from CPS writing obj 0x0fff inst 1 (zone 2),
# channel names "CHAN 1"/"CHAN 2" (framed, incl. 2-byte length prefix).
_CAP_WRITE_0FFF = bytes.fromhex(
    "00370101800fff0001002a0000002a000000000002"
    "4348414e203100000000000000000000004348414e20320000000000000000000000"
    "9181")
_PAYLOAD_0FFF = bytes.fromhex(
    "0000000000024348414e2031000000000000000000000"
    "04348414e20320000000000000000000000")


def test_crc16_ccitt_known_vector():
    # Verified write-record data CRC (poly 0x1021, init 0x0000) from the capture.
    assert rcmp.crc16_ccitt(_PAYLOAD_0FFF) == 0x9181


def test_build_write_matches_capture_byte_exact():
    assert rcmp.build_write(0x80, 0x0FFF, _PAYLOAD_0FFF, inst=1) == _CAP_WRITE_0FFF


def test_edit_write_reproduces_cps_modified_record():
    # Editing the normal CHAN 2 name to CHAN 2X must byte-match the record CPS
    # actually sent for that same edit (captured device 64), framing aside.
    normal = _PAYLOAD_0FFF
    i = normal.find(b"CHAN 2") + len(b"CHAN 2")
    modified = normal[:i] + b"\x58" + normal[i + 1:]
    cps_modified_record = bytes.fromhex(
        "0101800fff0001002a0000002a000000000002"
        "4348414e20310000000000000000000000"
        "4348414e20325800000000000000000000"
        "22e7")
    assert rcmp.build_write(0x80, 0x0FFF, modified, inst=1)[2:] == cps_modified_record


def test_build_write_length_counts_payload_plus_crc():
    rec = rcmp.build_write(0x80, 0x0FFF, b"\x01\x02\x03\x04")
    payload_body = rec[2:]            # strip frame length
    length_field = int.from_bytes(payload_body[7:9], "big")
    assert length_field == 4 + 2      # payload + CRC


def test_round_trip_build_then_parse():
    rec = next(rcmp.iter_records(rcmp.build_read(rcmp.PART_TUNING, 0x1079, 0x03E8)))
    info = rcmp.parse_record(rec)
    assert info["partition"] == rcmp.PART_TUNING
    assert info["object"] == 0x1079
    assert info["length"] == 0x03E8
