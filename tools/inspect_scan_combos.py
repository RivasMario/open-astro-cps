import ctypes
import time
import os, sys

REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "depot_buttons.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("scan_list")

combos = dc.enum_combos(dlg_hwnd)
print(f"Total combos on General page: {len(combos)}")
for c in combos:
    cur = c['cur_sel']
    txt = c['items'][cur] if 0 <= cur < len(c['items']) else str(cur)
    print(f"  Combo ID {c['id']} (Current: '{txt}'):")
    for idx, it in enumerate(c['items']):
        print(f"    [{idx}] {it}")

dc.close()
