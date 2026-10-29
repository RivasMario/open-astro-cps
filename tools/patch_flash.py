with open('tools/flash_radio_adp.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    # Keep 0x0FF1:0 zone count at 10
    val_ff1 = bytearray(cpg_objs[(0x80, 0x0ff1, 0)])"""

replacement = """    # 0x0FF1:0 Scan & Zone Master: Fixed Priority 1 (Ch 1) & Priority 2 (Ch 2)
    # Activates Scan 'Z' icon on Side 2 (1-Dot) press and eliminates ILS unpacking errors
    val_ff1 = bytes.fromhex("00010003000f000f0ff0000006010200000fe7000005000000000000000a")
    val_ff0 = bytes.fromhex("00000000000f010001010002010003000000000000000000000000000000000000000000000000000000000000000000000000")"""

assert target in content, "target not found"
content = content.replace(target, replacement)

target2 = """        (0x80, 0x0ff1, 0): bytes(val_ff1),
    }"""

replacement2 = """        (0x80, 0x0ff0, 0): val_ff0,
        (0x80, 0x0ff1, 0): val_ff1,
    }"""

assert target2 in content, "target2 not found"
content = content.replace(target2, replacement2)

with open('tools/flash_radio_adp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[+] Successfully patched flash_radio_adp.py!")
