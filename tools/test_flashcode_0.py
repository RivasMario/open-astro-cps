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

# Set 589108-101E87-0 (H101 removed, check digit 0)
print("[+] Typing FLASHcode 589108-101E87-0 into Update Codeplug...")
u.SendMessageW(h_fc1, WM_SETTEXT, 0, "589108")
u.SendMessageW(h_fc2, WM_SETTEXT, 0, "101E87")
u.SendMessageW(h_fc3, WM_SETTEXT, 0, "0")
time.sleep(0.5)

# Click OK
print("[+] Clicking OK (Button 21440)...")
u.PostMessageW(h_ok, BM_CLICK, 0, 0)
time.sleep(2.0)

popups = []
def check_pop(hwnd, extra):
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            tbuf = ctypes.create_unicode_buffer(512)
            u.GetWindowTextW(hwnd, tbuf, 512)
            popups.append((hwnd, tbuf.value))
    return True
u.EnumWindows(WNDENUMPROC(check_pop), 0)

print(f"Popups remaining: {popups}")
for h, title in popups:
    ctrls = []
    def get_c(ch, extra):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        if tb.value: ctrls.append(tb.value)
        return True
    u.EnumChildWindows(h, WNDENUMPROC(get_c), 0)
    print(f"  Popup {hex(h)} '{title}' texts: {ctrls}")

if not popups:
    print("[+] SUCCESS! DIALOG ACCEPTED AND CLOSED CLEANLY! Saving codeplug...")
    dc.save()
    time.sleep(1.0)
    print("[+] Successfully saved codeplug with Kitchen Sink FLASHcode!")
else:
    print("[!] Dialog had popups or was rejected.")

dc.close()
