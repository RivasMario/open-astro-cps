import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

work_cpg = os.path.join(repo, "backups", "depot_fuzzer_work.cpg")
dc = DepotController(work_cpg)
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
CB_SETCURSEL = 0x014E
CBN_SELCHANGE = 1
WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5

u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50194, 0)
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

h_model = u.GetDlgItem(dlg, 21423)
h_serial = u.GetDlgItem(dlg, 21410)
h_pkg = u.GetDlgItem(dlg, 21461)
h_ok = u.GetDlgItem(dlg, 21406)

u.SendMessageW(h_model, CB_SETCURSEL, 23, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21423, h_model)
u.SendMessageW(h_serial, WM_SETTEXT, 0, "205CFR2930")
u.SendMessageW(h_pkg, CB_SETCURSEL, 3, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21461, h_pkg)
time.sleep(0.5)

u.PostMessageW(h_ok, BM_CLICK, 0, 0)
time.sleep(1.5)

popups = []
def check_pop(hwnd, extra):
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            popups.append(hwnd)
    return True
u.EnumWindows(WNDENUMPROC(check_pop), 0)

for p in popups:
    tb = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(p, tb, 256)
    ctrls = []
    def get_c(ch, extra):
        tb2 = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb2, 256)
        cid = u.GetDlgCtrlID(ch)
        ctrls.append((hex(ch), cid, tb2.value))
        return True
    u.EnumChildWindows(p, WNDENUMPROC(get_c), 0)
    print(f"Window {hex(p)} '{tb.value}': {ctrls}")

dc.close()
