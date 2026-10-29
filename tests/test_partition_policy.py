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
    with pytest.raises(WriteSessionError,
                       match="never observed|not writable|does not declare"):
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


def test_live_write_client_enforces_allowlist():
    # Defense in depth: the on-wire write client applies the policy too, so an
    # out-of-range object is refused before any bytes are sent.
    from open_astro.protocol.rcmp_write import RcmpWriteClient, RcmpWriteError

    class _NoConn:
        def sendall(self, data):
            raise AssertionError("must refuse BEFORE sending any bytes")
        def recv(self, n):
            return b""
        def close(self):
            pass

    c = RcmpWriteClient(_NoConn(), allow_write=True)   # policy auto-loaded
    with pytest.raises(RcmpWriteError, match="outside|never observed"):
        c.write_object(0x80, 9999, b"\x00\x01")        # above 0x80 range
    with pytest.raises(RcmpWriteError, match="0x82"):
        c.write_object(0x82, 4217, b"\x00\x01")


# ---------------------------------------------------------------------------
# Motorola-declared layout (schema/patport_layout.json, from PatPort.exe /
# cgIsh10c.dll) cross-validated against the capture-derived map.
# ---------------------------------------------------------------------------
LAYOUT = os.path.join(REPO, "schema", "patport_layout.json")


def _layout():
    import json
    return json.load(open(LAYOUT))


def test_patport_layout_enum_and_partitions():
    lay = _layout()
    assert lay["access_rights_enum"] == {"0": "ReadOnly", "1": "ReadWrite",
                                         "2": "ReadWriteLocked"}
    parts = lay["partitions"]
    assert set(parts) == {"0x80", "0x81", "0x85"}     # CPS declares exactly these
    assert "0x82" not in parts                         # tuning is NOT codeplug
    assert parts["0x80"]["access"] == "ReadWrite"
    assert parts["0x81"]["access"] == "ReadWriteLocked"
    assert parts["0x85"]["access"] == "ReadWriteLocked"
    assert lay["unresolved_block_calls"] == 0


def test_two_sources_agree_on_partitions_and_counts():
    import json
    cap = json.load(open(MAP))["partitions"]
    lay = _layout()["partitions"]
    writable = {p for p, m in cap.items() if m["writable"]}
    assert writable == set(lay)        # same writable set from both sources
    for p, m in lay.items():           # one CPS block layout per captured object
        assert m["block_layouts"] == cap[p]["observed_objs"], p


def test_requires_unlock_for_locked_partitions():
    pol = PartitionPolicy.load(MAP)
    assert pol.requires_unlock(0x81) and pol.requires_unlock(0x85)
    assert not pol.requires_unlock(0x80)


def test_cps_layout_gate_refuses_undeclared_and_readonly():
    parts = {0x80: {"writable": True, "obj_min": 0, "obj_max": 9999},
             0x90: {"writable": True, "obj_min": 0, "obj_max": 9999},
             0x91: {"writable": True, "obj_min": 0, "obj_max": 9999}}
    pol = PartitionPolicy(parts, cps_layout={0x80: 1, 0x91: 0})
    pol.check(0x80, 5)                                  # declared ReadWrite
    with pytest.raises(WriteSessionError, match="does not declare"):
        pol.check(0x90, 5)                              # capture says ok, CPS doesn't
    with pytest.raises(WriteSessionError, match="ReadOnly"):
        pol.check(0x91, 5)
