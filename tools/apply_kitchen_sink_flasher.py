import os

path = r"C:\Users\skyway\open-astro-cps\tools\flash_radio_adp.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_1005 = '"1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05000000000800000004080c"'
new_1005 = '"1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05040004000800000007080c"'

old_1006 = '"1006": "00000010000100013530303030382d3030303438432d3700",  # 500008-00048C-7'
new_1006 = '"1006": "00000010000100013534303430382d3030303738432d3600",  # 540408-00078C-6'

if old_1005 in content and old_1006 in content:
    content = content.replace(old_1005, new_1005)
    content = content.replace(old_1006, new_1006)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: tools/flash_radio_adp.py updated!")
else:
    print("WARNING: String not matched in file!")
