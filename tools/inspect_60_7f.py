import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('C:/Users/skyway/open-astro-cps/backups/407CHT0214.cpg')

for e in sorted(cp.directory(), key=lambda x: (x['item_id'], x['instance'])):
    item = e['item_id']
    if 0x0060 <= item <= 0x007f:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"0x{item:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
cp.close()
