import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

REPO = r"C:\Users\skyway\open-astro-cps"
path = os.path.join(REPO, 'backups', '407CHT0214.cpg')
cp = CpgParser(path)
for e in cp.directory():
    if e['item_id'] == 0x0ffb:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"407CHT0214 0x0ffb:{e['instance']} ({len(dec)}B): {dec.hex()}")
cp.close()
