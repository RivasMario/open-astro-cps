import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50199, 0)
time.sleep(1.5)

dlg = None
def check_w(hwnd, extra):
    global dlg
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            dlg = hwnd
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumWindows(WNDENUMPROC(check_w), 0)

print(f"Update Codeplug Dialog HWND: {hex(dlg)}")
ctrls = []
def get_c(ch, extra):
    tb = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tb, 256)
    cid = u.GetDlgCtrlID(ch)
    cb = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cb, 256)
    rect = (ctypes.c_long * 4)()
    u.GetWindowRect(ch, rect)
    ctrls.append((cid, cb.value, tb.value, list(rect)))
    return True
u.EnumChildWindows(dlg, WNDENUMPROC(get_c), 0)

for c in ctrls:
    print(f"ID {c[0]:5d} | Class {c[1]:15s} | Text '{c[2]}' | Rect {c[3]}")

dc.close()
