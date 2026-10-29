import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

work_cpg = os.path.join(repo, "backups", "depot_buttons.cpg")
dc = DepotController(work_cpg)
dc.launch()

u = ctypes.windll.user32
u.PostMessageW(dc.main_hwnd, 0x0111, 50206, 0) # Flash Radio
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

tb = ctypes.create_unicode_buffer(256)
u.GetWindowTextW(dlg, tb, 256)
print(f"Flash Radio Dialog HWND {hex(dlg)}: '{tb.value}'")

ctrls = []
def get_c(ch, extra):
    if u.IsWindowVisible(ch):
        tb2 = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb2, 256)
        cid = u.GetDlgCtrlID(ch)
        cb = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cb, 256)
        ctrls.append((cid, cb.value, tb2.value))
    return True
u.EnumChildWindows(dlg, WNDENUMPROC(get_c), 0)

for c in ctrls:
    print(f"  ID {c[0]:5d} | {c[1]:15s} | '{c[2]}'")

dc.close()
