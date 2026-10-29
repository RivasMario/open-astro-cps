import pefile
import struct
import re

with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

# Let's find string table / data section
# String at VA 0x0153xxxx
# file offset = VA - 0x00400000
def get_str(va):
    foff = va - 0x00400000
    if 0 <= foff < len(raw):
        end = raw.find(b'\x00', foff)
        return raw[foff:end].decode('latin1', errors='replace')
    return ''

# Find pattern: push <val>, push <str_va>
# Opcode: 68 xx xx 53 01
results = []
for m in re.finditer(rb'\x68(..)\x00\x00\x68([\x00-\xff][\x00-\xff]\x53\x01)', raw):
    id_val = struct.unpack('<H', m.group(1))[0]
    str_va = struct.unpack('<I', m.group(2))[0]
    s = get_str(str_va)
    if s:
        results.append((m.start(), id_val, s))

print(f"Pattern 1 found: {len(results)}")
for foff, id_val, s in results[:40]:
    print(f"  ID 0x{id_val:04x} ({id_val:4d}): {s}")
