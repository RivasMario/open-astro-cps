#!/usr/bin/env python3
"""Update FLASHcode in an ASTRO 25 codeplug (.cpg) using Depot Win32 automation."""

import argparse
import ctypes
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from depot_auto_mapper import DepotController

u = ctypes.windll.user32
WM_COMMAND = 0x0111
WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5
EN_CHANGE = 0x0300
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)


def update_flashcode(cpg_path: str, flashcode: str):
    parts = flashcode.split("-")
    if len(parts) != 3 or len(parts[0]) != 6 or len(parts[1]) != 6 or len(parts[2]) != 1:
        raise ValueError(f"Invalid FLASHcode format '{flashcode}' (must be XXXXXX-XXXXXX-X)")

    fc1, fc2, fc3 = parts
    print(f"[+] Loading {cpg_path} into Depot...")
    dc = DepotController(os.path.abspath(cpg_path))
    dc.launch()

    try:
        print("[+] Triggering 'Tools -> Depot -> Update Codeplug' (WM_COMMAND 50199)...")
        u.PostMessageW(dc.main_hwnd, WM_COMMAND, 50199, 0)
        time.sleep(2.0)

        dlg = None
        def check_w(hwnd, extra):
            nonlocal dlg
            if u.IsWindowVisible(hwnd):
                pid = ctypes.c_ulong()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
                    dlg = hwnd
            return True

        u.EnumWindows(WNDENUMPROC(check_w), 0)
        if not dlg:
            raise RuntimeError("Update Codeplug dialog did not appear")

        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(dlg, tbuf, 256)
        print(f"[+] Found dialog: '{tbuf.value}' (HWND {hex(dlg)})")

        h_fc1 = u.GetDlgItem(dlg, 21433)
        h_fc2 = u.GetDlgItem(dlg, 21434)
        h_fc3 = u.GetDlgItem(dlg, 21435)
        h_ok = u.GetDlgItem(dlg, 21440)

        print(f"[+] Setting FLASHcode to {fc1}-{fc2}-{fc3} with EN_CHANGE notifications...")
        u.SendMessageW(h_fc1, WM_SETTEXT, 0, fc1)
        u.SendMessageW(dlg, WM_COMMAND, (EN_CHANGE << 16) | 21433, h_fc1)

        u.SendMessageW(h_fc2, WM_SETTEXT, 0, fc2)
        u.SendMessageW(dlg, WM_COMMAND, (EN_CHANGE << 16) | 21434, h_fc2)

        u.SendMessageW(h_fc3, WM_SETTEXT, 0, fc3)
        u.SendMessageW(dlg, WM_COMMAND, (EN_CHANGE << 16) | 21435, h_fc3)
        time.sleep(0.5)

        print("[+] Clicking OK (Button 21440)...")
        u.PostMessageW(h_ok, BM_CLICK, 0, 0)
        time.sleep(2.5)

        # Check for any subsequent confirmation popups
        for _ in range(5):
            popups = []
            def check_pop(hwnd, extra):
                if u.IsWindowVisible(hwnd):
                    pid = ctypes.c_ulong()
                    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == dc.proc.pid and hwnd != dc.main_hwnd:
                        t = ctypes.create_unicode_buffer(512)
                        u.GetWindowTextW(hwnd, t, 512)
                        popups.append((hwnd, t.value))
                return True
            u.EnumWindows(WNDENUMPROC(check_pop), 0)

            if not popups:
                break

            print(f"[!] Handling popups: {popups}")
            for h, title in popups:
                # Check for standard OK / Cancel / Yes button (ID 1, 2, or 6)
                btn_ok = u.GetDlgItem(h, 1)    # IDOK
                btn_cancel = u.GetDlgItem(h, 2) # IDCANCEL / OK on warnings
                btn_yes = u.GetDlgItem(h, 6)   # IDYES
                target_btn = btn_ok or btn_cancel or btn_yes
                if target_btn:
                    print(f"    Clicking button on popup '{title}'...")
                    u.SendMessageW(target_btn, BM_CLICK, 0, 0)
                else:
                    u.PostMessageW(h, WM_COMMAND, 2, 0)
            time.sleep(1.0)

        print("[+] Saving updated codeplug...")
        dc.save()
        time.sleep(1.5)
        print(f"[+] Codeplug successfully updated and saved: {cpg_path}")

    finally:
        dc.close()


def main():
    parser = argparse.ArgumentParser(description="Update codeplug FLASHcode via Depot")
    parser.add_argument("cpg", help="Path to .cpg file")
    parser.add_argument("flashcode", help="Target FLASHcode (e.g. 400008-006000-1)")
    args = parser.parse_args()

    update_flashcode(args.cpg, args.flashcode)


if __name__ == "__main__":
    main()
