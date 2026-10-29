import ctypes
u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
def cb(hwnd, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, tbuf, 256)
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if tbuf.value or cbuf.value == '#32770':
        print(f"PID {pid.value} HWND 0x{hwnd:08x}: {cbuf.value} '{tbuf.value}'")
    return True
u.EnumWindows(WNDENUMPROC(cb), 0)
