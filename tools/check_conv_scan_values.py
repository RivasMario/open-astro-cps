import ctypes, time, os, sys
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
from depot_auto_mapper import DepotController

u = ctypes.windll.user32
PSM_SETCURSEL = 0x0465
CB_GETCURSEL = 0x0147

for cpg in ["407CHT0214.cpg", "depot_buttons.cpg"]:
    print(f"\n=== CPG: {cpg} ===")
    dc = DepotController(os.path.join(repo, "backups", cpg))
    dc.launch()
    dlg_hwnd, mdi = dc.open_dialog("conv_pers")
    u.SendMessageW(dlg_hwnd, PSM_SETCURSEL, 9, 0)
    time.sleep(0.5)
    combos = dc.enum_combos(dlg_hwnd)
    for cid in [16138, 16143, 16137]:
        c = [cb for cb in combos if cb['id'] == cid]
        if c:
            cur = c[0]['cur_sel']
            items = c[0]['items']
            val = items[cur] if 0 <= cur < len(items) else f"UNKNOWN({cur})"
            print(f"  Combo {cid}: sel={cur} ({val}) out of {items}")
    dc.close()
