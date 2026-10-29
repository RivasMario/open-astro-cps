import pefile, struct

# Let's search cgIsh10c.dll for the item ID 0x0ff1
with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    cgish = fp.read()

# Item ID is 0x0ff1 (or 4081).
pattern = struct.pack("<H", 0x0ff1)
matches = [i for i in range(len(cgish)-2) if cgish[i:i+2] == pattern]
print(f"Matches for 0x0ff1 in cgIsh10c.dll: {[hex(m) for m in matches]}")
