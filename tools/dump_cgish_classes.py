import re

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\cgIsh10c.dll", "rb") as fp:
    data = fp.read()

classes = re.findall(b"\\.\\?AV[a-zA-Z0-9_]+@@", data)
print(f"Total classes: {len(classes)}")
for c in sorted(set(classes)):
    print(c.decode('ascii'))
