import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
CB_GETCOUNT = 0x0146
CB_GETLBTEXTLEN = 0x0149
CB_GETLBTEXT = 0x0148
CB_SETCURSEL = 0x014E
CBN_SELCHANGE = 1
WM_GETTEXT = 0x000D

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

h_pkg = u.GetDlgItem(dlg, 21443)
h_btn = u.GetDlgItem(dlg, 21475)
print("Button 21475 enabled?:", bool(u.IsWindowEnabled(h_btn)))

count = u.SendMessageW(h_pkg, CB_GETCOUNT, 0, 0)
print(f"Packages count in Update Codeplug: {count}")
for i in range(count):
    tlen = u.SendMessageW(h_pkg, CB_GETLBTEXTLEN, i, 0)
    tb = ctypes.create_unicode_buffer(tlen + 1)
    u.SendMessageW(h_pkg, CB_GETLBTEXT, i, tb)
    
    # Select this package
    u.SendMessageW(h_pkg, CB_SETCURSEL, i, 0)
    u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21443, h_pkg)
    time.sleep(0.3)
    
    fc1 = ctypes.create_unicode_buffer(32)
    fc2 = ctypes.create_unicode_buffer(32)
    fc3 = ctypes.create_unicode_buffer(32)
    u.SendMessageW(u.GetDlgItem(dlg, 21433), WM_GETTEXT, 32, fc1)
    u.SendMessageW(u.GetDlgItem(dlg, 21434), WM_GETTEXT, 32, fc2)
    u.SendMessageW(u.GetDlgItem(dlg, 21435), WM_GETTEXT, 32, fc3)
    print(f"  Pkg {i} ('{tb.value}'): FLASHcode = {fc1.value}-{fc2.value}-{fc3.value}")

dc.close()
