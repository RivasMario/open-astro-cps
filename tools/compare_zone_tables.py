import sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

for path in ['backups/Radio1_205CMB2249_codeplug.cpg', 'backups/depot_buttons.cpg']:
    cp = CpgParser(path)
    for e in cp.directory():
        if e['item_id'] in [0x0ff0, 0x0ff1, 0x0fe7, 0x0fe4]:
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"{path} {e['item_id']:04x}:{e['instance']:2d} ({len(dec)}B): {dec.hex()}")
    cp._ole.close()
