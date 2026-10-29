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

# Click OK on confirm dialog
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
u.SendMessageW(dlg, 0x0111, 1, 0)
time.sleep(1.5)

# Now find Select Port dialog
port_dlg = None
u.EnumWindows(WNDENUMPROC(enum_top), 0)
port_dlg = dlg
print(f"Select Port Dialog: 0x{port_dlg:08x}")

ctrls = []
def get_c(ch, extra):
    tb = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tb, 256)
    cb = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cb, 256)
    cid = u.GetDlgCtrlID(ch)
    ctrls.append((cid, cb.value, tb.value))
    return True

u.EnumChildWindows(port_dlg, WNDENUMPROC(get_c), 0)
print(f"Controls in Select Port dialog ({len(ctrls)}):")
for cid, cb, tb in ctrls:
    print(f"  ID {cid}: {cb} '{tb}'")

# If there is a ComboBox, get its items
for cid, cb, tb in ctrls:
    if cb == 'ComboBox':
        pass

dc.close()
