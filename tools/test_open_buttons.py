import subprocess
import time
import ctypes

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"

proc = subprocess.Popen([DEPOT_EXE])
time.sleep(2.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
WM_COMMAND = 0x0111
ID_MRU_FILE1 = 57616
ID_BUTTONS = 50088

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

# Dismiss intro
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
print(f"[+] Loading codeplug via MRU 1...")
u.SendMessageW(main_hwnd, WM_COMMAND, ID_MRU_FILE1, 0)
time.sleep(3.0)

print(f"[+] Opening Buttons dialog (ID {ID_BUTTONS})...")
u.PostMessageW(main_hwnd, WM_COMMAND, ID_BUTTONS, 0)
time.sleep(2.0)

# Check all windows in the process
wins = get_proc_windows()
print(f"[+] Open windows after Buttons command ({len(wins)}):")
for h, c, t in wins:
    print(f"  Window 0x{h:08x} Class '{c}' Title '{t}'")

# Check all child windows of AfxMDIFrame42
children = []
def child_cb(ch, extra):
    cc = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cc, 256)
    ct = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, ct, 256)
    cid = u.GetDlgCtrlID(ch)
    vis = u.IsWindowVisible(ch)
    children.append((ch, cid, cc.value, ct.value, vis))
    return True

u.EnumChildWindows(main_hwnd, WNDENUMPROC(child_cb), 0)
print(f"[+] Child windows of Main Frame ({len(children)}):")
for ch, cid, cc, ct, vis in children:
    if vis and (ct or 'MDI' in cc or '#' in cc):
        print(f"  Child 0x{ch:08x} (ID {cid}): '{cc}' - '{ct}'")

proc.terminate()
