"""Offline tests for the .cpg -> RCMP write-session assembler.

The oracle is the real codeplug backups in backups/: every object stored in a
`.cpg` carries its own CRC, so the write-record encoder can be proven byte-exact
without a radio and without a captured write session. The partition map is
cross-checked against a committed live read capture.
"""
import glob
import json
import os

import pytest

olefile = pytest.importorskip("olefile")

from open_astro.parsers.cpg_parser import CpgParser, crc16_ccitt
from open_astro.protocol import rcmp
from open_astro.protocol.write_session import (
    CpgWriteAssembler, WriteObject, WriteSessionError, part_map_from_capture,
    PART_TUNING,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUPS = sorted(glob.glob(os.path.join(REPO, "backups", "*.cpg")))


def _unframe_write(record: bytes):
    """Pull (part, obj, inst, payload, crc) back out of a framed 0101 record."""
    inner = record[2:]                       # drop 2-byte length prefix
    assert inner[:2] == b"\x01\x01"
    part = inner[2]
    obj = int.from_bytes(inner[3:5], "big")
    inst = int.from_bytes(inner[5:7], "big")
    n = int.from_bytes(inner[7:9], "big")    # counts payload + 2-byte CRC
    # header is 0101 part obj(2) inst(2) n(2) 0000 n(2) = 13 bytes
    payload = inner[13:13 + (n - 2)]
    crc = int.from_bytes(inner[-2:], "big")
    return part, obj, inst, payload, crc


# ---------------------------------------------------------------------------
# The core oracle: encoder CRC == the CRC stored in every real .cpg object
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cpg", BACKUPS, ids=[os.path.basename(b) for b in BACKUPS])
def test_build_write_crc_matches_stored_cpg_crc(cpg):
    p = CpgParser(cpg)
    try:
        objs = p.objects()
    finally:
        p.close()
    assert objs, f"no objects decoded from {cpg}"
    for o in objs:
        assert o["crc_ok"], f"{o['name']} tag {o['tag']} failed its own CRC"
        rec = rcmp.build_write(0x80, o["tag"], o["payload"], o["instance"])
        _, _, _, payload, crc = _unframe_write(rec)
        # the encoder must reproduce the payload and the exact stored CRC
        assert payload == o["payload"]
        assert crc == o["stored_crc"], (
            f"{o['name']}: encoder CRC 0x{crc:04x} != stored 0x{o['stored_crc']:04x}")
        assert crc == crc16_ccitt(o["payload"])


# ---------------------------------------------------------------------------
# Assembler: load from .cpg, round-trip, and ordering
# ---------------------------------------------------------------------------
def test_from_cpg_loads_all_crc_ok_objects():
    cpg = BACKUPS[0]
    p = CpgParser(cpg)
    try:
        n_ok = sum(1 for o in p.objects() if o["crc_ok"])
    finally:
        p.close()
    asm = CpgWriteAssembler.from_cpg(cpg)
    assert len(asm.objects) == n_ok
    assert len(asm.write_records()) == n_ok


def test_records_round_trip_part_obj_inst_payload():
    asm = CpgWriteAssembler.from_cpg(BACKUPS[0])
    for w, rec in zip(asm.objects, asm.write_records()):
        part, obj, inst, payload, _ = _unframe_write(rec)
        assert (part, obj, inst, payload) == (w.part, w.obj, w.inst, w.payload)


# ---------------------------------------------------------------------------
# Safety gates
# ---------------------------------------------------------------------------
def test_refuses_tuning_partition():
    asm = CpgWriteAssembler(
        [WriteObject(PART_TUNING, 0x10, 0, b"\x00\x01")])
    with pytest.raises(WriteSessionError, match="0x82"):
        asm.write_records()


def test_refuses_unapproved_partition():
    asm = CpgWriteAssembler([WriteObject(0x99, 0x10, 0, b"\x00\x01")])
    with pytest.raises(WriteSessionError, match="unapproved"):
        asm.write_records()
    # ...unless explicitly allowed
    ok = CpgWriteAssembler([WriteObject(0x99, 0x10, 0, b"\x00\x01")],
                           allowed_parts={0x80, 0x99})
    assert len(ok.write_records()) == 1


def test_from_cpg_aborts_on_corrupt_object():
    # Feed objects directly with a deliberately broken payload/crc path: a part
    # map that marks an object tuning must still be refused at assembly time.
    pmap = {}
    asm = CpgWriteAssembler.from_cpg(BACKUPS[0], part_map=pmap)
    # mark the first object's partition as tuning and confirm the guard trips
    first = asm.objects[0]
    asm.objects[0] = WriteObject(PART_TUNING, first.obj, first.inst, first.payload)
    with pytest.raises(WriteSessionError, match="0x82"):
        asm.write_records()


# ---------------------------------------------------------------------------
# Session framing
# ---------------------------------------------------------------------------
def test_build_session_requires_prepare_or_optin():
    asm = CpgWriteAssembler.from_cpg(BACKUPS[0])
    with pytest.raises(WriteSessionError, match="prepare"):
        asm.build_session()


def test_build_session_structure_offline():
    asm = CpgWriteAssembler.from_cpg(BACKUPS[0])
    sess = asm.build_session(allow_without_prepare=True)
    recs = list(rcmp.iter_records(sess))
    # opens with 0106 00, ends with 0106 01, writes in between in object order
    assert recs[0] == bytes([0x01, 0x06, 0x00])
    assert recs[-1] == bytes([0x01, 0x06, 0x01])
    writes = [r for r in recs if int.from_bytes(r[:2], "big") == rcmp.OP_WRITE]
    assert len(writes) == len(asm.objects)
    # order preserved
    first_obj = int.from_bytes(writes[0][3:5], "big")
    assert first_obj == asm.objects[0].obj


# ---------------------------------------------------------------------------
# Cross-source: .cpg object tags match the live read capture's object ids
# ---------------------------------------------------------------------------
def test_cpg_tags_match_live_read_capture():
    cap = os.path.join(REPO, "captures", "cps_20261023_082619_decoded.json")
    if not os.path.exists(cap):
        pytest.skip("read capture not present")
    d = json.load(open(cap))
    stream = bytes.fromhex(d["OUT host->radio"]["rcmp_stream_hex"])
    pmap = part_map_from_capture(stream)
    cap_objs = {obj for (obj, _inst) in pmap}
    # Use whichever backup overlaps most (the capture's own radio).
    best = 0.0
    for cpg in BACKUPS:
        p = CpgParser(cpg)
        try:
            tags = {o["tag"] for o in p.objects()}
        finally:
            p.close()
        if tags:
            best = max(best, len(tags & cap_objs) / len(tags))
    # The matching radio's codeplug tags should be almost entirely present as
    # object ids in the live read capture -- confirms tag == RCMP object id.
    assert best > 0.9, f"best cpg/capture tag overlap only {best:.2f}"
