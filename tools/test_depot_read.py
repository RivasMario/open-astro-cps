import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

# Test reading device in Depot
cpg_path = os.path.join(REPO, "backups", "205CFR2930.cpg")
dc = DepotController(cpg_path)
dc.launch()

u = ctypes.windll.user32
ID_READ_DEVICE = 32789
print(f"[+] Sending ID_READ_DEVICE ({ID_READ_DEVICE}) to Depot...")
u.PostMessageW(dc.main_hwnd, 0x0111, ID_READ_DEVICE, 0)

# Monitor modal dialogs for 15 seconds
for i in range(15):
    time.sleep(1.0)
    # Check top level windows
    def enum_top(hwnd, extra):
        if u.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
                tbuf = ctypes.create_unicode_buffer(512)
                u.GetWindowTextW(hwnd, tbuf, 512)
                cbuf = ctypes.create_unicode_buffer(256)
                u.GetClassNameW(hwnd, cbuf, 256)
                print(f"  [Depot Window {i}s] 0x{hwnd:08x}: {cbuf.value} '{tbuf.value}'")
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    u.EnumWindows(WNDENUMPROC(enum_top), 0)

dc.close()
