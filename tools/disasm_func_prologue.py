from capstone import *
import pefile

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)
text_sec = [s for s in pe.sections if b".text" in s.Name][0]
text_data = text_sec.get_data()
text_base = pe.OPTIONAL_HEADER.ImageBase + text_sec.VirtualAddress

md = Cs(CS_ARCH_X86, CS_MODE_32)
# Disassemble from 0x10015ca0 to 0x10015cf2
start_va = 0x10015ca0
code = text_data[start_va - text_base : 0x10015cf2 - text_base]
for ins in md.disasm(code, start_va):
    print(f"0x{ins.address:08x}:  {ins.mnemonic:8s} {ins.op_str}")
