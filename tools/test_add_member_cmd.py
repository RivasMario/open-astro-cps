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
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
PSM_SETCURSEL = 0x0465

u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 2, 0)
time.sleep(1.0)

tbl_hwnd = None
tb_hwnd = None

def find_windows(ch, extra):
    global tbl_hwnd, tb_hwnd
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    if 'Scan List Member Table' in tbuf.value:
        tbl_hwnd = ch
    if 'ToolbarWindow32' in cbuf.value:
        tb_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_windows), 0)
print(f"Member Table HWND: 0x{tbl_hwnd:08x}, Toolbar: 0x{tb_hwnd:08x}")

# 1. Send WM_COMMAND 32853 to tbl_hwnd (its direct parent!)
print("[+] Sending WM_COMMAND 32853 to tbl_hwnd...")
u.SendMessageW(tbl_hwnd, 0x0111, 32853, tb_hwnd)
time.sleep(1.5)

# Check if any new dialog or window appeared
def enum_all(ch, extra):
    vis = u.IsWindowVisible(ch)
    if vis:
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tbuf, 256)
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cbuf, 256)
        if tbuf.value:
            print(f"  Visible: {cbuf.value} '{tbuf.value}'")
    return True

print("[+] Windows in Member Table after Add:")
u.EnumChildWindows(tbl_hwnd, WNDENUMPROC(enum_all), 0)

dc.save()
dc.close()

snap_after = get_cpg_snapshot(cpg_path)
diffs = diff_snapshots(snap_before, snap_after)
print("\n=== SCAN MEMBER DIFFS ===")
for k, v in diffs.items():
    if not k.startswith("80:0047:"):
        print(f"Object {k}:")
        print(f"  Before: {v['before']}")
        print(f"  After : {v['after']}")
        print(f"  Changes: {v['changed_bytes']}")
