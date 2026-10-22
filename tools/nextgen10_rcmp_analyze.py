#!/usr/bin/env python3
"""Static analysis of NextGen10.dll for OpenAstro CPS: extract RCMP opcode
numbers and partition/ISH constants. Reads the binary by path only; never
executes it. Run with: python -P ng_analyze.py <stage> <path-to-NextGen10.dll>
"""
import sys, struct, re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

stage = sys.argv[1]
path = sys.argv[2]

pe = pefile.PE(path, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.__data__  # whole file bytes

# section table
secs = []
for s in pe.sections:
    nm = s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((nm, s.VirtualAddress, s.Misc_VirtualSize,
                 s.PointerToRawData, s.SizeOfRawData))

def rva_to_off(rva):
    for nm, va, vs, po, rs in secs:
        if va <= rva < va + max(vs, rs):
            return po + (rva - va)
    return None

def off_to_rva(off):
    for nm, va, vs, po, rs in secs:
        if po <= off < po + rs:
            return va + (off - po)
    return None

text = [(nm, va, vs, po, rs) for (nm, va, vs, po, rs) in secs if nm in (".text", "CODE")]

if stage == "layout":
    print(f"ImageBase = 0x{base:08X}  file_size={len(data)}")
    for nm, va, vs, po, rs in secs:
        print(f"  {nm:8s} RVA=0x{va:06X} vsize=0x{vs:06X} rawoff=0x{po:06X} rawsz=0x{rs:06X} "
              f"VA=0x{base+va:08X}..0x{base+va+vs:08X}")

elif stage == "strings":
    # dump ascii strings >=4 with VA, filtered by keywords given after path
    kws = [k.lower() for k in sys.argv[3:]] if len(sys.argv) > 3 else None
    for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
        s = m.group().decode("latin1")
        if kws and not any(k in s.lower() for k in kws):
            continue
        rva = off_to_rva(m.start())
        va = base + rva if rva is not None else 0
        print(f"0x{va:08X} off=0x{m.start():06X} {s}")

elif stage == "xref":
    # find 4-byte LE refs in .text to the VA of each string whose text contains needle(s)
    needles = sys.argv[3:]
    # build string table
    strs = []
    for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
        s = m.group().decode("latin1")
        if any(n in s for n in needles):
            rva = off_to_rva(m.start())
            if rva is not None:
                strs.append((base + rva, s))
    for va, s in strs:
        imm = struct.pack("<I", va)
        hits = []
        for nm, tva, vs, po, rs in text:
            raw = data[po:po+rs]
            idx = 0
            while True:
                j = raw.find(imm, idx)
                if j < 0:
                    break
                hits.append(base + tva + j)
                idx = j + 1
        print(f"STR 0x{va:08X} {s!r}  xrefs={len(hits)} " +
              " ".join(f"0x{h:08X}" for h in hits[:8]))

elif stage == "disasm":
    # disassemble a window: VA start, nbytes
    start_va = int(sys.argv[3], 16)
    nbytes = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x120
    rva = start_va - base
    off = rva_to_off(rva)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    code = data[off:off+nbytes]
    for insn in md.disasm(code, start_va):
        print(f"0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")

elif stage == "immscan":
    # count/locate push/mov of specific 16/32-bit immediates in .text
    wanted = [int(x, 16) for x in sys.argv[3:]]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for nm, tva, vs, po, rs in text:
        for insn in md.disasm(data[po:po+rs], base + tva):
            if insn.mnemonic in ("push", "mov", "cmp") and insn.op_str:
                m = re.search(r"0x([0-9a-f]+)$", insn.op_str)
                if m:
                    v = int(m.group(1), 16)
                    if v in wanted:
                        print(f"0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
