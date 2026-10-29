import struct

with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

# Let's find the table at file offset around 0x0072ef00
# Notice the 32-bit pointers:
# e.g. at 0x0072ef00 - let's see how many pointers there are
table_offset = 0x0072ee00
# Search for the byte sequence 00 01 02 03 04 6d 6d 05
token_arr_pos = raw.find(b'\x00\x01\x02\x03\x04\x6d\x6d\x05')
print(f"Token array starts at file offset 0x{token_arr_pos:08x}")

# The pointers are right before it!
# How many pointers?
ptr_pos = token_arr_pos
# Go backwards reading 4-byte pointers until invalid VA
ptrs = []
p = token_arr_pos - 4
while p >= 0:
    val = struct.unpack('<I', raw[p:p+4])[0]
    # Check if val is a valid VA in PE (0x00400000 - 0x01800000)
    if 0x00400000 <= val <= 0x01800000:
        ptrs.append((p, val))
        p -= 4
    else:
        break

ptrs.reverse()
print(f"Found {len(ptrs)} string pointers before token array")

def get_str(va):
    foff = va - 0x00400000
    if 0 <= foff < len(raw):
        end = raw.find(b'\x00', foff)
        return raw[foff:end].decode('latin1', errors='replace')
    return ''

tokens = raw[token_arr_pos:token_arr_pos+len(ptrs)]
results = []
for idx, (p_off, va) in enumerate(ptrs):
    s = get_str(va)
    tok = tokens[idx] if idx < len(tokens) else None
    results.append((idx, tok, s, hex(va)))

for idx, tok, s, va in results[:60]:
    print(f"Index {idx:2d} | Token 0x{tok:02x} ({tok:2d}) | {s:<30} (VA {va})")
