import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
print("[+] Triggering 'Tools -> Depot -> Update Codeplug' (ID 50199)...")
u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50199, 0)
time.sleep(2.0)

all_popups = []
def check_all(hwnd, extra):
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            all_popups.append(hwnd)
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumWindows(WNDENUMPROC(check_all), 0)

for p in all_popups:
    tbuf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(p, tbuf, 512)
    print(f"Popup {hex(p)} Title: '{tbuf.value}'")
    def get_c(ch, extra):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        cid = u.GetDlgCtrlID(ch)
        cb = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cb, 256)
        print(f"    Control {hex(ch)} ID {cid} Class '{cb.value}': '{tb.value}'")
        return True
    u.EnumChildWindows(p, WNDENUMPROC(get_c), 0)

dc.close()
