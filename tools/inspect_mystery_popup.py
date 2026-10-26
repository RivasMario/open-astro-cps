import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

work_cpg = os.path.join(repo, "backups", "depot_fuzzer_work.cpg")
dc = DepotController(work_cpg)
dc.launch()

u = ctypes.windll.user32
u.PostMessageW(dc.main_hwnd, 0x0111, 50194, 0)
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

h_ok = u.GetDlgItem(dlg, 21406)
u.PostMessageW(dlg, 0x0111, 21406, h_ok)
time.sleep(1.0)

wins = []
def check_a(hwnd, extra):
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd not in (dc.main_hwnd, dlg):
            wins.append(hwnd)
    return True
u.EnumWindows(WNDENUMPROC(check_a), 0)

for w in wins:
    tb = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(w, tb, 256)
    cls = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(w, cls, 256)
    ctrls = []
    def get_c(ch, extra):
        c_tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, c_tb, 256)
        c_cls = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, c_cls, 256)
        cid = u.GetDlgCtrlID(ch)
        ctrls.append((hex(ch), cid, c_cls.value, c_tb.value))
        return True
    u.EnumChildWindows(w, WNDENUMPROC(get_c), 0)
    print(f'Popup {hex(w)} "{tb.value}" ({cls.value}): {ctrls}')

dc.close()
