import os, sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

for root in ['backups', r'G:\My Drive\RADIO']:
    if not os.path.exists(root): continue
    for r, d, files in os.walk(root):
        for f in files:
            if f.endswith('.cpg'):
                path = os.path.join(r, f)
                try:
                    cp = CpgParser(path)
                    for e in cp.directory():
                        if e['item_id'] == 0x0049:
                            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
                            dec = rc4(cp.key, strm)[6:-2]
                            if not all(b == 0xff for b in dec[13:]):
                                print(f"{path} 0x0049:{e['instance']} ({len(dec)}B): {dec.hex()}")
                    cp._ole.close()
                except Exception:
                    pass
