import os

depot_dir = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot"
for name in ["patphopt.mdf", "patphopt_a.mdf"]:
    p = os.path.join(depot_dir, name)
    with open(p, "rb") as f:
        data = f.read()
    print(f"{name}: len={len(data)}")
    print("  First 200 bytes:", data[:200])
