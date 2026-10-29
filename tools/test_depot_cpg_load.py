import os, sys, time
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

test_cpg = os.path.join(REPO, "backups", "407CHT0214.cpg")

dc = DepotController(test_cpg)
print(f"[+] Testing open {test_cpg} in Depot...")
dc.launch()
print("[+] Succeeded! No modal error dialog.")
dc.close()
