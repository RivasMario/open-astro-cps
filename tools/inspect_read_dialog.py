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

# Find the dialog
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

print(f"Read Dialog HWND: 0x{dlg:08x}" if dlg else "No dialog")

# Enumerate controls inside dialog
ctrls = []
def enum_c(ch, extra):
    tbuf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(ch, tbuf, 512)
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    ctrls.append((cid, cbuf.value, tbuf.value))
    return True

u.EnumChildWindows(dlg, WNDENUMPROC(enum_c), 0)
for cid, c, t in ctrls:
    print(f"  ID {cid}: {c} '{t}'")

dc.close()
