with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    cgish = fp.read()

for m in [0x53b3, 0x5873, 0x981c, 0xe843, 0x14c33]:
    start = max(0, m - 30)
    end = min(len(cgish), m + 30)
    print(f"--- Context at {hex(m)} ---")
    print(cgish[start:end])
