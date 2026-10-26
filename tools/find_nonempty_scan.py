import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

for root in ['C:/Users/skyway/open-astro-cps/backups', r'G:\My Drive\RADIO']:
    if not os.path.exists(root): continue
    for r, d, files in os.walk(root):
        for f in files:
            if f.endswith('.cpg'):
                path = os.path.join(r, f)
                try:
                    cp = CpgParser(path)
                    for e in cp.directory():
                        if e['item_id'] in (0x0049, 0x004e):
                            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
                            dec = rc4(cp.key, strm)[6:-2]
                            if not all(b == 0xff for b in dec[10:]):
                                print(f"{f} 0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
                    cp.close()
                except Exception:
                    pass
