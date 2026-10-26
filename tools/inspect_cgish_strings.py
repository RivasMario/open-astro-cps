with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    cgish = fp.read()

start = 0x2f0e0
end = 0x2f550
print(cgish[start:end])
