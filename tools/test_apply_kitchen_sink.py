import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

work_cpg = os.path.join(repo, "backups", "depot_fuzzer_work.cpg")
import shutil
shutil.copyfile(os.path.join(repo, "backups", "depot_buttons.cpg"), work_cpg)

dc = DepotController(work_cpg)
dc.launch()

u = ctypes.windll.user32
WM_COMMAND = 0x0111
WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5

u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50199, 0) # Update Codeplug
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

h_fc1 = u.GetDlgItem(dlg, 21433)
h_fc2 = u.GetDlgItem(dlg, 21434)
h_fc3 = u.GetDlgItem(dlg, 21435)
h_ok = u.GetDlgItem(dlg, 21440)

print("[+] Typing FLASHcode 54940F-E0078D-8 into Update Codeplug...")
u.SendMessageW(h_fc1, WM_SETTEXT, 0, "54940F")
u.SendMessageW(h_fc2, WM_SETTEXT, 0, "E0078D")
u.SendMessageW(h_fc3, WM_SETTEXT, 0, "8")
time.sleep(0.5)

print("[+] Clicking OK (Button 21440)...")
u.PostMessageW(h_ok, BM_CLICK, 0, 0)
time.sleep(1.5)

# Find any warning popups and click OK on them
def dismiss_popups():
    popups = []
    def check_pop(hwnd, extra):
        if u.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == dc.proc.pid and hwnd not in (dc.main_hwnd, dlg):
                popups.append(hwnd)
        return True
    u.EnumWindows(WNDENUMPROC(check_pop), 0)
    for p in popups:
        # Click OK (1)
        print(f"[+] Dismissing popup {hex(p)} via IDOK...")
        u.PostMessageW(p, WM_COMMAND, 1, 0)
        time.sleep(0.5)

dismiss_popups()
time.sleep(1.5)

# Check if main Update Codeplug dialog closed
if not u.IsWindowVisible(dlg):
    print("[+] UPDATE CODEPLUG DIALOG CLOSED SUCCESSFULLY!")
    dc.save()
    time.sleep(1.0)
    print(f"[+] Successfully saved updated codeplug to {work_cpg}!")
else:
    print("[!] Dialog is still open, checking child controls...")
    # Maybe click OK again?
    u.PostMessageW(h_ok, BM_CLICK, 0, 0)
    time.sleep(1.0)
    dismiss_popups()
    if not u.IsWindowVisible(dlg):
        print("[+] Closed on second try!")
        dc.save()

dc.close()
