import ctypes
import time
import os, sys

REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "src"))
from depot_auto_mapper import DepotController, get_cpg_snapshot, diff_snapshots

cpg_path = os.path.join(REPO, "backups", "depot_buttons.cpg")
snap_before = get_cpg_snapshot(cpg_path)

dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("scan_list")

combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}

# 1. Set Priority 1 Type to 'Fixed' (index 1)
print("[+] Setting Priority 1 Type to Fixed...")
dc.mutate_combo(dlg_hwnd, mdi_hwnd, combos[19604], 1)

# Re-read combos because 19603 might now be enabled
combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}

# 2. Set Priority 1 Member to '1' (index 1)
print("[+] Setting Priority 1 Member to Channel 1...")
dc.mutate_combo(dlg_hwnd, mdi_hwnd, combos[19603], 1)

# 3. Set Priority 2 Type to 'Fixed' (index 1)
print("[+] Setting Priority 2 Type to Fixed...")
dc.mutate_combo(dlg_hwnd, mdi_hwnd, combos[19606], 1)

combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}

# 4. Set Priority 2 Member to '2' (index 2)
print("[+] Setting Priority 2 Member to Channel 2...")
dc.mutate_combo(dlg_hwnd, mdi_hwnd, combos[19605], 2)

time.sleep(1.0)
dc.save()
dc.close()

snap_after = get_cpg_snapshot(cpg_path)
diffs = diff_snapshots(snap_before, snap_after)
print("\n=== SCAN LIST DIFFS ===")
for k, v in diffs.items():
    if not k.startswith("80:0047:"):
        print(f"Object {k}:")
        print(f"  Before: {v['before']}")
        print(f"  After : {v['after']}")
        print(f"  Changes: {v['changed_bytes']}")
