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

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
PSM_SETCURSEL = 0x0465

u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 2, 0)
time.sleep(1.0)

# Find 'Scan List Member Table' dialog
tbl_hwnd = None
def find_tbl(ch, extra):
    global tbl_hwnd
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    if 'Scan List Member Table' in tbuf.value:
        tbl_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tbl), 0)
print(f"Member Table HWND: 0x{tbl_hwnd:08x}")

# Enumerate children of member table
children = []
def cb(ch, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    vis = u.IsWindowVisible(ch)
    children.append((ch, cid, cbuf.value, tbuf.value, vis))
    return True

u.EnumChildWindows(tbl_hwnd, WNDENUMPROC(cb), 0)
print(f"Children of Member Table ({len(children)}):")
for ch, cid, c, t, vis in children:
    print(f"  Ctrl 0x{ch:08x} ID {cid} (vis={vis}): {c} '{t}'")

dc.close()
