import subprocess, time, ctypes, struct

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
depot = r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot'
exe = r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe'
cpg = r'C:\Users\skyway\open-astro-cps\backups\Radio1_205CMB2249_codeplug.cpg'

proc = subprocess.Popen([exe, cpg], cwd=depot)
print("Depot started PID:", proc.pid, flush=True)

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
BM_CLICK = 0x00F5

clicked_start = False
for _ in range(20):
    time.sleep(0.5)
    def find_start(hwnd, lparam):
        global clicked_start
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if buf.value == 'START':
            user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
            clicked_start = True
            return False
        return True
    user32.EnumChildWindows(user32.GetDesktopWindow(), WNDENUMPROC(find_start), 0)
    if clicked_start:
        print("Clicked START", flush=True)
        break

expand_btn = None
tree_hwnd = None
for _ in range(20):
    time.sleep(0.5)
    def find_ctrls(hwnd, lparam):
        global expand_btn, tree_hwnd
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == proc.pid:
            b = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, b, 512)
            cb = ctypes.create_unicode_buffer(512)
            user32.GetClassNameW(hwnd, cb, 512)
            if b.value == 'Expand All':
                expand_btn = hwnd
            elif cb.value == 'SysTreeView32':
                tree_hwnd = hwnd
        return True
    user32.EnumChildWindows(user32.GetDesktopWindow(), WNDENUMPROC(find_ctrls), 0)
    if expand_btn and tree_hwnd:
        print("Found TreeView:", tree_hwnd, "Expand:", expand_btn, flush=True)
        break

user32.SendMessageW(expand_btn, BM_CLICK, 0, 0)
time.sleep(1.0)

TVM_GETNEXTITEM = 0x110A
TVGN_ROOT = 0x0000
TVGN_NEXT = 0x0001
TVGN_CHILD = 0x0004
TVM_GETITEMW = 0x113E
TVIF_TEXT = 0x0001
TVM_SELECTITEM = 0x110B
TVGN_CARET = 0x0009

hProcess = kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
remote_tv = kernel32.VirtualAllocEx(hProcess, 0, 1024, 0x1000 | 0x2000, 0x04)
remote_str = remote_tv + 256
local_str = ctypes.create_unicode_buffer(256)
read_bytes = ctypes.c_size_t()

def get_node_text(hitem):
    tvitem = struct.pack('<IIIIIIIIII', TVIF_TEXT, hitem, 0, 0, remote_str, 256, 0, 0, 0, 0)
    kernel32.WriteProcessMemory(hProcess, remote_tv, tvitem, len(tvitem), None)
    user32.SendMessageW(tree_hwnd, TVM_GETITEMW, 0, remote_tv)
    kernel32.ReadProcessMemory(hProcess, remote_str, ctypes.byref(local_str), 512, ctypes.byref(read_bytes))
    return local_str.value

target_node = None
def search_node(hitem):
    global target_node
    while hitem:
        txt = get_node_text(hitem)
        if 'Conventional Personality - 1' in txt or 'Zone Channel Assignment - 1' in txt:
            print(f"Found: {txt} at hItem=0x{hitem:x}", flush=True)
            target_node = hitem
            return
        child = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_CHILD, hitem)
        if child:
            search_node(child)
            if target_node: return
        hitem = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_NEXT, hitem)

root = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_ROOT, 0)
search_node(root)

if target_node:
    user32.SendMessageW(tree_hwnd, TVM_SELECTITEM, TVGN_CARET, target_node)
    time.sleep(0.3)
    user32.SendMessageW(tree_hwnd, 0x0100, 0x0D, 0) # VK_RETURN
    user32.SendMessageW(tree_hwnd, 0x0101, 0x0D, 0)
    time.sleep(1.0)
    
    windows = []
    def enum_w(hwnd, lparam):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == proc.pid:
            tb = ctypes.create_unicode_buffer(512)
            cb = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, tb, 512)
            user32.GetClassNameW(hwnd, cb, 512)
            if tb.value or cb.value in ['#32770', 'SysTabControl32']:
                windows.append((hwnd, cb.value, tb.value))
        return True
    user32.EnumChildWindows(user32.GetDesktopWindow(), WNDENUMPROC(enum_w), 0)
    print("Windows after opening target:", flush=True)
    for h, c, t in windows:
        if any(k in t for k in ['Zone', 'Personality', 'Conventional', 'Assignment', 'Channel']) or c == '#32770':
            print(f"  hwnd={h}: [{c}] {repr(t)}", flush=True)

proc.terminate()
