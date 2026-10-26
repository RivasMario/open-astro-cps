import pefile
from capstone import *
import struct

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)

# String is at file offset 0x2dad8. Find its VA
str_rva = 0x2dad8 # approximate, let's locate exact section
for section in pe.sections:
    if section.PointerToRawData <= 0x2dad8 < section.PointerToRawData + section.SizeOfRawData:
        str_rva = section.VirtualAddress + (0x2dad8 - section.PointerToRawData)
        break

str_va = pe.OPTIONAL_HEADER.ImageBase + str_rva
print(f"String VA: 0x{str_va:08x}, RVA: 0x{str_rva:08x}")

# Find references to str_va in .text section
text_sec = None
for s in pe.sections:
    if b".text" in s.Name:
        text_sec = s
        break

text_data = text_sec.get_data()
text_base = pe.OPTIONAL_HEADER.ImageBase + text_sec.VirtualAddress

va_bytes = struct.pack("<I", str_va)
refs = []
idx = 0
while True:
    pos = text_data.find(va_bytes, idx)
    if pos == -1:
        break
    refs.append(text_base + pos)
    idx = pos + 1

print(f"References found at VAs: {[hex(r) for r in refs]}")

md = Cs(CS_ARCH_X86, CS_MODE_32)
for ref_va in refs:
    ref_offset = ref_va - text_base
    disasm_start = max(0, ref_offset - 100)
    disasm_end = min(len(text_data), ref_offset + 150)
    code = text_data[disasm_start:disasm_end]
    start_va = text_base + disasm_start
    print(f"\n--- Disassembly around ref 0x{ref_va:08x} ---")
    for ins in md.disasm(code, start_va):
        print(f"0x{ins.address:08x}:  {ins.mnemonic:8s} {ins.op_str}")
