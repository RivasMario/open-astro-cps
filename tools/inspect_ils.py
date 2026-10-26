import sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('backups/Radio1_205CMB2249_codeplug.cpg')
for e in sorted(cp.directory(), key=lambda x: (x['item_id'], x['instance'])):
    if e['item_id'] in [0x0ffc, 0x0ffd, 0x0ffe, 0x0fff, 0x0ff1, 0x0ff0]:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"Item 0x{e['item_id']:04x} Inst {e['instance']:2d} ({len(dec)}B): {dec.hex()}")
cp._ole.close()
