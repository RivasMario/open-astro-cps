import sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('backups/205CMB2249_ADP.cpg')
for e in cp.directory():
    if e['item_id'] == 0x004e:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"205CMB2249_ADP 0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
cp._ole.close()
