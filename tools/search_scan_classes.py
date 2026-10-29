import re

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe", "rb") as fp:
    data = fp.read()

classes = re.findall(b"\\.\\?AV[a-zA-Z0-9_]*Scan[a-zA-Z0-9_]*@@", data)
print(f"Total Scan classes: {len(classes)}")
for c in sorted(set(classes))[:30]:
    print(c.decode('ascii'))
