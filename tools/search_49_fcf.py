import pefile, struct

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    cgish = fp.read()

# Search for 0x0049
p49 = struct.pack("<H", 0x0049)
m49 = [i for i in range(len(cgish)-2) if cgish[i:i+2] == p49]
print("0x0049 matches:", [hex(m) for m in m49])

p_fcf = struct.pack("<H", 0x0fcf)
m_fcf = [i for i in range(len(cgish)-2) if cgish[i:i+2] == p_fcf]
print("0x0fcf matches:", [hex(m) for m in m_fcf])
