import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
CB_SETCURSEL = 0x014E
CBN_SELCHANGE = 1
WM_GETTEXT = 0x000D

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
h_pkg = u.GetDlgItem(dlg, 21461)

# Select Model 'H46UCF9PW6AN'
# Let's find index of 'H46UCF9PW6AN'
CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
CB_GETLBTEXTLEN = 0x0149
count = u.SendMessageW(h_model, CB_GETCOUNT, 0, 0)
target_idx = -1
for i in range(count):
    tlen = u.SendMessageW(h_model, CB_GETLBTEXTLEN, i, 0)
    tb = ctypes.create_unicode_buffer(tlen + 1)
    u.SendMessageW(h_model, CB_GETLBTEXT, i, tb)
    if tb.value == 'H46UCF9PW6AN':
        target_idx = i
        break

print(f"Model H46UCF9PW6AN index: {target_idx}")
u.SendMessageW(h_model, CB_SETCURSEL, target_idx, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21423, h_model)
time.sleep(0.5)

# For each package, inspect the FLASHcode generated
pkg_count = u.SendMessageW(h_pkg, CB_GETCOUNT, 0, 0)
for pidx in range(pkg_count):
    u.SendMessageW(h_pkg, CB_SETCURSEL, pidx, 0)
    u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21461, h_pkg)
    time.sleep(0.5)
    
    tlen = u.SendMessageW(h_pkg, CB_GETLBTEXTLEN, pidx, 0)
    tb = ctypes.create_unicode_buffer(tlen + 1)
    u.SendMessageW(h_pkg, CB_GETLBTEXT, pidx, tb)
    
    fc1 = ctypes.create_unicode_buffer(32)
    fc2 = ctypes.create_unicode_buffer(32)
    fc3 = ctypes.create_unicode_buffer(32)
    u.SendMessageW(u.GetDlgItem(dlg, 21402), WM_GETTEXT, 32, fc1)
    u.SendMessageW(u.GetDlgItem(dlg, 21404), WM_GETTEXT, 32, fc2)
    u.SendMessageW(u.GetDlgItem(dlg, 21408), WM_GETTEXT, 32, fc3)
    print(f"Package {pidx} ('{tb.value}'): FLASHcode = {fc1.value}-{fc2.value}-{fc3.value}")

dc.close()
