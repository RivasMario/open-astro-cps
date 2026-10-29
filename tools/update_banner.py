import os

path = r"C:\Users\skyway\open-astro-cps\tools\flash_radio_adp.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_str = 'print(f"FLASHcode:       500008-00048C-7 (Q667 ADP Enabled)")'
new_str = 'print(f"FLASHcode:       540408-00078C-6 (Kitchen Sink: Q387 Scan + Q53 FPP + Q667 ADP + H869 AES)")'

if old_str in c:
    c = c.replace(old_str, new_str)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated banner!")
else:
    print("Not found")
