import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

dc = DepotController(os.path.join(repo, "backups", "depot_buttons.cpg"))
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
CB_SETCURSEL = 0x014E
CBN_SELCHANGE = 1
WM_SETTEXT = 0x000C

u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50194, 0)
time.sleep(1.5)

dlg = None
def check_w(hwnd, extra):
    global dlg
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            dlg = hwnd
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumWindows(WNDENUMPROC(check_w), 0)

h_model = u.GetDlgItem(dlg, 21423)
h_serial = u.GetDlgItem(dlg, 21410)
h_pkg = u.GetDlgItem(dlg, 21461)
h_ok = u.GetDlgItem(dlg, 21406)

# Select Model 'H46UCF9PW6AN' (index 23)
u.SendMessageW(h_model, CB_SETCURSEL, 23, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21423, h_model)
time.sleep(0.5)

# Set Serial Number
u.SendMessageW(h_serial, WM_SETTEXT, 0, "205CFR2930")

# Select Package 2 (9600 Digital Trunk Data)
u.SendMessageW(h_pkg, CB_SETCURSEL, 2, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21461, h_pkg)
time.sleep(0.5)

print("[+] Clicking OK on Depot Create Codeplug...")
u.PostMessageW(dlg, WM_COMMAND, 21406, h_ok)

# Wait for dialog to close and document to be created
for _ in range(10):
    time.sleep(1.0)
    if not u.IsWindow(dlg) or not u.IsWindowVisible(dlg):
        print("[+] Create Codeplug dialog closed!")
        break

# Save as depot_created.cpg
out_cpg = os.path.join(repo, "backups", "depot_created.cpg")
dc.target_cpg = out_cpg
dc.save()
print(f"[+] Codeplug saved to {out_cpg}!")
dc.close()
