import ctypes
import time
import subprocess
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg"

WM_COMMAND = 0x0111
WM_CLOSE = 0x0010

ID_BUTTONS = 50088
ID_SAVE = 57603

print("=== Testing Direct Win32 WM_COMMAND Automation ===")
proc = subprocess.Popen([DEPOT_EXE, TARGET_CPG])

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

main_hwnd = None
for attempt in range(15):
    time.sleep(1.0)
    found_hwnd = []
    def enum_cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == proc.pid:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                found_hwnd.append((hwnd, buf.value))
        return True
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    for h, title in found_hwnd:
        if "ASTRO 25" in title or "PatPort" in title or "depot_buttons" in title:
            main_hwnd = h
            print(f"[+] Found main window after {attempt+1}s: HWND 0x{h:08x}: '{title}'")
            break
    if main_hwnd:
        break

if main_hwnd:
    print(f"[+] Sending WM_COMMAND ID_BUTTONS (50088) to HWND 0x{main_hwnd:08x}...")
    user32.PostMessageW(main_hwnd, WM_COMMAND, ID_BUTTONS, 0)
    time.sleep(2.0)

    # Check open windows again
    dialogs = []
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    for h, title in found_hwnd:
        if h != main_hwnd and title:
            dialogs.append((h, title))
            print(f"  [+] Active Dialog: HWND 0x{h:08x}: '{title}'")

    print("[+] Sending WM_CLOSE to main window...")
    user32.PostMessageW(main_hwnd, WM_CLOSE, 0, 0)
    time.sleep(1.0)

proc.terminate()
print("[+] Test completed.")
