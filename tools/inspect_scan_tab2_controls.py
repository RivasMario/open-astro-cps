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

# Enum all buttons/controls on the dialog
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

ctrls = []
def cb(ch, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    vis = u.IsWindowVisible(ch)
    ctrls.append((ch, cid, cbuf.value, tbuf.value, vis))
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(cb), 0)
print(f"Total controls: {len(ctrls)}")
for ch, cid, c, t, vis in ctrls:
    if vis and (c in ('Button', 'ComboBox') or 'Add' in t or 'Member' in t):
        print(f"  Ctrl 0x{ch:08x} ID {cid}: {c} '{t}'")

dc.close()
