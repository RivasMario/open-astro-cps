import re

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe", "rb") as fp:
    data = fp.read()

matches = re.findall(b"C[A-Za-z0-9_]*ScanList[A-Za-z0-9_]*", data)
print(f"Matches for ScanList: {set(m.decode('latin1') for m in matches)}")
