import ctypes
import time
import os, sys

REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "depot_buttons.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("conv_pers")

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

tab_ctrl = None
def find_tab(ch, extra):
    global tab_ctrl
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if cbuf.value == 'SysTabControl32':
        tab_ctrl = ch
    return True
u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tab), 0)

TCM_GETITEMCOUNT = 0x1304
TCM_GETITEMW = 0x133C
TCIF_TEXT = 1

class TCITEM(ctypes.Structure):
    _fields_ = [
        ('mask', ctypes.c_uint),
        ('dwState', ctypes.c_uint),
        ('dwStateMask', ctypes.c_uint),
        ('pszText', ctypes.c_wchar_p),
        ('cchTextMax', ctypes.c_int),
        ('iImage', ctypes.c_int),
        ('lParam', ctypes.c_long)
    ]

count = u.SendMessageW(tab_ctrl, TCM_GETITEMCOUNT, 0, 0)
print(f"Tabs in Conventional Personality ({count}):")
buf = ctypes.create_unicode_buffer(256)
for i in range(count):
    item = TCITEM()
    item.mask = TCIF_TEXT
    item.pszText = ctypes.cast(buf, ctypes.c_wchar_p)
    item.cchTextMax = 256
    u.SendMessageW(tab_ctrl, TCM_GETITEMW, i, ctypes.byref(item))
    print(f"  Tab {i}: '{buf.value}'")

dc.close()
