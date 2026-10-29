import ctypes
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

def check(hwnd, extra):
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, tbuf, 256)
    if 'Tip of the Day' in tbuf.value:
        print(f"Found Tip Dialog: 0x{hwnd:08x}")
        def child_cb(ch, extra):
            cbuf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(ch, cbuf, 256)
            ct = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(ch, ct, 256)
            cid = u.GetDlgCtrlID(ch)
            print(f"  Child 0x{ch:08x} ID {cid}: {cbuf.value} '{ct.value}'")
            return True
        u.EnumChildWindows(hwnd, WNDENUMPROC(child_cb), 0)
    return True

# Enum all desktops
h = u.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId())
u.EnumDesktopWindows(h, WNDENUMPROC(check), 0)
