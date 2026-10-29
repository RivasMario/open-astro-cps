import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
WM_GETTEXT = 0x000D
LB_GETCOUNT = 0x018B
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A

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

def get_text(cid):
    h = u.GetDlgItem(dlg, cid)
    tb = ctypes.create_unicode_buffer(256)
    u.SendMessageW(h, WM_GETTEXT, 256, tb)
    return tb.value

print("Current Codeplug in Depot:")
print("  Serial:", get_text(21430))
print(f"  FLASHcode: {get_text(21433)}-{get_text(21434)}-{get_text(21435)}")

# Read ListBox 21477
h_lb = u.GetDlgItem(dlg, 21477)
count = u.SendMessageW(h_lb, LB_GETCOUNT, 0, 0)
items = []
for i in range(count):
    tlen = u.SendMessageW(h_lb, LB_GETTEXTLEN, i, 0)
    tb = ctypes.create_unicode_buffer(tlen + 1)
    u.SendMessageW(h_lb, LB_GETTEXT, i, tb)
    items.append(tb.value)
print(f"Active Options in ListBox ({count}):")
for it in items:
    print(f"  * {it}")

dc.close()
