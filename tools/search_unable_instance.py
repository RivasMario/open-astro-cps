import os, re

depot_dir = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot"

pattern = b"unable to determine instance"

for fname in os.listdir(depot_dir):
    if fname.endswith(".dll") or fname.endswith(".exe"):
        fpath = os.path.join(depot_dir, fname)
        try:
            with open(fpath, "rb") as fp:
                data = fp.read()
                matches = [m.start() for m in re.finditer(pattern, data, re.IGNORECASE)]
                if matches:
                    print(f"Found in {fname} at offsets: {[hex(m) for m in matches]}")
                    for m in matches:
                        start = max(0, m - 50)
                        end = min(len(data), m + 150)
                        print(f"  Context: {data[start:end]}")
        except Exception as e:
            pass
