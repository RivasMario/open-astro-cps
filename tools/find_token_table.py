with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

# Let's find where 0x18 (Light), 0x1a (Scan/Zone), 0x19 (Monitor/Power), 0x21 (TalkAround), 0x23 (Unprogrammed)
# are mapped to strings!
# In 0x0020:0:
# 0x18 -> Light
# 0x19 -> Monitor
# 0x1a -> Scan
# 0x21 -> TalkAround/Direct
# 0x23 -> Unprogrammed

# Let's find tables of bytes [18, 19, 1a, 21, 23] or structs containing these byte values
tokens = [0x18, 0x19, 0x1a, 0x21, 0x23]
# Search for arrays or tables with these values
import re

# In PatPortDepot.exe, where are the button token values?
# Let's search for sequences containing 18 19 1a ...
for m in re.finditer(rb'\x18\x19\x1a', raw):
    print(f"Match 18 19 1a at offset 0x{m.start():08x}")

# Or search where 'Light' string pointer is stored in an array
pos_light = raw.find(b'Light\x00')
print(f"Light string at 0x{pos_light:08x}")
