import sys, os, time, ctypes
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()
h, mdi = dc.open_dialog("scan_list")
combos = dc.enum_combos(h)
print(f"Scan List Combos ({len(combos)}):")
for cb in combos:
    print(f"  ID {cb['id']}: cur_sel={cb['cur_sel']}, items={cb['items']}")
dc.close_dialog(h)
dc.close()
