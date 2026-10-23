"""Extract the codeplug partition layout that Motorola CPS itself declares.

CPS (PatPort.exe) builds the codeplug layout at runtime with the ISH engine in
cgIsh10c.dll:

  * CcgIshCpLayout::AddPartition(WORD partition, AccessRights rights)
      -- one call per codeplug partition, with immediate arguments;
  * CcgIshBlkLayout::SetPartitionNum(WORD partition)
      -- one call per block layout, assigning each block to a partition.

The AccessRights enum is decoded from cgIsh10c.dll's own comparators
(CcgIshBlkLayout::IsReadOnly / IsReadWrite / IsReadWriteLocked compare the
rights field against 0 / 1 / 2).

This script finds those call sites by their import-table slots, reads the
pushed immediates, and writes schema/patport_layout.json. Only DERIVED FACTS
are written (partition numbers, access rights, block counts) -- never Motorola
code or data. The binaries are NOT in the repo; point the script at your own
CPS install / extracted cab.

Run (python -P keeps user site-packages for pefile/capstone):
    python -P tools/patport_partition_layout.py <PatPort.exe> <cgIsh10c.dll>
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from collections import Counter

import capstone
import pefile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

ADD_PARTITION = "?AddPartition@CcgIshCpLayout@@QAEHGW4AccessRights@@@Z"
SET_PARTITION = "?SetPartitionNum@CcgIshBlkLayout@@QAEXG@Z"
_RIGHTS_FUNCS = {
    "?IsReadOnly@CcgIshBlkLayout@@QBEHXZ": "ReadOnly",
    "?IsReadWrite@CcgIshBlkLayout@@QBEHXZ": "ReadWrite",
    "?IsReadWriteLocked@CcgIshBlkLayout@@QBEHXZ": "ReadWriteLocked",
}


def _iat_slot(pe: pefile.PE, name: str) -> int:
    for d in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        for imp in d.imports:
            if imp.name and imp.name.decode() == name:
                return imp.address
    raise SystemExit(f"[-] import not found: {name}")


def _call_sites(pe: pefile.PE, slot: int):
    base = pe.OPTIONAL_HEADER.ImageBase
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    data, tva = text.get_data(), base + text.VirtualAddress
    needle = b"\xff\x15" + struct.pack("<I", slot)   # call dword ptr [slot]
    i = 0
    while (i := data.find(needle, i)) >= 0:
        yield tva + i
        i += 6


def _window(pe: pefile.PE, va: int, back: int):
    """Disassemble backwards from a call: the first start that decodes cleanly
    onto the call instruction."""
    base = pe.OPTIONAL_HEADER.ImageBase
    for st in range(va - back, va):
        ins = list(_MD.disasm(pe.get_data(st - base, va + 6 - st), st))
        if ins and ins[-1].address == va:
            return ins
    return []


def _after(pe: pefile.PE, va: int, n: int = 40):
    base = pe.OPTIONAL_HEADER.ImageBase
    return list(_MD.disasm(pe.get_data(va - base, n), va))


def access_rights_enum(cgish_path: str) -> dict:
    """Decode the AccessRights enum from cgIsh10c.dll's comparators."""
    pe = pefile.PE(cgish_path)
    base = pe.OPTIONAL_HEADER.ImageBase
    exports = {e.name.decode(): base + e.address
               for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    enum = {}
    for fn, label in _RIGHTS_FUNCS.items():
        ins = list(_MD.disasm(pe.get_data(exports[fn] - base, 32), exports[fn]))
        value = None
        for x in ins:
            if x.mnemonic == "test" and x.op_str.split(",")[0] == x.op_str.split(",")[-1].strip():
                value = 0          # test reg, reg ; sete -> compares against 0
            m = re.match(r"\w+, (0x[0-9a-f]+|\d+)$", x.op_str)
            if x.mnemonic == "cmp" and m:
                value = int(m.group(1), 0)
            if x.mnemonic.startswith("ret"):
                break
        if value is None:
            raise SystemExit(f"[-] could not decode {label} from {fn}")
        enum[value] = label
    return enum


def partition_layout(patport_path: str, enum: dict) -> dict:
    pe = pefile.PE(patport_path)
    add_slot = _iat_slot(pe, ADD_PARTITION)
    set_slot = _iat_slot(pe, SET_PARTITION)

    partitions = {}
    var_part = {}       # stack var holding the partition number -> partition
    for va in _call_sites(pe, add_slot):
        pushes = [x for x in _window(pe, va, 48) if x.mnemonic == "push"]
        if len(pushes) < 2:
            raise SystemExit(f"[-] AddPartition @ {va:#x}: arguments not found")
        # thiscall, args pushed right-to-left: push rights; push partition
        part = int(pushes[-1].op_str, 0)
        rights = int(pushes[-2].op_str, 0)
        partitions[part] = {"access_rights": rights,
                            "access": enum.get(rights, f"unknown({rights})")}
        for x in _after(pe, va + 6):
            m = re.match(r"word ptr \[ebp - (0x[0-9a-f]+)\], (0x[0-9a-f]+)", x.op_str)
            if x.mnemonic == "mov" and m and int(m.group(2), 16) == part:
                var_part[m.group(1)] = part
                break

    blocks = Counter()
    unresolved = 0
    for va in _call_sites(pe, set_slot):
        var = None
        for x in reversed(_window(pe, va, 260)[:-1]):
            m = re.match(r"\w+, word ptr \[ebp - (0x[0-9a-f]+)\]", x.op_str)
            if x.mnemonic in ("mov", "movzx") and m:
                var = m.group(1)
                break
        if var in var_part:
            blocks[var_part[var]] += 1
        else:
            unresolved += 1
    for part, n in blocks.items():
        partitions.setdefault(part, {})["block_layouts"] = n
    return {"partitions": partitions, "unresolved_block_calls": unresolved}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    patport, cgish = sys.argv[1], sys.argv[2]
    enum = access_rights_enum(cgish)
    layout = partition_layout(patport, enum)
    out = {
        "_comment": ("Codeplug partition layout as declared by Motorola CPS "
                     "(PatPort.exe -> cgIsh10c.dll CcgIshCpLayout::AddPartition / "
                     "CcgIshBlkLayout::SetPartitionNum). Derived facts only. "
                     "Regenerate with tools/patport_partition_layout.py."),
        "access_rights_enum": {str(k): v for k, v in sorted(enum.items())},
        "partitions": {f"0x{p:02x}": meta for p, meta in sorted(layout["partitions"].items())},
        "unresolved_block_calls": layout["unresolved_block_calls"],
    }
    dest = os.path.join(REPO, "schema", "patport_layout.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"[+] wrote {dest}")
    print(f"    AccessRights enum: {out['access_rights_enum']}")
    for p, meta in out["partitions"].items():
        print(f"    {p}: {meta}")
    if out["unresolved_block_calls"]:
        print(f"[!] {out['unresolved_block_calls']} SetPartitionNum calls unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
