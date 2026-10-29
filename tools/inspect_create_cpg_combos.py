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

CB_GETCOUNT = 0x0146
CB_GETLBTEXTLEN = 0x0149
CB_GETLBTEXT = 0x0148
CB_GETCURSEL = 0x0147

for cid in [21419, 21457, 21420, 21423, 21461]:
    h = u.GetDlgItem(dlg, cid)
    count = u.SendMessageW(h, CB_GETCOUNT, 0, 0)
    cur = u.SendMessageW(h, CB_GETCURSEL, 0, 0)
    items = []
    for i in range(count):
        tlen = u.SendMessageW(h, CB_GETLBTEXTLEN, i, 0)
        tb = ctypes.create_unicode_buffer(tlen + 1)
        u.SendMessageW(h, CB_GETLBTEXT, i, tb)
        items.append(tb.value)
    print(f"Combo {cid}: count={count}, sel={cur}, items={items}")

dc.close()
