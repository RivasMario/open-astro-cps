import subprocess
import time
import ctypes
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

DEPOT_EXE = r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe"
TARGET_CPG = os.path.join(REPO, "backups", "depot_buttons.cpg")

def get_snapshot(cpg_path):
    cp = CpgParser(cpg_path)
    objs = {}
    for e in cp.directory():
        if e['partition'] != 0x82:
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            objs[(e['partition'], e['item_id'], e['instance'])] = rc4(cp.key, strm)[6:-2]
    cp._ole.close()
    return objs

snap_before = get_snapshot(TARGET_CPG)
print(f"[+] Baseline snapshot taken: {len(snap_before)} objects", flush=True)

proc = subprocess.Popen([DEPOT_EXE])
time.sleep(2.0)
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_DOWN = 0x28
VK_RETURN = 0x0D
CBN_SELCHANGE = 1
CBN_SELENDOK = 9
CB_SETCURSEL = 0x014E
CB_GETCURSEL = 0x0147
ID_MRU_FILE1 = 57616
ID_BUTTONS = 50088
ID_FILE_SAVE = 57603

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
        print(f"[+] Dismissing intro: 0x{intro[0]:08x}", flush=True)
        u.SendMessageW(intro[0], WM_COMMAND, 22784, 0)
        break
    time.sleep(0.5)

time.sleep(2.0)

main_hwnd = None
for h, c, t in get_proc_windows():
    if c == 'AfxMDIFrame42':
        main_hwnd = h
        break

print(f"Main HWND: 0x{main_hwnd:08x}", flush=True)
print(f"[+] Loading codeplug via MRU 1...", flush=True)
u.SendMessageW(main_hwnd, WM_COMMAND, ID_MRU_FILE1, 0)
time.sleep(3.0)

# Dismiss tip of the day if present
for h, c, t in get_proc_windows():
    if 'Tip of the Day' in t:
        print(f"[+] Dismissing Tip of the Day (0x{h:08x})...", flush=True)
        u.SendMessageW(h, WM_COMMAND, 2, 0)

time.sleep(1.0)
print(f"[+] Opening Buttons dialog (ID {ID_BUTTONS})...", flush=True)
u.PostMessageW(main_hwnd, WM_COMMAND, ID_BUTTONS, 0)
time.sleep(2.0)

# Find Buttons dialog
buttons_dlg = None
buttons_mdi = None
def find_dlg(ch, extra):
    global buttons_dlg, buttons_mdi
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    if 'Buttons' in tbuf.value:
        if cbuf.value == '#32770':
            buttons_dlg = ch
        elif 'Afx' in cbuf.value:
            buttons_mdi = ch
    return True

u.EnumChildWindows(main_hwnd, WNDENUMPROC(find_dlg), 0)
print(f"[+] Buttons dialog HWND: 0x{buttons_dlg:08x}, MDI HWND: 0x{buttons_mdi:08x}", flush=True)

# Find ComboBox for Side 2 (ID 15601)
combo_s2 = None
def find_s2(ch, extra):
    global combo_s2
    if u.GetDlgCtrlID(ch) == 15601:
        combo_s2 = ch
    return True
u.EnumChildWindows(buttons_dlg, WNDENUMPROC(find_s2), 0)

print(f"[+] Side 2 ComboBox HWND: 0x{combo_s2:08x}", flush=True)
cur = u.SendMessageW(combo_s2, CB_GETCURSEL, 0, 0)
print(f"[+] Current Side 2 index: {cur}", flush=True)

# Send simulated keyboard input to combo_s2: Down Arrow, then Return
print("[+] Sending VK_DOWN and VK_RETURN to ComboBox...", flush=True)
u.SendMessageW(combo_s2, WM_KEYDOWN, VK_DOWN, 0)
u.SendMessageW(combo_s2, WM_KEYUP, VK_DOWN, 0)
time.sleep(0.5)
u.SendMessageW(combo_s2, WM_KEYDOWN, VK_RETURN, 0)
u.SendMessageW(combo_s2, WM_KEYUP, VK_RETURN, 0)

new_cur = u.SendMessageW(combo_s2, CB_GETCURSEL, 0, 0)
print(f"[+] New Side 2 index after VK_DOWN: {new_cur}", flush=True)

# Also notify both dialog and MDI frame
for parent in [buttons_dlg, buttons_mdi]:
    if parent:
        u.SendMessageW(parent, WM_COMMAND, (CBN_SELCHANGE << 16) | 15601, combo_s2)
        u.SendMessageW(parent, WM_COMMAND, (CBN_SELENDOK << 16) | 15601, combo_s2)

time.sleep(1.0)

# Trigger File -> Save (57603)
print("[+] Sending ID_FILE_SAVE (57603)...", flush=True)
u.SendMessageW(main_hwnd, WM_COMMAND, ID_FILE_SAVE, 0)
time.sleep(3.0)

proc.terminate()
time.sleep(1.0)

# Now inspect codeplug diff!
snap_after = get_snapshot(TARGET_CPG)
print("\n=== BINARY DIFF IN CODEPLUG ===", flush=True)
diff_count = 0
for k in sorted(set(snap_before.keys()) | set(snap_after.keys())):
    v1 = snap_before.get(k)
    v2 = snap_after.get(k)
    if v1 != v2:
        diff_count += 1
        part, item, inst = k
        print(f"Object {part:02x}:{item:04x}:{inst}:", flush=True)
        print(f"  Before: {v1.hex() if v1 else 'None'}", flush=True)
        print(f"  After : {v2.hex() if v2 else 'None'}", flush=True)

print(f"\n[+] Total objects changed: {diff_count}", flush=True)
