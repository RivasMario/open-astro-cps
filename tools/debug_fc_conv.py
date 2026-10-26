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

print("[+] Setting 540401-00038C-7...")
u.SendMessageW(h_fc1, WM_SETTEXT, 0, "540401")
u.SendMessageW(h_fc2, WM_SETTEXT, 0, "00038C")
u.SendMessageW(h_fc3, WM_SETTEXT, 0, "7")
time.sleep(0.5)

print("[+] Sending BM_CLICK to OK...")
u.PostMessageW(h_ok, BM_CLICK, 0, 0)

for sec in range(6):
    time.sleep(1.0)
    wins = []
    def get_w(hwnd, extra):
        if u.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
                tb = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(hwnd, tb, 256)
                wins.append((hwnd, tb.value))
        return True
    u.EnumWindows(WNDENUMPROC(get_w), 0)
    print(f"t={sec+1}s: Active windows: {wins}")
    if not wins:
        print("[+] ALL DIALOGS CLOSED!")
        dc.save()
        break
    for h, title in wins:
        if title != 'Depot Update Codeplug':
            ctrls = []
            def get_c(ch, extra):
                tb = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(ch, tb, 256)
                if tb.value: ctrls.append(tb.value)
                return True
            u.EnumChildWindows(h, WNDENUMPROC(get_c), 0)
            print(f"   Popup '{title}': {ctrls}")

dc.close()
