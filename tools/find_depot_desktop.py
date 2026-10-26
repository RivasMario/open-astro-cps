import subprocess
import time
import ctypes

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg"

proc = subprocess.Popen([DEPOT_EXE, TARGET_CPG])
time.sleep(5.0)

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

def check_desktop(name):
    h = u.OpenDesktopW(name, 0, False, 0x01FF)
    if not h:
        print(f"Could not open desktop {name}")
        return
    found = []
    def cb(hwnd, extra):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == proc.pid:
            length = u.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            u.GetWindowTextW(hwnd, buf, length + 1)
            found.append((hwnd, buf.value))
        return True
    u.EnumDesktopWindows(h, WNDENUMPROC(cb), 0)
    print(f"Desktop '{name}': found {len(found)} windows for PID {proc.pid}")
    for hw, t in found:
        print(f"   HWND 0x{hw:08x}: '{t}'")
    u.CloseDesktop(h)

check_desktop("Default")

h_cur = u.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId())
buf = ctypes.create_unicode_buffer(256)
u.GetUserObjectInformationW(h_cur, 2, buf, 256, None)
check_desktop(buf.value)

proc.terminate()
