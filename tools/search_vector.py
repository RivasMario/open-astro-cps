import pefile, struct

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe", "rb") as fp:
    data = fp.read()

pos = data.find(b"CnvPerScanListVector")
print("Position:", hex(pos))
start = max(0, pos - 50)
end = min(len(data), pos + 100)
print("Context:", data[start:end])
