import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController, get_cpg_snapshot, diff_snapshots

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
snap_before = get_cpg_snapshot(cpg_path)

dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("scan_list")

# Switch to Tab 2 (Scan List Member Table)
PSM_SETCURSEL = 0x0465
ctypes.windll.user32.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 1, 0)
time.sleep(1.0)

# Inspect controls on tab 2
combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}
print("Combos on tab 2:", [(cid, c['items']) for cid, c in combos.items()])

dc.close()
