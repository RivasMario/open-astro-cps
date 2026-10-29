import sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('backups/Radio1_205CMB2249_codeplug.cpg')
for e in cp.directory():
    if e['item_id'] in [0x004e, 0x0049, 0x004a, 0x004b]:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
cp._ole.close()
