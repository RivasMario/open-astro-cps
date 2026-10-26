import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController, get_cpg_snapshot, diff_snapshots

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
snap_before = get_cpg_snapshot(cpg_path)

dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("scan_list")

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
PSM_SETCURSEL = 0x0465

u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 2, 0)
time.sleep(1.0)

tb_hwnd = None
def find_tb(ch, extra):
    global tb_hwnd
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if 'ToolbarWindow32' in cbuf.value:
        tb_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tb), 0)

# Get rect of button 0
pid = ctypes.c_ulong()
u.GetWindowThreadProcessId(tb_hwnd, ctypes.byref(pid))
k32 = ctypes.windll.kernel32
h_proc = k32.OpenProcess(0x0038, False, pid.value)
remote_buf = k32.VirtualAllocEx(h_proc, None, 16, 0x1000, 0x04)

TB_GETITEMRECT = 0x041d
u.SendMessageW(tb_hwnd, TB_GETITEMRECT, 0, remote_buf)

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

rc = RECT()
k32.ReadProcessMemory(h_proc, remote_buf, ctypes.byref(rc), 16, None)
k32.VirtualFreeEx(h_proc, remote_buf, 0, 0x8000)
k32.CloseHandle(h_proc)

print(f"Button 0 rect: ({rc.left}, {rc.top}, {rc.right}, {rc.bottom})")
x = (rc.left + rc.right) // 2
y = (rc.top + rc.bottom) // 2
lparam = (y << 16) | (x & 0xffff)

print(f"[+] Clicking Toolbar button 0 at ({x}, {y})...")
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
u.SendMessageW(tb_hwnd, WM_LBUTTONDOWN, 1, lparam)
u.SendMessageW(tb_hwnd, WM_LBUTTONUP, 0, lparam)
time.sleep(2.0)

dc.save()
dc.close()

snap_after = get_cpg_snapshot(cpg_path)
diffs = diff_snapshots(snap_before, snap_after)
print("\n=== SCAN MEMBER DIFFS ===")
for k, v in diffs.items():
    if not k.startswith("80:0047:"):
        print(f"Object {k}:")
        print(f"  Before: {v['before']}")
        print(f"  After : {v['after']}")
        print(f"  Changes: {v['changed_bytes']}")
