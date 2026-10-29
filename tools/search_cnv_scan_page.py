import pefile, struct
from capstone import *

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
pe = pefile.PE(dll_path)

# Find string "CCnvPerScanRecPage"
with open(dll_path, "rb") as fp:
    data = fp.read()

pos = data.find(b"CCnvPerScanRecPage")
print(f"Position: {hex(pos)}")

# Find section
sec = None
for s in pe.sections:
    if s.PointerToRawData <= pos < s.PointerToRawData + s.SizeOfRawData:
        sec = s
        break

str_rva = sec.VirtualAddress + (pos - sec.PointerToRawData)
str_va = pe.OPTIONAL_HEADER.ImageBase + str_rva
print(f"String VA: 0x{str_va:08x}")

# Find references to str_va in code
va_bytes = struct.pack("<I", str_va)
refs = []
idx = 0
while True:
    p = data.find(va_bytes, idx)
    if p == -1: break
    refs.append(p)
    idx = p + 1

print(f"References: {[hex(r) for r in refs]}")
