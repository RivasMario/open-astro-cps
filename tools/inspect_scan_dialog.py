import ctypes
import time
import os, sys

REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController, DIALOG_COMMANDS

cpg_path = os.path.join(REPO, "backups", "depot_buttons.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("scan_list")

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

# Enumerate all controls in Scan List dialog (buttons, tabs, lists, combos)
all_ctrls = []
def cb(ch, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    vis = u.IsWindowVisible(ch)
    all_ctrls.append((ch, cid, cbuf.value, tbuf.value, vis))
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(cb), 0)
print(f"Total controls in Scan List dialog: {len(all_ctrls)}")
for ch, cid, c, t, vis in all_ctrls:
    print(f"  Ctrl 0x{ch:08x} ID {cid} (vis={vis}): {c} '{t}'")

dc.close()
