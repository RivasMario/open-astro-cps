with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

# Let's find the function prologue before 0x00553000
# 55 8b ec (push ebp; mov ebp, esp)
entry = None
for p in range(0x00152000, 0x00153000):
    if raw[p:p+3] == b'\x55\x8b\xec':
        entry = p

print(f"Function entry point before 0x00153000: 0x{entry:08x} (VA 0x{0x00400000+entry:08x})")

# Let's see all calls to 0x124a162 or similar registration functions in this function
import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Disassemble from 0x00153cd0 backwards 40 bytes to see the exact pattern of one button
code = raw[0x00153ca0:0x00153d10]
for ins in md.disasm(code, 0x00400000 + 0x00153ca0):
    print(f"0x{ins.address:08x}: {ins.mnemonic:<7} {ins.op_str}")
