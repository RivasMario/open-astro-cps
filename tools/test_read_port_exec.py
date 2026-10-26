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

# Find first dialog and click OK
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
u.SendMessageW(dlg, 0x0111, 1, 0)
time.sleep(1.5)

# Find Select Port dialog
port_dlg = None
u.EnumWindows(WNDENUMPROC(enum_top), 0)
port_dlg = dlg

# Find combo 1025
combo_hwnd = u.GetDlgItem(port_dlg, 1025)
CB_GETCOUNT = 0x0146
CB_GETLBTEXTLEN = 0x0149
CB_GETLBTEXT = 0x0148
CB_GETCURSEL = 0x0147

count = u.SendMessageW(combo_hwnd, CB_GETCOUNT, 0, 0)
cur_sel = u.SendMessageW(combo_hwnd, CB_GETCURSEL, 0, 0)
items = []
for i in range(count):
    tlen = u.SendMessageW(combo_hwnd, CB_GETLBTEXTLEN, i, 0)
    tb = ctypes.create_unicode_buffer(tlen + 1)
    u.SendMessageW(combo_hwnd, CB_GETLBTEXT, i, tb)
    items.append(tb.value)

print(f"Port options ({count}): {items}, current sel = {cur_sel}")

# Let's see if USB or COM7 is selected, then click OK!
print(f"[+] Clicking OK to start read on port: {items[cur_sel]}...")
u.SendMessageW(port_dlg, 0x0111, 1, 0) # IDOK

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
    print(f"[{s}s] Active Depot windows: {top_wins}")
    for h, c, t in top_wins:
        ctrls = []
        def get_c(ch, extra):
            tb = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(ch, tb, 256)
            if tb.value: ctrls.append(tb.value)
            return True
        u.EnumChildWindows(h, WNDENUMPROC(get_c), 0)
        print(f"    Window text contents: {ctrls}")

dc.close()
