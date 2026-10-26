with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

import re
import struct

# In 0x00153000 to 0x00155000:
# Let's find every instruction that pushes a string in block 1 (0x0153bed8 - 0x0153c0bc)
# Opcode: 68 <VA>
# And let's see what is pushed before/after!

entries = []
for str_va in range(0x0153bed8, 0x0153c0cc, 4):
    target = struct.pack('<I', str_va)
    # search in raw
    pos = 0
    while True:
        idx = raw.find(target, pos)
        if idx == -1: break
        # check if it's push (0x68 before it)
        if idx > 0 and raw[idx-1] == 0x68:
            # get surrounding 30 bytes
            chunk = raw[idx-16:idx+20]
            entries.append((idx-1, str_va, chunk))
        pos = idx + 1

# Let's read string at str_va
def get_str(va):
    foff = va - 0x00400000
    end = raw.find(b'\x00', foff)
    return raw[foff:end].decode('latin1', errors='replace')

print(f"Found {len(entries)} push references:")
import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for foff, str_va, chunk in sorted(entries, key=lambda x: x[0]):
    name = get_str(str_va)
    # disassemble 30 bytes around foff
    code = raw[foff-10:foff+25]
    instrs = [f"{ins.mnemonic} {ins.op_str}" for ins in md.disasm(code, foff-10)]
    print(f"0x{foff:08x} | {name:<20} | {'; '.join(instrs)}")
