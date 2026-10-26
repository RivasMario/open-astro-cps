import subprocess
import time
import ctypes

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"

proc = subprocess.Popen([DEPOT_EXE])
time.sleep(2.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
WM_COMMAND = 0x0111
CB_GETCOUNT = 0x0146
CB_GETCURSEL = 0x0147
CB_GETLBTEXTLEN = 0x0149
CB_GETLBTEXT = 0x0148

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

# 1. Dismiss intro
for _ in range(5):
    wins = get_proc_windows()
    intro = [h for h, c, t in wins if c == '#32770' and not t]
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

# Dismiss tip of the day if present
for h, c, t in get_proc_windows():
    if 'Tip of the Day' in t:
        print(f"[+] Dismissing Tip of the Day (0x{h:08x})...")
        u.SendMessageW(h, WM_COMMAND, 2, 0) # IDCANCEL / Close

print(f"[+] Opening Buttons dialog (ID {ID_BUTTONS})...")
u.PostMessageW(main_hwnd, WM_COMMAND, ID_BUTTONS, 0)
time.sleep(2.0)

# Find Buttons dialog
buttons_dlg = None
for h, c, t in get_proc_windows():
    if c == '#32770' and t == 'Buttons':
        buttons_dlg = h
        break

if not buttons_dlg:
    # Look in child windows
    def find_dlg(ch, extra):
        global buttons_dlg
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cbuf, 256)
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tbuf, 256)
        if cbuf.value == '#32770' and tbuf.value == 'Buttons':
            buttons_dlg = ch
        return True
    u.EnumChildWindows(main_hwnd, WNDENUMPROC(find_dlg), 0)

print(f"[+] Buttons dialog HWND: 0x{buttons_dlg:08x}")

# Find all ComboBoxes inside Buttons dialog
combos = []
def enum_ctrls(ch, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    if cbuf.value == 'ComboBox':
        combos.append((ch, cid))
    return True

u.EnumChildWindows(buttons_dlg, WNDENUMPROC(enum_ctrls), 0)
print(f"[+] Found {len(combos)} ComboBox controls in Buttons dialog:\n")

for ch, cid in combos:
    count = u.SendMessageW(ch, CB_GETCOUNT, 0, 0)
    cur_sel = u.SendMessageW(ch, CB_GETCURSEL, 0, 0)
    items = []
    for i in range(count):
        tlen = u.SendMessageW(ch, CB_GETLBTEXTLEN, i, 0)
        tbuf = ctypes.create_unicode_buffer(tlen + 1)
        u.SendMessageW(ch, CB_GETLBTEXT, i, tbuf)
        items.append(tbuf.value)
    cur_text = items[cur_sel] if 0 <= cur_sel < len(items) else f"Idx {cur_sel}"
    print(f"ComboBox HWND 0x{ch:08x} ID {cid} (Current: '{cur_text}' [{cur_sel}/{count}]):")
    for i, it in enumerate(items):
        print(f"    [{i:2d}] {it}")
    print()

proc.terminate()
