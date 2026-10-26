import ctypes

u = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

h_desk = u.OpenDesktopW('exebox-R2QH6R7NPX6OEDQRU2IKPTYWFY', 0, False, 0x01FF)
u.SetThreadDesktop(h_desk)

h = 0x013b07d4
children = []
def child_cb(ch, extra):
    cbuf = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(ch, cbuf, 256)
    tbuf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ch, tbuf, 256)
    cid = u.GetDlgCtrlID(ch)
    children.append((ch, cid, cbuf.value, tbuf.value))
    return True

u.EnumChildWindows(h, WNDENUMPROC(child_cb), 0)
print(f"Dialog 0x{h:08x} controls ({len(children)}):")
for ch, cid, c, t in children:
    print(f"  Child 0x{ch:08x} ID {cid}: {c} '{t}'")
