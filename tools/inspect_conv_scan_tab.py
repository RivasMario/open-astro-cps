import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
dc = DepotController(cpg_path)
dc.launch()
dlg_hwnd, mdi_hwnd = dc.open_dialog("conv_pers")

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

# Enum all tabs
tab_hwnd = None
def find_tab(ch, extra):
    global tab_hwnd
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    if 'SysTabControl32' in cbuf.value:
        tab_hwnd = ch
    return True

u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(find_tab), 0)
TCM_GETITEMCOUNT = 0x1304
count = u.SendMessageW(tab_hwnd, TCM_GETITEMCOUNT, 0, 0)
print(f"Conv Pers Tabs: {count}")

# Switch to each tab and look for 'Scan'
PSM_SETCURSEL = 0x0465
for i in range(count):
    u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, i, 0)
    time.sleep(0.3)
    combos = dc.enum_combos(dlg_hwnd)
    texts = []
    def get_t(ch, extra):
        if u.IsWindowVisible(ch):
            tb = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(ch, tb, 256)
            if tb.value: texts.append(tb.value)
        return True
    u.EnumChildWindows(dlg_hwnd, WNDENUMPROC(get_t), 0)
    if any('scan' in t.lower() for t in texts):
        print(f"Tab {i} has Scan controls! Texts: {[t for t in texts if 'scan' in t.lower()]}")
        for c in combos:
            print(f"  Combo ID {c['id']}: items={c['items']}")

dc.close()
