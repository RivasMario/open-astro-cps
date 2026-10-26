import sys
import glob
sys.path.append("C:/Users/skyway/open-astro-cps/src")
from open_astro.parsers.cpg_parser import CpgParser, rc4

files = glob.glob("C:/Users/skyway/open-astro-cps/backups/*.cpg")

for f in files:
    try:
        cp = CpgParser(f)
        print("=== File:", f)
        for entry in cp.directory():
            p, item, inst = entry['partition'], entry['item_id'], entry['instance']
            if item in (0x0ff0, 0x0ff1, 0x0ffc, 0x0ffd, 0x0ffe, 0x0020, 0x0022):
                strm = cp._read(['DataStg', f"Strm_{entry['stream']}"])
                dec = rc4(cp.key, strm)[6:-2]
                print(f"  ({hex(p)}, {hex(item)}, {inst}): len={len(dec)} hex={dec.hex()}")
        cp.close()
    except Exception as e:
        print(f"Error {f}: {e}")
