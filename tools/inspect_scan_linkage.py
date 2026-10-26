import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

for name in ['407CHT0214', 'Radio1_205CMB2249_codeplug', 'depot_buttons']:
    path = os.path.join(repo, 'backups', f'{name}.cpg')
    if not os.path.exists(path):
        continue
    cp = CpgParser(path)
    for e in cp.directory():
        if e['item_id'] in (0x0fcf, 0x0fce, 0x0049, 0x004a, 0x0ff1, 0x0ff0):
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"{name} {hex(e['item_id'])}:{e['instance']} len={len(dec)}: {dec.hex()}")
