import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('C:/Users/skyway/open-astro-cps/backups/407CHT0214.cpg')

for e in cp.directory():
    if e['item_id'] in (0x0fbc, 0x0fbd):
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
cp.close()
