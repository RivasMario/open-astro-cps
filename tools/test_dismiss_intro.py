import subprocess
import time
import ctypes

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg"

proc = subprocess.Popen([DEPOT_EXE, TARGET_CPG])
time.sleep(2.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

# Find the intro dialog
def find_windows():
    found = []
    def cb(hwnd, extra):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == proc.pid:
            cbuf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, cbuf, 256)
            tbuf = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(hwnd, tbuf, 256)
            found.append((hwnd, cbuf.value, tbuf.value))
        return True
    u.EnumWindows(WNDENUMPROC(cb), 0)
    return found

wins = find_windows()
intro_dlg = None
for h, c, t in wins:
    if c == '#32770':
        intro_dlg = h
        break

if intro_dlg:
    print(f"[+] Found intro dialog 0x{intro_dlg:08x}. Sending START command (22784)...")
    # BM_CLICK = 0x00F5, or WM_COMMAND with ID 22784
    WM_COMMAND = 0x0111
    u.SendMessageW(intro_dlg, WM_COMMAND, 22784, 0)
    time.sleep(2.0)

# Now check windows again!
wins_after = find_windows()
print(f"[+] Windows after dismissing intro ({len(wins_after)}):")
for h, c, t in wins_after:
    print(f"  HWND 0x{h:08x}: Class '{c}', Title '{t}'")

proc.terminate()
