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
h_fc1 = u.GetDlgItem(dlg, 21402)
h_fc2 = u.GetDlgItem(dlg, 21404)
h_fc3 = u.GetDlgItem(dlg, 21408)
h_ok = u.GetDlgItem(dlg, 21406)

# Select Model 'H46UCF9PW6AN' (index 23)
u.SendMessageW(h_model, CB_SETCURSEL, 23, 0)
u.SendMessageW(dlg, WM_COMMAND, (CBN_SELCHANGE << 16) | 21423, h_model)
time.sleep(0.5)

# Set Serial Number
u.SendMessageW(h_serial, WM_SETTEXT, 0, "205CFR2930")

# Set Kitchen Sink FLASHcode: 599108-101E87-3
u.SendMessageW(h_fc1, WM_SETTEXT, 0, "599108")
u.SendMessageW(h_fc2, WM_SETTEXT, 0, "101E87")
u.SendMessageW(h_fc3, WM_SETTEXT, 0, "3")
time.sleep(0.5)

# Click OK!
print("[+] Clicking OK on Depot Create Codeplug...")
u.SendMessageW(dlg, WM_COMMAND, 21406, h_ok)
time.sleep(2.0)

# Check if any error dialog appeared
err_dlg = None
def check_err(hwnd, extra):
    global err_dlg
    if u.IsWindowVisible(hwnd):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
            err_dlg = hwnd
    return True
u.EnumWindows(WNDENUMPROC(check_err), 0)

if err_dlg:
    tb = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(err_dlg, tb, 512)
    ctrls = []
    def get_c(ch, extra):
        t = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, t, 256)
        if t.value: ctrls.append(t.value)
        return True
    u.EnumChildWindows(err_dlg, WNDENUMPROC(get_c), 0)
    print(f"Popup appeared: '{tb.value}' ctrls={ctrls}")

# Save codeplug as depot_kitchen_sink.cpg
out_cpg = os.path.join(repo, "backups", "depot_kitchen_sink.cpg")
print(f"[+] Saving created codeplug to {out_cpg}...")
# File -> Save As (57604)
# Or save directly
dc.target_cpg = out_cpg
dc.save()
print("[+] Saved successfully!")

dc.close()
