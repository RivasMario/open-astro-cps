import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
print("[+] Triggering 'Tools -> Depot -> Create Codeplug' (ID 50194)...")
u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50194, 0)
time.sleep(1.5)

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
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumWindows(WNDENUMPROC(check_w), 0)

print(f"Active popups ({len(top_wins)}): {top_wins}")
for h, c, t in top_wins:
    ctrls = []
    def get_c(ch, extra):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        cid = u.GetDlgCtrlID(ch)
        cb = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cb, 256)
        if tb.value or cb.value in ('Edit', 'ComboBox', 'Button'):
            ctrls.append((cid, cb.value, tb.value))
        return True
    u.EnumChildWindows(h, WNDENUMPROC(get_c), 0)
    print(f"  Window {hex(h)} '{t}' controls:")
    for ctrl in ctrls:
        print(f"    ID {ctrl[0]}: {ctrl[1]} = '{ctrl[2]}'")

dc.close()
