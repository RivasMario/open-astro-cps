import os, re

depot_dir = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot"

# Let's search all DLLs and EXEs for strings containing "Scan List"
results = {}
for fname in os.listdir(depot_dir):
    if fname.endswith(".dll") or fname.endswith(".exe"):
        fpath = os.path.join(depot_dir, fname)
        try:
            with open(fpath, "rb") as fp:
                data = fp.read()
                matches = re.findall(b"Scan List[a-zA-Z0-9_ ]*", data, re.IGNORECASE)
                if matches:
                    results[fname] = set(m.decode('latin1', errors='ignore') for m in matches[:20])
        except Exception:
            pass

for fname, matches in results.items():
    print(f"=== {fname} ===")
    for m in list(matches)[:10]:
        print(f"  {m}")
