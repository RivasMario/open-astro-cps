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

tab_hwnd = None
def cb(ch, extra):
    global tab_hwnd
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if 'SysTabControl32' in cbuf.value:
        tab_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(cb), 0)
print(f"Tab Control: 0x{tab_hwnd:08x}")

TCM_GETITEMCOUNT = 0x1304
TCM_GETITEMW = 0x133c
TCIF_TEXT = 0x0001

class TCITEMW(ctypes.Structure):
    _fields_ = [
        ('mask', ctypes.c_uint),
        ('dwState', ctypes.c_uint),
        ('dwStateMask', ctypes.c_uint),
        ('pszText', ctypes.c_wchar_p),
        ('cchTextMax', ctypes.c_int),
        ('iImage', ctypes.c_int),
        ('lParam', ctypes.c_long)
    ]

count = u.SendMessageW(tab_hwnd, TCM_GETITEMCOUNT, 0, 0)
print(f"Tab count: {count}")

dc.close()
