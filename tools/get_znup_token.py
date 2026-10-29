import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController, get_cpg_snapshot, diff_snapshots

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
snap_before = get_cpg_snapshot(cpg_path)

dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("buttons")

combos = {c['id']: c for c in dc.enum_combos(dlg_hwnd)}
c15601 = combos[15601]

# Find index of 'ZnUp'
znup_idx = c15601['items'].index('ZnUp')
print(f"Setting Control 15601 to 'ZnUp' (index {znup_idx})...")
dc.mutate_combo(dlg_hwnd, mdi_hwnd, c15601, znup_idx)

time.sleep(1.0)
dc.save()
dc.close()

snap_after = get_cpg_snapshot(cpg_path)
diffs = diff_snapshots(snap_before, snap_after)
print("\n=== BUTTON DIFFS ===")
for k, v in diffs.items():
    if "0020" in k:
        print(f"Object {k}: {v['changed_bytes']}")
