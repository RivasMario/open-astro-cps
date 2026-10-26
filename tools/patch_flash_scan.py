import sys

file_path = r'C:\Users\skyway\open-astro-cps\tools\flash_radio_adp.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'val_ff1 = bytes.fromhex("00010003000f000f0ff0000000ffffff000fe70000000000000000000003")' in line:
        new_lines.append('    val_ff1 = bytes.fromhex("00010003000f000f0ff0000006010200000fe7000005000000000000000a")\n')
        continue
    if 'val_ff0 = bytes.fromhex("00000000000f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")' in line:
        new_lines.append('    val_ff0 = bytes.fromhex("00000000000f010001010002010003000000000000000000000000000000000000000000000000000000000000000000000000")\n')
        continue
    if 'val_49 =' in line or 'val_fcf =' in line or 'Scan List 1 Members:' in line:
        continue
    if '(0x80, 0x0049, 0): val_49,' in line or '(0x80, 0x0fcf, 0): val_fcf,' in line:
        continue
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Updated flash_radio_adp.py successfully.")
