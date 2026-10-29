"""Unit tests for ChannelPatcher and codeplug editing."""
import os
import pytest

olefile = pytest.importorskip("olefile")

from open_astro.parsers.cpg_parser import CpgParser
from open_astro.parsers.cpg_decode import CpgDecoder, TAG_CHANNEL_NAMES, TAG_CHANNEL_FREQS
from open_astro.parsers.channel_patch import ChannelPatcher, encode_squelch_byte, ChannelPatchError
from open_astro.protocol import rcmp

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_VHF = os.path.join(REPO, "backups", "407CHT0214.cpg")
BACKUP_800 = os.path.join(REPO, "backups", "205CFR2930.cpg")


def test_encode_squelch_byte_ctcss():
    # 156.7 Hz is index 26 (0x1a)
    assert encode_squelch_byte(pl_tone=156.7) == 26
    # 67.0 Hz is index 1
    assert encode_squelch_byte(pl_tone=67.0) == 1
    # CSQ
    assert encode_squelch_byte() == 0


def test_encode_squelch_byte_dpl():
    # DPL 023 is first code in DPL_CODES -> 0x80 | 0 = 0x80
    assert encode_squelch_byte(dpl_code=23) == 0x80
    # DPL 754 is last code (index 103) -> 0x80 | 103 = 0xe7
    assert encode_squelch_byte(dpl_code=754) == 0x80 | 103


def test_encode_squelch_byte_unknown_raises():
    with pytest.raises(ChannelPatchError):
        encode_squelch_byte(pl_tone=999.9)
    with pytest.raises(ChannelPatchError):
        encode_squelch_byte(dpl_code=999)


def test_patch_channel_name_and_frequency():
    parser = CpgParser(BACKUP_VHF)
    try:
        objects = parser.objects()
    finally:
        parser.close()

    patcher = ChannelPatcher(objects)
    # Zone 1 Channel 1 original was "LAW" on 158.94000 MHz
    patcher.patch_channel(1, 1, name="DISPATCH", rx_frequency=155.12500, tx_frequency=155.12500,
                          rx_pl_tone=156.7, tx_pl_tone=156.7, simplex=True)

    # Decode modified objects via CpgDecoder.build_from_streams
    streams = [(o["tag"], o["instance"], o["payload"]) for o in patcher.objects]
    cp = CpgDecoder.build_from_streams(streams)
    ch1 = cp.zones[0].channels[0]
    assert ch1.name == "DISPATCH"
    assert ch1.rx_frequency == 155.125
    assert ch1.tx_frequency == 155.125
    assert ch1.rx_pl_tone == 156.7
    assert ch1.tx_pl_tone == 156.7
    assert ch1.voice_type == "Analog"


def test_generate_edits_matches_modified_objects():
    parser = CpgParser(BACKUP_VHF)
    try:
        objects = parser.objects()
    finally:
        parser.close()

    patcher = ChannelPatcher(objects)
    patcher.patch_channel(1, 2, name="TAC 2X")

    edits = patcher.generate_edits(objects)
    assert len(edits) == 1  # Only zone 1's 0x0FFF was modified
    part, obj, inst, hex_data = edits[0].split(":")
    assert part == "80"
    assert obj == "0fff"
    assert inst == "0"
    assert len(hex_data) > 0


def test_to_write_assembler():
    parser = CpgParser(BACKUP_800)
    try:
        objects = parser.objects()
    finally:
        parser.close()

    patcher = ChannelPatcher(objects)
    patcher.patch_channel(1, 1, name="CALL 1")

    asm = patcher.to_write_assembler()
    records = asm.write_records()
    assert len(records) == len(objects)

    # Build session with synthesized prepare records
    session = asm.build_session(synthesize_prepare=True)
    assert len(session) > 0
    # First record is session open (010600)
    assert session[:5] == bytes.fromhex("0003010600")
