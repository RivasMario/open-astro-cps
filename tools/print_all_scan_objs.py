import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

for root, d, files in os.walk('C:/Users/skyway/open-astro-cps/backups'):
    for f in files:
        if f.endswith('.cpg'):
            path = os.path.join(root, f)
            try:
                cp = CpgParser(path)
                for e in cp.directory():
                    if e['item_id'] in [0x0049, 0x004a, 0x004b, 0x0fce, 0x0fcf]:
                        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
                        dec = rc4(cp.key, strm)[6:-2]
                        print(f"{f} 0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
                cp.close()
            except Exception as ex:
                print(f, ex)
