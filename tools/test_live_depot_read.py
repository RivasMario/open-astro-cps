import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "205CFR2930.cpg")
dc = DepotController(cpg_path)
dc.launch()

u = ctypes.windll.user32
ID_READ_DEVICE = 32789
u.PostMessageW(dc.main_hwnd, 0x0111, ID_READ_DEVICE, 0)
time.sleep(1.5)

# Find confirmation dialog
dlg = None
def enum_top(hwnd, extra):
    global dlg
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            dlg = hwnd
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumWindows(WNDENUMPROC(enum_top), 0)

print(f"Clicking OK on dialog 0x{dlg:08x}...")
u.SendMessageW(dlg, 0x0111, 1, 0) # IDOK = 1

# Monitor progress for 20 seconds
for s in range(20):
    time.sleep(1.0)
    top_wins = []
    def check_w(hwnd, extra):
        if u.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
                tbuf = ctypes.create_unicode_buffer(512)
                u.GetWindowTextW(hwnd, tbuf, 512)
                cbuf = ctypes.create_unicode_buffer(256)
                u.GetClassNameW(hwnd, cbuf, 256)
                top_wins.append((hwnd, cbuf.value, tbuf.value))
        return True
    u.EnumWindows(WNDENUMPROC(check_w), 0)
    print(f"[{s}s] Active Depot child windows: {top_wins}")
    # If error or progress box appears, inspect controls
    for h, c, t in top_wins:
        if 'Error' in t or 'Reading' in t or 'Warning' in t or 'ASTRO' in t:
            ctrls = []
            def get_c(ch, extra):
                tb = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(ch, tb, 256)
                if tb.value: ctrls.append(tb.value)
                return True
            u.EnumChildWindows(h, WNDENUMPROC(get_c), 0)
            print(f"    Window text contents: {ctrls}")

dc.close()
