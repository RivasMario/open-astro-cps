import pefile

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)

if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    print(f"Total exports: {len(pe.DIRECTORY_ENTRY_EXPORT.symbols)}")
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        name = exp.name.decode('ascii') if exp.name else f"ord_{exp.ordinal}"
        print(f"  0x{pe.OPTIONAL_HEADER.ImageBase + exp.address:08x}: {name}")
