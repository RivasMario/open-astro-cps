import pefile, struct
from capstone import *

dll_path = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll"
pe = pefile.PE(dll_path)
text_sec = [s for s in pe.sections if b".text" in s.Name][0]
text_data = text_sec.get_data()
text_base = pe.OPTIONAL_HEADER.ImageBase + text_sec.VirtualAddress

target_va = 0x10015cd0

calls = []
for i in range(len(text_data) - 5):
    if text_data[i] == 0xe8: # near call
        rel = struct.unpack("<i", text_data[i+1:i+5])[0]
        cur_va = text_base + i
        dest_va = cur_va + 5 + rel
        if dest_va == target_va:
            calls.append(cur_va)

print(f"Calls to 0x{target_va:08x}: {[hex(c) for c in calls]}")

md = Cs(CS_ARCH_X86, CS_MODE_32)
for c in calls:
    off = c - text_base
    code = text_data[max(0, off - 50) : min(len(text_data), off + 30)]
    start_va = text_base + max(0, off - 50)
    print(f"\n--- Caller at 0x{c:08x} ---")
    for ins in md.disasm(code, start_va):
        print(f"0x{ins.address:08x}:  {ins.mnemonic:8s} {ins.op_str}")
