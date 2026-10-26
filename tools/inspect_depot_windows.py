import ctypes

user32 = ctypes.windll.user32

pid_target = 14860
windows = []

def cb(hwnd, extra):
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == pid_target:
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        visible = user32.IsWindowVisible(hwnd)
        windows.append((hwnd, visible, buf.value))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(cb), 0)

print(f"Windows for PID {pid_target}:")
for h, v, title in windows:
    print(f"  HWND 0x{h:08x} | Visible: {v} | Title: '{title}'")
