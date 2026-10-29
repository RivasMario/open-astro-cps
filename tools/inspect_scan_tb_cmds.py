import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
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

TB_GETBUTTON = 0x0417

# Read button command IDs using VirtualAllocEx in Depot process
pid = ctypes.c_ulong()
u.GetWindowThreadProcessId(tb_hwnd, ctypes.byref(pid))
k32 = ctypes.windll.kernel32
h_proc = k32.OpenProcess(0x0038, False, pid.value) # VM_OPERATION | VM_READ | VM_WRITE

remote_buf = k32.VirtualAllocEx(h_proc, None, 64, 0x1000, 0x04)

class TBBUTTON32(ctypes.Structure):
    _fields_ = [
        ('iBitmap', ctypes.c_int),
        ('idCommand', ctypes.c_int),
        ('fsState', ctypes.c_byte),
        ('fsStyle', ctypes.c_byte),
        ('bReserved', ctypes.c_byte * 2),
        ('dwData', ctypes.c_ulong),
        ('iString', ctypes.c_int)
    ]

tb_btn = TBBUTTON32()
for i in range(7):
    u.SendMessageW(tb_hwnd, TB_GETBUTTON, i, remote_buf)
    k32.ReadProcessMemory(h_proc, remote_buf, ctypes.byref(tb_btn), ctypes.sizeof(tb_btn), None)
    print(f"Toolbar button {i}: idCommand = {tb_btn.idCommand}, fsStyle = {hex(tb_btn.fsStyle)}")

k32.VirtualFreeEx(h_proc, remote_buf, 0, 0x8000)
k32.CloseHandle(h_proc)

dc.close()
