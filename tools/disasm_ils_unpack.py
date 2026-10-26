import pefile, capstone

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)
image_base = pe.OPTIONAL_HEADER.ImageBase
target_off = 0x2dad8

# Find VA of string
for s in pe.sections:
    if s.PointerToRawData <= target_off < s.PointerToRawData + s.SizeOfRawData:
        rva = target_off - s.PointerToRawData + s.VirtualAddress
        va = image_base + rva
        print(f"VA of string: {hex(va)}")
        
        # Find xrefs to string
        va_bytes = va.to_bytes(4, 'little')
        for s2 in pe.sections:
            data = s2.get_data()
            idx = 0
            while True:
                idx = data.find(va_bytes, idx)
                if idx == -1: break
                ref_va = image_base + s2.VirtualAddress + idx
                print(f"Referenced at {hex(ref_va)}")
                
                # Disassemble around ref
                cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
                code_start = max(0, idx - 150)
                code_slice = data[code_start : idx + 100]
                insns = list(cs.disasm(code_slice, image_base + s2.VirtualAddress + code_start))
                for insn in insns:
                    marker = "==>" if insn.address <= ref_va < insn.address + insn.size else "   "
                    print(f"{marker} 0x{insn.address:08x}: {insn.mnemonic:8s} {insn.op_str}")
                idx += 1
        break
