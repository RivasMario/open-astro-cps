with open('C:/Users/skyway/open-astro-cps/tools/flash_radio_adp.py', 'rb') as f:
    content = f.read()

old_sw20 = b'sw_20 = "00000002000700070329041d6018611a621994298623"'
new_sw20 = b'sw_20 = "00000002000700070329041d60186142621994298623"'

old_sw22 = b'sw_22 = "00000002000700070329041d60186121621994298623"'
new_sw22 = b'sw_22 = "00000002000700070329041d60186142621994298623"'

assert old_sw20 in content, 'old_sw20 not found'
assert old_sw22 in content, 'old_sw22 not found'

content = content.replace(old_sw20, new_sw20)
content = content.replace(old_sw22, new_sw22)

with open('C:/Users/skyway/open-astro-cps/tools/flash_radio_adp.py', 'wb') as f:
    f.write(content)
print('[+] Patched flash_radio_adp.py with ZnUp (0x42) for Middle Button!')
