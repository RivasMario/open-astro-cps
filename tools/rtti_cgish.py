import pefile, struct

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)
rdata_sec = [s for s in pe.sections if b".rdata" in s.Name or b".data" in s.Name]

# Search for 0x1001dacc
vtable_va = 0x1001dacc
print(f"Vtable VA: 0x{vtable_va:08x}")

# In MSVC RTTI, vtable[-1] (at vtable_va - 4) is pointer to RTTI Complete Object Locator
col_rva = vtable_va - pe.OPTIONAL_HEADER.ImageBase - 4
data = pe.get_memory_mapped_image()
col_ptr = struct.unpack("<I", data[col_rva : col_rva + 4])[0]
print(f"COL ptr: 0x{col_ptr:08x}")

col_rva = col_ptr - pe.OPTIONAL_HEADER.ImageBase
type_desc_ptr = struct.unpack("<I", data[col_rva + 12 : col_rva + 16])[0]
print(f"TypeDescriptor ptr: 0x{type_desc_ptr:08x}")

td_rva = type_desc_ptr - pe.OPTIONAL_HEADER.ImageBase
mangled_name = data[td_rva + 8 : td_rva + 100].split(b"\x00")[0]
print(f"Mangled class name: {mangled_name.decode('ascii', errors='ignore')}")
