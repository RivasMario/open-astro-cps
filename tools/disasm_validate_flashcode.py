import pefile, capstone

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
target_va = 0x96414d
target_rva = target_va - image_base

# Find section
for s in pe.sections:
    if s.VirtualAddress <= target_rva < s.VirtualAddress + s.Misc_VirtualSize:
        offset = target_rva - s.VirtualAddress
        data = s.get_data()
        start = max(0, offset - 150)
        end = min(len(data), offset + 150)
        
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        code_slice = data[start:end]
        code_va = image_base + s.VirtualAddress + start
        
        print(f"Disassembly around {hex(target_va)}:")
        for insn in cs.disasm(code_slice, code_va):
            marker = "==>" if insn.address <= target_va < insn.address + insn.size else "   "
            print(f"{marker} 0x{insn.address:08x}: {insn.mnemonic} {insn.op_str}")
        break
