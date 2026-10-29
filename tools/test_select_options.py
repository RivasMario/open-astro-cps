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

h_lb = u.GetDlgItem(dlg, 21477)
GWL_STYLE = -16
style = ctypes.windll.user32.GetWindowLongW(h_lb, GWL_STYLE)
print(f"ListBox style: {hex(style)}")

LB_GETSELCOUNT = 0x0190
LB_GETSELITEMS = 0x0191
LB_SETSEL = 0x0185
LB_GETCURSEL = 0x0188
LBN_SELCHANGE = 1
WM_GETTEXT = 0x000D

print("Initial Sel count:", u.SendMessageW(h_lb, LB_GETSELCOUNT, 0, 0))

# Select item 0 (Q387)
u.SendMessageW(h_lb, LB_SETSEL, 1, 0)
u.SendMessageW(dlg, WM_COMMAND, (LBN_SELCHANGE << 16) | 21477, h_lb)
time.sleep(0.5)

fc1 = ctypes.create_unicode_buffer(32)
fc2 = ctypes.create_unicode_buffer(32)
fc3 = ctypes.create_unicode_buffer(32)
u.SendMessageW(u.GetDlgItem(dlg, 21433), WM_GETTEXT, 32, fc1)
u.SendMessageW(u.GetDlgItem(dlg, 21434), WM_GETTEXT, 32, fc2)
u.SendMessageW(u.GetDlgItem(dlg, 21435), WM_GETTEXT, 32, fc3)
print(f"After selecting item 0: FLASHcode = {fc1.value}-{fc2.value}-{fc3.value}")

# Select all items
for i in range(13):
    u.SendMessageW(h_lb, LB_SETSEL, 1, i)
u.SendMessageW(dlg, WM_COMMAND, (LBN_SELCHANGE << 16) | 21477, h_lb)
time.sleep(0.5)
u.SendMessageW(u.GetDlgItem(dlg, 21433), WM_GETTEXT, 32, fc1)
u.SendMessageW(u.GetDlgItem(dlg, 21434), WM_GETTEXT, 32, fc2)
u.SendMessageW(u.GetDlgItem(dlg, 21435), WM_GETTEXT, 32, fc3)
print(f"After selecting all 13 items: FLASHcode = {fc1.value}-{fc2.value}-{fc3.value}")

# Read which items are selected
sel_count = u.SendMessageW(h_lb, LB_GETSELCOUNT, 0, 0)
print(f"Final Sel count: {sel_count}")

dc.close()
