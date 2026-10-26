import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

REPO = r"C:\Users\skyway\open-astro-cps"
for name in ['205CFR2930.cpg', '407CHT0214.cpg', '205CMB2249_ADP.cpg']:
    path = os.path.join(REPO, 'backups', name)
    cp = CpgParser(path)
    for e in cp.directory():
        if e['item_id'] in (0x0049, 0x004a, 0x004b, 0x004c, 0x004e, 0x004f):
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"{name} 0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
    cp.close()
