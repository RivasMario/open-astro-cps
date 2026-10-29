import os, re

depot_dir = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot"

for fname in os.listdir(depot_dir):
    if fname.endswith(".dll") or fname.endswith(".exe"):
        fpath = os.path.join(depot_dir, fname)
        try:
            with open(fpath, "rb") as fp:
                data = fp.read()
                matches = re.findall(b"Add [A-Z][a-zA-Z0-9_ ]*", data)
                if matches:
                    relevant = [m.decode('latin1') for m in matches if 'member' in m.lower() or 'channel' in m.lower() or 'scan' in m.lower()]
                    if relevant:
                        print(f"=== {fname} ===")
                        print(set(relevant))
        except Exception:
            pass
