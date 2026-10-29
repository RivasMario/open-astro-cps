import pefile, capstone

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
target_va = 0x96a6f9
target_rva = target_va - image_base

for s in pe.sections:
    if s.VirtualAddress <= target_rva < s.VirtualAddress + s.Misc_VirtualSize:
        offset = target_rva - s.VirtualAddress
        data = s.get_data()
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        code_slice = data[offset : offset + 300]
        print(f"Disassembly of 0x{target_va:08x}:")
        for insn in cs.disasm(code_slice, target_va):
            print(f"  0x{insn.address:08x}: {insn.mnemonic:8s} {insn.op_str}")
            if insn.mnemonic in ('ret', 'retf'):
                break
        break
