import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
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

h_ok = u.GetDlgItem(dlg, 21406)
print(f"Clicking OK (HWND {hex(h_ok)})...")
u.PostMessageW(dlg, WM_COMMAND, 21406, h_ok)

time.sleep(1.0)
top_wins = []
def check_all(hwnd, extra):
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid:
            tbuf = ctypes.create_unicode_buffer(512)
            u.GetWindowTextW(hwnd, tbuf, 512)
            cbuf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, cbuf, 256)
            top_wins.append((hwnd, cbuf.value, tbuf.value))
    return True
u.EnumWindows(WNDENUMPROC(check_all), 0)

print("Windows after clicking OK:")
for w in top_wins:
    print(f"  HWND {hex(w[0])} Class '{w[1]}' Title '{w[2]}'")
    ctrls = []
    def get_c(ch, extra):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        if tb.value: ctrls.append(tb.value)
        return True
    u.EnumChildWindows(w[0], WNDENUMPROC(get_c), 0)
    print(f"    Texts: {ctrls}")

dc.close()
