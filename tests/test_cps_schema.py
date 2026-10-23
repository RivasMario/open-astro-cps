"""Cross-validation of the CPS-derived schema against real data.

schema/block_type_map.json comes from PatPort.exe (tools/patport_block_map.py);
the .cpg Strm_0 directory and the live capture are independent sources. Every
check here compares Motorola's code against bytes from the user's own radios.
"""
import glob
import json
import os
from collections import Counter, defaultdict

import pytest

olefile = pytest.importorskip("olefile")

from open_astro.parsers.cpg_parser import CpgParser
from open_astro.protocol import rcmp
from open_astro.protocol.write_session import CpgWriteAssembler, PartitionPolicy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUPS = sorted(glob.glob(os.path.join(REPO, "backups", "*.cpg")))
BLOCKS = json.load(open(os.path.join(REPO, "schema", "block_type_map.json")))["blocks"]
ITEM_PART = {b["item_id"]: int(b["partition"], 16) for b in BLOCKS}


def _capture_objects():
    cap = defaultdict(set)
    for f in glob.glob(os.path.join(REPO, "captures", "cps_*_decoded.json")):
        hx = json.load(open(f)).get("OUT host->radio", {}).get("rcmp_stream_hex", "")
        for r in (rcmp.iter_records(bytes.fromhex(hx)) if hx else []):
            if int.from_bytes(r[:2], "big") in (rcmp.OP_READ, rcmp.OP_WRITE) and len(r) >= 7:
                cap[r[2]].add(int.from_bytes(r[3:5], "big"))
    return cap


def test_block_map_complete_and_unique():
    assert len(BLOCKS) == 169
    assert all(b["item_id"] is not None and b["partition"] for b in BLOCKS)
    assert len({b["item_id"] for b in BLOCKS}) == 169          # no duplicate ids
    assert len({b["type"] for b in BLOCKS}) == 169             # no duplicate types
    assert Counter(b["partition"] for b in BLOCKS) == {"0x80": 164, "0x81": 3, "0x85": 2}


def test_block_map_equals_live_capture_per_partition():
    cap = _capture_objects()
    if not cap:
        pytest.skip("no captures")
    for part in (0x80, 0x81, 0x85):
        mapped = {i for i, p in ITEM_PART.items() if p == part}
        assert mapped == cap[part], f"partition 0x{part:02x}"


def test_known_anchor_types():
    by_type = {b["type"]: b["item_id"] for b in BLOCKS}
    assert (by_type[24], by_type[43], by_type[243]) == (4100, 4101, 4102)   # 0x81
    assert (by_type[239], by_type[238]) == (4798, 4799)                      # 0x85


@pytest.mark.parametrize("cpg", BACKUPS, ids=[os.path.basename(b) for b in BACKUPS])
def test_directory_matches_streams_and_cps_partitions(cpg):
    p = CpgParser(cpg)
    try:
        directory = p.directory()
        objs = {int(o["name"].split("_")[-1]): o for o in p.objects()}
    finally:
        p.close()
    assert directory and len(directory) == len(objs)
    for d in directory:
        o = objs[d["stream"]]
        assert (o["tag"], o["instance"], o["stored_crc"]) == \
            (d["item_id"], d["instance"], d["stream_crc"])
        assert o["partition"] == d["partition"]
        # the file's partition for the object == the partition CPS assigns its block
        assert ITEM_PART[d["item_id"]] == d["partition"]


def test_assembler_gets_partitions_from_cpg_without_capture():
    cpg = os.path.join(REPO, "backups", "205CFR2930.cpg")
    asm = CpgWriteAssembler.from_cpg(cpg, policy=PartitionPolicy.load())  # no part_map
    parts = Counter(w.part for w in asm.objects)
    assert parts == {0x80: 143, 0x81: 3}
    assert len(asm.write_records()) == 146      # every object passes the policy
