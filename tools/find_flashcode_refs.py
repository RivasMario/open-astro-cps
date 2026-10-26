import pefile

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
rva = None
target_file_offset = 19066492

for s in pe.sections:
    if s.PointerToRawData <= target_file_offset < s.PointerToRawData + s.SizeOfRawData:
        rva = target_file_offset - s.PointerToRawData + s.VirtualAddress
        break

va = image_base + rva
print(f"VA of 'Invalid FLASHcode!': {hex(va)}")

va_bytes = va.to_bytes(4, 'little')
for s in pe.sections:
    data = s.get_data()
    idx = 0
    while True:
        idx = data.find(va_bytes, idx)
        if idx == -1:
            break
        ref_rva = s.VirtualAddress + idx
        ref_va = image_base + ref_rva
        print(f"Referenced in section {s.Name.decode().strip(chr(0))} at {hex(ref_va)}")
        idx += 1
