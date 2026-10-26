import re

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\Rud50c.dll", "rb") as fp:
    data = fp.read()

matches = re.findall(b"Scan[a-zA-Z0-9_]*", data)
print(f"Matches in Rud50c: {set(m.decode('latin1') for m in matches[:50])}")
