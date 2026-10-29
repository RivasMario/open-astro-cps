import subprocess
import time
import ctypes
import os

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = os.path.abspath(r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg")

proc = subprocess.Popen([DEPOT_EXE])
time.sleep(2.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
WM_COMMAND = 0x0111

def get_proc_windows():
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

# Dismiss intro dialog
for _ in range(5):
    wins = get_proc_windows()
    intro = [h for h, c, t in wins if c == '#32770']
    if intro:
        u.SendMessageW(intro[0], WM_COMMAND, 22784, 0)
        break
    time.sleep(0.5)

time.sleep(2.0)

main_hwnd = None
for h, c, t in get_proc_windows():
    if c == 'AfxMDIFrame42':
        main_hwnd = h
        break

print(f"Main HWND: 0x{main_hwnd:08x}")

# Try sending WM_COMMAND 57601 (File -> Open)
print("[+] Triggering File -> Open (57601)...")
u.PostMessageW(main_hwnd, WM_COMMAND, 57601, 0)
time.sleep(1.5)

# Look for open file dialog
wins = get_proc_windows()
open_dlg = None
for h, c, t in wins:
    print(f"  Window: HWND 0x{h:08x} '{c}': '{t}'")
    if c == '#32770' and ('Open' in t or not t):
        open_dlg = h

if open_dlg:
    print(f"[+] Found Open File Dialog: 0x{open_dlg:08x}")
    # Enumerate children of file dialog to find edit control (usually 1148 or Edit)
    children = []
    def child_cb(ch, extra):
        cc = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cc, 256)
        cid = u.GetDlgCtrlID(ch)
        children.append((ch, cid, cc.value))
        return True
    u.EnumChildWindows(open_dlg, WNDENUMPROC(child_cb), 0)
    for ch, cid, cc in children:
        if cc == 'Edit':
            print(f"  Found Edit control: 0x{ch:08x} ID {cid}")

proc.terminate()
