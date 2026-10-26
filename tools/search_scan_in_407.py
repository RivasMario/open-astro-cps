import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('C:/Users/skyway/open-astro-cps/backups/407CHT0214.cpg')

print("Searching objects in 407CHT0214.cpg...")
for e in cp.directory():
    strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
    dec = rc4(cp.key, strm)[6:-2]
    # Check ASCII
    try:
        s = dec.decode('ascii')
        if any(w in s.lower() for w in ['scan', 'list']):
            print(f"Object 0x{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {s}")
    except Exception:
        pass
cp.close()
