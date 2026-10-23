"""Map every CPS codeplug block TYPE to its wire ITEM ID and partition.

Background (docs/CPS_ISH_SCHEMA.md): PatPort.exe builds the codeplug layout. For
each block it looks the block up by its ISH *type* id, then assigns it to a
partition (CcgIshBlkLayout::SetPartitionNum). The id that goes on the RCMP wire
and into .cpg stream tags is a different *item* id. The link lives in the block
builders:

  * PatPort's block lookup (0x7d6dd8 in R20.01.00) dispatches on the type
    through nested jump tables / compare chains to a builder function;
  * most builders hard-code the item id as the first argument of
    CgIshBlkLayoutAttrib(item_id, ...);
  * a shared generic builder instead receives the item id as its 4th argument.

Rather than pattern-match every dispatcher branch, this tool EMULATES the
dispatcher (unicorn) once per block type, stubs imported calls, and stops at the
first internal call -- the builder -- capturing its stack arguments.

Output: schema/block_type_map.json (derived facts only: type, item id,
partition). Verified in tests against the capture-derived partition map and the
.cpg tags of the real backups.

Run (python -P keeps user site-packages):
    python -P tools/patport_block_map.py <PatPort.exe>
Requires: pefile, capstone, unicorn.
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
from unicorn import UC_ARCH_X86, UC_HOOK_CODE, UC_MODE_32, Uc, UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP,
                               UC_X86_REG_ESP)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# PatPort.exe R20.01.00 addresses (found by tools/patport_partition_layout.py's
# call-site analysis and docs/CPS_ISH_SCHEMA.md). Check these if your build differs.
DISPATCH = 0x7d6dd8          # block lookup: (type, flag, flag) -> builder
GENERIC_BUILDER = 0xc47ac2   # shared builder: item id passed as 4th arg
SET_PARTITION = "?SetPartitionNum@CcgIshBlkLayout@@QAEXG@Z"
ADD_PARTITION = "?AddPartition@CcgIshCpLayout@@QAEHGW4AccessRights@@@Z"
ATTRIB_CTOR = "??0CgIshBlkLayoutAttrib@@QAE@GGHH@Z"


def _iat(pe, name):
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in d.imports:
            if imp.name and imp.name.decode() == name:
                return imp.address
    raise SystemExit(f"[-] import not found: {name}")


def _calls(pe, slot):
    base = pe.OPTIONAL_HEADER.ImageBase
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    data, tva = text.get_data(), base + text.VirtualAddress
    needle = b"\xff\x15" + struct.pack("<I", slot)
    i = 0
    while (i := data.find(needle, i)) >= 0:
        yield tva + i
        i += 6


def _window(pe, va, back):
    base = pe.OPTIONAL_HEADER.ImageBase
    for st in range(va - back, va):
        ins = list(_MD.disasm(pe.get_data(st - base, va + 6 - st), st))
        if ins and ins[-1].address == va:
            return ins
    return []


def block_types_by_partition(pe):
    """(type, partition) for every SetPartitionNum call: the type is the id
    pushed for the preceding block lookup, the partition is resolved from the
    per-partition local written right after AddPartition."""
    base = pe.OPTIONAL_HEADER.ImageBase
    var_part = {}
    for va in _calls(pe, _iat(pe, ADD_PARTITION)):
        pushes = [x for x in _window(pe, va, 48) if x.mnemonic == "push"]
        part = int(pushes[-1].op_str, 0)
        for x in _MD.disasm(pe.get_data(va + 6 - base, 40), va + 6):
            m = re.match(r"word ptr \[ebp - (0x[0-9a-f]+)\], (0x[0-9a-f]+)", x.op_str)
            if x.mnemonic == "mov" and m and int(m.group(2), 16) == part:
                var_part[m.group(1)] = part
                break
    out = []
    for va in _calls(pe, _iat(pe, SET_PARTITION)):
        ins = _window(pe, va, 260)
        var = typ = None
        for x in reversed(ins[:-1]):
            m = re.match(r"\w+, word ptr \[ebp - (0x[0-9a-f]+)\]", x.op_str)
            if x.mnemonic in ("mov", "movzx") and m:
                var = m.group(1)
                break
        for k, x in enumerate(ins):
            if x.mnemonic == "call" and x.op_str == f"{DISPATCH:#x}":
                for y in reversed(ins[:k]):
                    if y.mnemonic == "push" and re.fullmatch(r"0x[0-9a-f]+|\d+", y.op_str):
                        typ = int(y.op_str, 0)
                        break
                break
        if typ is None:   # lookup may sit just outside the window: use DoesBlkExist push
            for x in ins:
                if x.mnemonic == "push" and re.fullmatch(r"0x[0-9a-f]+|\d+", x.op_str):
                    typ = int(x.op_str, 0)
                    break
        out.append((typ, var_part.get(var)))
    return out


class _Emu:
    """Run the block-lookup dispatcher for one type; stop at the builder call."""

    def __init__(self, pe):
        self.pe = pe
        self.iat = {i.address for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports}
        base = pe.OPTIONAL_HEADER.ImageBase
        size = (pe.OPTIONAL_HEADER.SizeOfImage + 0xFFF) & ~0xFFF
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.mu.mem_map(base, size)
        self.mu.mem_write(base, pe.get_memory_mapped_image())
        self.stk, self.this, self.ret = 0x60000000, 0x61000000, 0x62000000
        self.mu.mem_map(self.stk - 0x100000, 0x100000)
        self.mu.mem_map(self.this, 0x10000)
        self.mu.mem_map(self.ret, 0x1000)

    def builder_for(self, typ):
        mu, res = self.mu, {}
        esp = self.stk - 0x1000
        for v in (0, 0, typ, self.ret):            # args right-to-left + return
            esp -= 4
            mu.mem_write(esp, struct.pack("<I", v))
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_ECX, self.this)

        def hook(uc, addr, sz, _):
            x = next(_MD.disasm(bytes(uc.mem_read(addr, sz)), addr), None)
            if x is None or x.mnemonic != "call":
                return
            m = re.fullmatch(r"dword ptr \[(0x[0-9a-f]+)\]", x.op_str)
            if m and int(m.group(1), 16) in self.iat:   # imported call: stub it
                uc.reg_write(UC_X86_REG_EAX, 0)
                uc.reg_write(UC_X86_REG_EIP, addr + sz)
                return
            if re.fullmatch(r"0x[0-9a-f]+", x.op_str):
                sp = uc.reg_read(UC_X86_REG_ESP)
                res["builder"] = int(x.op_str, 16)
                res["args"] = [struct.unpack("<I", bytes(uc.mem_read(sp + 4 * k, 4)))[0]
                               for k in range(4)]
                uc.emu_stop()

        h = mu.hook_add(UC_HOOK_CODE, hook)
        try:
            mu.emu_start(DISPATCH, self.ret, count=4000)
        except UcError as e:
            res["error"] = str(e)
        mu.hook_del(h)
        return res


def _attrib_item_id(pe, fn, attrib_slot):
    base = pe.OPTIONAL_HEADER.ImageBase
    pushes = []
    for x in _MD.disasm(pe.get_data(fn - base, 0x600), fn):
        if x.mnemonic == "push":
            pushes.append(x.op_str)
        if x.mnemonic == "call" and x.op_str == f"dword ptr [{attrib_slot:#x}]":
            v = pushes[-1] if pushes else ""
            return int(v, 0) if re.fullmatch(r"0x[0-9a-f]+|\d+", v) else None
        if x.mnemonic.startswith("ret"):
            return None
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pe = pefile.PE(sys.argv[1])
    attrib = _iat(pe, ATTRIB_CTOR)
    emu = _Emu(pe)
    rows, problems = [], []
    for typ, part in block_types_by_partition(pe):
        r = emu.builder_for(typ)
        b = r.get("builder")
        iid, src = None, None
        if b is not None:
            iid = _attrib_item_id(pe, b, attrib)
            src = "attrib-immediate"
            if iid is None and b == GENERIC_BUILDER:
                iid, src = r["args"][3] & 0xFFFF, "generic-builder-arg4"
        if iid is None or part is None:
            problems.append({"type": typ, "partition": part, "builder": b})
        rows.append({"type": typ, "item_id": iid, "partition": part, "source": src})
    rows.sort(key=lambda r: (r["partition"] or 0, r["item_id"] or 0))
    out = {
        "_comment": ("CPS codeplug block TYPE -> wire ITEM ID -> partition, from "
                     "PatPort.exe's block builders (dispatcher emulated). Derived "
                     "facts only. Regenerate with tools/patport_block_map.py."),
        "blocks": [{"item_id": r["item_id"], "type": r["type"],
                    "partition": f"0x{r['partition']:02x}" if r["partition"] is not None else None,
                    "source": r["source"]} for r in rows],
        "unresolved": problems,
    }
    dest = os.path.join(REPO, "schema", "block_type_map.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(f"[+] wrote {dest}: {len(rows)} blocks, {len(problems)} unresolved")
    print("    by partition:", dict(Counter(b["partition"] for b in out["blocks"])))
    print("    sources:", dict(Counter(b["source"] for b in out["blocks"])))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
