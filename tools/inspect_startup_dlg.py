import subprocess
import time
import ctypes

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg"

proc = subprocess.Popen([DEPOT_EXE, TARGET_CPG])
time.sleep(3.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

dlg_hwnd = None
def cb(hwnd, extra):
    global dlg_hwnd
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == proc.pid:
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd, cbuf, 256)
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, tbuf, 256)
        print(f"Top window: HWND 0x{hwnd:08x}, Class '{cbuf.value}', Text '{tbuf.value}'")
        if cbuf.value == '#32770':
            dlg_hwnd = hwnd
    return True

u.EnumWindows(WNDENUMPROC(cb), 0)

if dlg_hwnd:
    print(f"Dialog HWND: 0x{dlg_hwnd:08x}")
    children = []
    def child_cb(hchild, extra):
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hchild, cbuf, 256)
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hchild, tbuf, 256)
        ctrl_id = u.GetDlgCtrlID(hchild)
        children.append((hchild, ctrl_id, cbuf.value, tbuf.value))
        return True
    u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(child_cb), 0)
    for c in children:
        print(f"  Child HWND 0x{c[0]:08x} ID {c[1]}: Class '{c[2]}', Text '{c[3]}'")

proc.terminate()
