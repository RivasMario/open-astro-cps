import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("buttons")

combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}
for cid, c in combos.items():
    print(f"Control {cid} items: {c['items']}")

dc.close()
