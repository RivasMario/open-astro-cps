import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController, get_cpg_snapshot, diff_snapshots

dc = DepotController(os.path.join(repo, "backups", "depot_fuzzer_work.cpg"))
dc.launch()

dlg_hwnd, mdi = dc.open_dialog("conv_pers")
u = ctypes.windll.user32
PSM_SETCURSEL = 0x0465
u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 9, 0)
time.sleep(0.5)

combos = dc.enum_combos(dlg_hwnd)
c16138 = [cb for cb in combos if cb['id'] == 16138][0]
print("Combo 16138 before:", c16138)

snap_before = get_cpg_snapshot(dc.target_cpg)
dc.mutate_combo(dlg_hwnd, mdi, c16138, 1) # Select '1'
dc.save()
time.sleep(0.5)
snap_after = get_cpg_snapshot(dc.target_cpg)

diffs = diff_snapshots(snap_before, snap_after)
print("\nExact diffs when setting Scan List to 1:")
for k, v in diffs.items():
    print(f"  {k}:")
    for cb in v['changed_bytes']:
        print(f"    Offset {cb['offset']}: {cb['before']} -> {cb['after']}")

dc.close()
