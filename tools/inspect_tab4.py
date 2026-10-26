import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "depot_buttons.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("conv_pers")

u = ctypes.windll.user32
PSM_SETCURSEL = 0x0465
u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 4, 0)
time.sleep(0.5)

combos = dc.enum_combos(dlg_hwnd)
for c in combos:
    cid = c['id']
    items = c['items']
    print(f"Combo ID {cid}: items={items}")

# Also print all visible text labels on Tab 4
texts = []
def get_t(ch, extra):
    if u.IsWindowVisible(ch):
        tb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tb, 256)
        cid = u.GetDlgCtrlID(ch)
        if tb.value: texts.append((cid, tb.value))
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(get_t), 0)
print(f"Visible texts on Tab 4: {texts}")

dc.close()
