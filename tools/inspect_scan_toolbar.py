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

# Find ToolbarWindow32 inside scan list
tb_hwnd = None
def find_tb(ch, extra):
    global tb_hwnd
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if 'ToolbarWindow32' in cbuf.value:
        tb_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tb), 0)
print(f"Toolbar HWND: 0x{tb_hwnd:08x}")

TB_BUTTONCOUNT = 0x0418
TB_GETBUTTON = 0x0417

class TBBUTTON(ctypes.Structure):
    _fields_ = [
        ('iBitmap', ctypes.c_int),
        ('idCommand', ctypes.c_int),
        ('fsState', ctypes.c_byte),
        ('fsStyle', ctypes.c_byte),
        ('bReserved', ctypes.c_byte * 2),
        ('dwData', ctypes.c_ulong),
        ('iString', ctypes.c_int)
    ]

btn_count = u.SendMessageW(tb_hwnd, TB_BUTTONCOUNT, 0, 0)
print(f"Toolbar button count: {btn_count}")

dc.close()
