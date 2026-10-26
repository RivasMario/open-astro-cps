import ctypes, time, os, sys
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

cpg_path = os.path.join(REPO, "backups", "407CHT0214.cpg")
dc = DepotController(cpg_path)
dc.launch()

u = ctypes.windll.user32
print("[+] Opening Scan List DB (ID 50062)...")
u.SendMessageW(dc.main_hwnd, 0x0111, 50062, 0)
time.sleep(2.0)

# Inspect all windows under MDI client
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

wins = []
def cb(ch, extra):
    vis = u.IsWindowVisible(ch)
    if vis:
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(ch, tbuf, 256)
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(ch, cbuf, 256)
        cid = u.GetDlgCtrlID(ch)
        wins.append((ch, cid, cbuf.value, tbuf.value))
    return True

u.EnumChildWindows(dc.main_hwnd, WNDENUMPROC(cb), 0)
print(f"Windows in MDI ({len(wins)}):")
for ch, cid, c, t in wins:
    print(f"  0x{ch:08x} ID {cid}: {c} '{t}'")

dc.close()
