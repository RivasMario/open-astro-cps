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

u = ctypes.windll.user32
PSM_SETCURSEL = 0x0465

u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 2, 0)
time.sleep(1.0)

print("[+] Sending WM_COMMAND 32853 (Add Member)...")
u.SendMessageW(dlg_hwnd, 0x0111, 32853, 0)
time.sleep(1.0)

# Check if a dialog or row popped up
modal = dc.find_modal_dialog()
print(f"Modal dialog: 0x{modal:08x}" if modal else "No modal")

time.sleep(1.0)
dc.save()
dc.close()

snap_after = get_cpg_snapshot(cpg_path)
diffs = diff_snapshots(snap_before, snap_after)
print("\n=== SCAN MEMBER DIFFS ===")
for k, v in diffs.items():
    if "0049" in k or "004a" in k or "004c" in k or "0fcf" in k:
        print(f"Object {k}:")
        print(f"  Before: {v['before']}")
        print(f"  After : {v['after']}")
