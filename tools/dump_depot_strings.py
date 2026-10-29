with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    fp.seek(0x0113b500)
    data = fp.read(0x4000)

offset = 0x0113b500
i = 0
strings = []
while i < len(data):
    if 0x20 <= data[i] <= 0x7e:
        start = i
        while i < len(data) and 0x20 <= data[i] <= 0x7e:
            i += 1
        s = data[start:i].decode('latin1')
        if len(s) >= 2:
            strings.append((offset + start, s))
    else:
        i += 1

print(f"Total strings extracted: {len(strings)}")
# Write them to an artifact or markdown file
with open('C:/Users/skyway/open-astro-cps/tools/depot_raw_strings.txt', 'w', encoding='utf-8') as out:
    for foff, s in strings:
        out.write(f"0x{foff:08x}: {s}\n")

print("Saved to tools/depot_raw_strings.txt")
