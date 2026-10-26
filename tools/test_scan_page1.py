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

PSM_SETCURSEL = 0x0465 # WM_USER + 101

print("[+] Sending PSM_SETCURSEL 1 to property sheet...")
u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 1, 0)
time.sleep(1.5)

# Inspect all controls
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
print(f"Controls after PSM_SETCURSEL 1 ({len(all_ctrls)}):")
for ch, cid, c, t, vis in all_ctrls:
    if vis and t:
        print(f"  Visible: ID {cid}: {c} '{t}'")

dc.close()
