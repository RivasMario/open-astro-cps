import pefile, capstone

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
target_va = 0x963100
target_rva = target_va - image_base

for s in pe.sections:
    if s.VirtualAddress <= target_rva < s.VirtualAddress + s.Misc_VirtualSize:
        offset = target_rva - s.VirtualAddress
        data = s.get_data()
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        code_slice = data[offset : offset + 1500]
        for insn in cs.disasm(code_slice, target_va):
            if 'push' in insn.mnemonic and '0x162e' in insn.op_str:
                print(f"0x{insn.address:08x}: {insn.mnemonic:8s} {insn.op_str}")
        break
