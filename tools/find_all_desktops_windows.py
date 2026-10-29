import ctypes

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

def check_desktop(name, h_desk=None):
    close_it = False
    if h_desk is None:
        h_desk = u.OpenDesktopW(name, 0, False, 0x01FF)
        close_it = True
    if not h_desk:
        return
    wins = []
    def cb(hwnd, extra):
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        cbuf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd, cbuf, 256)
        tbuf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, tbuf, 256)
        if tbuf.value or cbuf.value == '#32770':
            wins.append((hwnd, pid.value, cbuf.value, tbuf.value))
        return True
    u.EnumDesktopWindows(h_desk, WNDENUMPROC(cb), 0)
    print(f"=== Desktop '{name}' ({len(wins)} windows) ===", flush=True)
    for hw, pid, c, t in wins:
        print(f"  PID {pid} HWND 0x{hw:08x}: {c} '{t}'", flush=True)
    if close_it:
        u.CloseDesktop(h_desk)

check_desktop("Default")
h_cur = u.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId())
buf = ctypes.create_unicode_buffer(256)
u.GetUserObjectInformationW(h_cur, 2, buf, 256, None)
check_desktop(buf.value, h_cur)
