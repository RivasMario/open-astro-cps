import pefile, struct

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    cgish = fp.read()

# Let's find 0x0ffb layout
p_ffb = struct.pack("<H", 0x0ffb)
matches = [i for i in range(len(cgish)-2) if cgish[i:i+2] == p_ffb]
print("0x0ffb matches in cgIsh10c.dll:", [hex(m) for m in matches])
