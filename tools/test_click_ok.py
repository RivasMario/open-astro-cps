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

print("[+] Typing FLASHcode 540401-00038C-7 into Update Codeplug...")
u.SendMessageW(h_fc1, WM_SETTEXT, 0, "540401")
u.SendMessageW(h_fc2, WM_SETTEXT, 0, "00038C")
u.SendMessageW(h_fc3, WM_SETTEXT, 0, "7")
time.sleep(0.5)

# Send WM_COMMAND with IDOK (1) to dialog
print("[+] Sending WM_COMMAND 1 to dialog...")
u.SendMessageW(dlg, WM_COMMAND, 1, h_ok)
time.sleep(1.5)

if not u.IsWindowVisible(dlg):
    print("[+] SUCCESS! DIALOG CLOSED CLEANLY! Saving codeplug...")
    dc.save()
    time.sleep(1.0)
    print(f"[+] Successfully saved updated codeplug to {work_cpg}!")
else:
    print("[!] Dialog is still visible. Sending WM_COMMAND 21440...")
    u.SendMessageW(dlg, WM_COMMAND, 21440, h_ok)
    time.sleep(1.5)
    if not u.IsWindowVisible(dlg):
        print("[+] Closed on 21440! Saving...")
        dc.save()
    else:
        print("[!] Still visible.")

dc.close()
