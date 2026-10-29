import ctypes

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_wchar_p, ctypes.c_int)

h_winsta = u.GetProcessWindowStation()
desktops = []
def desk_cb(name, extra):
    desktops.append(name)
    return True

u.EnumDesktopsW(h_winsta, DESKTOPENUMPROC(desk_cb), 0)
for d in desktops:
    h = u.OpenDesktopW(d, 0, False, 0x01FF)
    if not h: continue
    wins = []
    def win_cb(hwnd, extra):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 16736:
            cbuf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, cbuf, 256)
            tbuf = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(hwnd, tbuf, 256)
            wins.append((hwnd, pid.value, cbuf.value, tbuf.value))
        return True
    u.EnumDesktopWindows(h, WNDENUMPROC(win_cb), 0)
    if wins:
        print(f"Found on Desktop '{d}':")
        for hw, pid, c, t in wins:
            print(f"  0x{hw:08x}: {c} '{t}'")
    u.CloseDesktop(h)
