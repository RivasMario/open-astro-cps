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

tab_ctrl = None
def find_tab(ch, extra):
    global tab_ctrl
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if cbuf.value == 'SysTabControl32':
        tab_ctrl = ch
    return True
u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tab), 0)

TCM_GETITEMCOUNT = 0x1304
TCM_SETCURSEL = 0x130C
WM_NOTIFY = 0x004E
TCN_SELCHANGE = -551 # 0xFFFFFDD9

count = u.SendMessageW(tab_ctrl, TCM_GETITEMCOUNT, 0, 0)
print(f"Tab count: {count}")

# Switch to Tab 1 (Members)
print("[+] Switching to Tab 1...")
u.SendMessageW(tab_ctrl, TCM_SETCURSEL, 1, 0)
# Send TCN_SELCHANGE notification to dialog
class NMHDR(ctypes.Structure):
    _fields_ = [('hwndFrom', ctypes.c_void_p), ('idFrom', ctypes.c_uint), ('code', ctypes.c_int)]

hdr = NMHDR(tab_ctrl, 12320, TCN_SELCHANGE)
u.SendMessageW(dlg_hwnd, WM_NOTIFY, 12320, ctypes.byref(hdr))
time.sleep(1.5)

# Inspect all controls again
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
print(f"\nControls after switching tab ({len(all_ctrls)}):")
for ch, cid, c, t, vis in all_ctrls:
    if vis or t:
        print(f"  Ctrl 0x{ch:08x} ID {cid} (vis={vis}): {c} '{t}'")

dc.close()
