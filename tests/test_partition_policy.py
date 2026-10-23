"""Tests for the CPS-derived partition allowlist (schema/partition_map.json)
and its enforcement in the write assembler. Offline; the oracle is the capture-
derived map committed to the repo."""
import glob
import os

import pytest

olefile = pytest.importorskip("olefile")

from open_astro.protocol.write_session import (
    CpgWriteAssembler, WriteObject, WriteSessionError, PartitionPolicy,
    part_map_from_capture,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(REPO, "schema", "partition_map.json")
BACKUPS = sorted(glob.glob(os.path.join(REPO, "backups", "*.cpg")))


def test_map_file_present_and_sane():
    assert os.path.exists(MAP), "run tools/derive_partition_map.py"
    pol = PartitionPolicy.load(MAP)
    # 0x80 codeplug writable, 0x82 tuning never writable
    assert pol.partitions[0x80]["writable"] is True
    assert pol.partitions[0x82]["writable"] is False


def test_policy_refuses_tuning():
    pol = PartitionPolicy.load(MAP)
    with pytest.raises(WriteSessionError, match="0x82"):
        pol.check(0x82, 4217)


def test_policy_allows_codeplug_object_in_range():
    pol = PartitionPolicy.load(MAP)
    pol.check(0x80, 100)          # within 10..4095, no raise
    pol.check(0x81, 4101)         # within 4100..4102


def test_policy_refuses_object_out_of_range():
    pol = PartitionPolicy.load(MAP)
    with pytest.raises(WriteSessionError, match="outside"):
        pol.check(0x80, 9999)     # above observed 0x80 max


def test_policy_refuses_unobserved_partition():
    pol = PartitionPolicy.load(MAP)
    with pytest.raises(WriteSessionError, match="never observed|not writable"):
        pol.check(0x99, 10)


def test_fallback_when_map_missing_still_refuses_tuning():
    pol = PartitionPolicy.load(os.path.join(REPO, "schema", "does_not_exist.json"))
    assert pol.source == "(default fallback)"
    with pytest.raises(WriteSessionError, match="0x82"):
        pol.check(0x82, 4217)
    pol.check(0x80, 123456)       # no range check in fallback -> allowed


def test_assembler_under_policy_passes_for_real_cpg():
    # A real codeplug assembled with the capture part-map must satisfy the
    # policy end-to-end (every object lands in an allowed, in-range partition).
    cap = os.path.join(REPO, "captures", "cps_20261023_082619_decoded.json")
    if not os.path.exists(cap) or not BACKUPS:
        pytest.skip("inputs not present")
    import json
    d = json.load(open(cap))
    pmap = part_map_from_capture(bytes.fromhex(d["OUT host->radio"]["rcmp_stream_hex"]))
    pol = PartitionPolicy.load(MAP)
    # pick the backup whose objects are covered by the capture part-map
    for cpg in BACKUPS:
        asm = CpgWriteAssembler.from_cpg(cpg, part_map=pmap, policy=pol)
        if all((o.obj, o.inst) in pmap for o in asm.objects):
            recs = asm.write_records()      # must not raise
            assert len(recs) == len(asm.objects)
            return
    pytest.skip("no backup fully covered by the committed capture part-map")


def test_assembler_policy_blocks_tuning_object():
    pol = PartitionPolicy.load(MAP)
    asm = CpgWriteAssembler([WriteObject(0x82, 4217, 0, b"\x00\x01")], policy=pol)
    with pytest.raises(WriteSessionError, match="0x82"):
        asm.write_records()
