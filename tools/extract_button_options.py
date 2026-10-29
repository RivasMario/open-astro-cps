import pefile
import struct

with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

pe = pefile.PE(data=raw)
data_sec = [s for s in pe.sections if s.Name.decode().strip('\x00') == '.data'][0]
va_to_file = lambda va: data_sec.PointerToRawData + (va - 0x00400000 - data_sec.VirtualAddress)

def get_str(va):
    try:
        foff = va_to_file(va)
        if 0 <= foff < len(raw):
            end = raw.find(b'\x00', foff)
            return raw[foff:end].decode('latin1', errors='replace')
    except:
        pass
    return None

# Let's search around 0x00153000 - 0x0015a000 for button entries
# Pattern: push <string_va>, push <id>, etc.
# Or let's scan for all strings pushed in that function
# Let's find every `push 0x0153xxxx`
import re
items = []
for m in re.finditer(rb'\x68([\x00-\xff][\x00-\xff]\x53\x01)', raw):
    str_va = struct.unpack('<I', m.group(1))[0]
    s = get_str(str_va)
    if s and len(s) >= 2:
        # Check what was pushed right before or after
        # 10 bytes before and 20 bytes after
        idx = m.start()
        context = raw[max(0, idx-16):min(len(raw), idx+24)]
        items.append((idx, str_va, s, context.hex()))

print(f"Total string pushes found: {len(items)}")

# Let's filter for button-related strings:
keywords = ['Light', 'Monitor', 'Scan', 'TalkAround', 'Power', 'Emergency', 'Phone',
            'Unprogrammed', 'Call', 'Volume', 'Mute', 'Lock', 'ZnUp', 'ZnDn', 'Select', 'Direct']
btn_items = [it for it in items if any(k.lower() in it[2].lower() for k in keywords)]
print(f"Button-related items: {len(btn_items)}")

# Group by function or address range
seen = set()
for foff, va, s, ctx in btn_items:
    if s not in seen:
        seen.add(s)
        print(f"  {s:<25} (VA 0x{va:08x}, at code 0x{foff:08x})")
