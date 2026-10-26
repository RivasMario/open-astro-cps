import ctypes, time, os, sys, threading
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
BM_CLICK = 0x00F5

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

h_btn = u.GetDlgItem(dlg, 21475)
print(f"PostMessage BM_CLICK to 'Add on options' (HWND {hex(h_btn)})...")
u.PostMessageW(h_btn, BM_CLICK, 0, 0)

time.sleep(1.5)
sub_dlg = None
def check_sub(hwnd, extra):
    global sub_dlg
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd not in (dc.main_hwnd, dlg):
            sub_dlg = hwnd
    return True
u.EnumWindows(WNDENUMPROC(check_sub), 0)

print(f"Sub dialog HWND: {hex(sub_dlg) if sub_dlg else 'None'}")
if sub_dlg:
    tbuf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(sub_dlg, tbuf, 512)
    print(f"Sub dialog Title: '{tbuf.value}'")
    ctrls = []
    def get_c(ch, extra):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        cid = u.GetDlgCtrlID(ch)
        cb = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cb, 256)
        ctrls.append((cid, cb.value, tb.value))
        return True
    u.EnumChildWindows(sub_dlg, WNDENUMPROC(get_c), 0)
    for c in ctrls:
        print(f"  ID {c[0]}: {c[1]} = '{c[2]}'")
    
    # Close sub dialog
    u.PostMessageW(sub_dlg, WM_COMMAND, 2, 0) # IDCANCEL

time.sleep(0.5)
u.PostMessageW(dlg, WM_COMMAND, 2, 0)
time.sleep(0.5)
dc.close()
