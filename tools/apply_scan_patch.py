with open('C:/Users/skyway/open-astro-cps/tools/flash_radio_adp.py', 'rb') as f:
    content = f.read()

# 1. Update sw_20 and sw_22 back to Scan
old_sw20 = b'sw_20 = "00000002000700070329041d60186142621994298623"'
new_sw20 = b'sw_20 = "00000002000700070329041d6018611a621994298623"'

old_sw22 = b'sw_22 = "00000002000700070329041d60186142621994298623"'
new_sw22 = b'sw_22 = "00000002000700070329041d60186121621994298623"'

# 2. Add val_49 and val_fcf definition before custom_objs
anchor = b'    val_ff0 = bytes.fromhex("00000000000f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")'
addition = b'\r\n    # Scan List 1 Members: 3 active channels in Zone 1 (Ch 1 OPEN ASTRO, Ch 2 TEAM ANALOG, Ch 3 ADP SECURE)\r\n    val_49 = bytes.fromhex("00010012003200140fcf000003010203ffffffffffffffffffffffffffffff")\r\n    val_fcf = bytes.fromhex("000000000001010101ffffffffffffffffffffffffffffff")'

# 3. Add to custom_objs
c_anchor = b'        (0x80, 0x0ff1, 0): val_ff1,'
c_addition = b'\r\n        (0x80, 0x0049, 0): val_49,\r\n        (0x80, 0x0fcf, 0): val_fcf,'

# 4. Cap val_ff1 zone count to 3
old_ff1 = b'val_ff1 = bytes.fromhex("00010003000f000f0ff0000000ffffff000fe7000000000000000000000a")'
new_ff1 = b'val_ff1 = bytes.fromhex("00010003000f000f0ff0000000ffffff000fe70000000000000000000003")'

assert old_sw20 in content, 'old_sw20 not found'
assert old_sw22 in content, 'old_sw22 not found'
assert anchor in content, 'anchor not found'
assert c_anchor in content, 'c_anchor not found'
assert old_ff1 in content, 'old_ff1 not found'

content = content.replace(old_sw20, new_sw20)
content = content.replace(old_sw22, new_sw22)
content = content.replace(anchor, anchor + addition)
content = content.replace(c_anchor, c_anchor + c_addition)
content = content.replace(old_ff1, new_ff1)

with open('C:/Users/skyway/open-astro-cps/tools/flash_radio_adp.py', 'wb') as f:
    f.write(content)
print('[+] Successfully patched flash_radio_adp.py with populated Scan List 1 and 3-Zone limit!')
