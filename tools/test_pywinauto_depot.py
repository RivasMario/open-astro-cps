import subprocess
import time
import ctypes
import os
from pywinauto import Application
import pywinauto.keyboard as keyboard

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = os.path.abspath(r"C:\Users\skyway\open-astro-cps\backups\depot_buttons.cpg")

proc = subprocess.Popen([DEPOT_EXE])
time.sleep(2.0)

u = ctypes.windll.user32
WM_COMMAND = 0x0111
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

# Dismiss intro
for _ in range(5):
    found = []
    def cb(hwnd, extra):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == proc.pid:
            cbuf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, cbuf, 256)
            if cbuf.value == '#32770':
                found.append(hwnd)
        return True
    u.EnumWindows(WNDENUMPROC(cb), 0)
    if found:
        print(f"[+] Dismissing intro: 0x{found[0]:08x}")
        u.SendMessageW(found[0], WM_COMMAND, 22784, 0)
        break
    time.sleep(0.5)

time.sleep(2.0)

app = Application(backend="win32").connect(process=proc.pid)
main_win = app.top_window()
print(f"[+] Attached pywinauto: '{main_win.window_text()}'")

# Check menu items in pywinauto
menu = main_win.menu()
if menu:
    print(f"[+] Menu items: {[m.text() for m in menu.items()]}")

# Send Ctrl+O
print("[+] Sending Ctrl+O to main window...")
main_win.type_keys("^o")
time.sleep(1.5)

print("[+] Windows in process after Ctrl+O:")
for w in app.windows():
    print(f"  '{w.window_text()}' ({w.class_name()})")

proc.terminate()
