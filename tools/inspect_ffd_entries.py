import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

REPO = r"C:\Users\skyway\open-astro-cps"
path = os.path.join(REPO, 'backups', '407CHT0214.cpg')
cp = CpgParser(path)
for e in cp.directory():
    if e['item_id'] == 0x0ffd and e['instance'] == 0:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"0x0ffd:0 ({len(dec)}B): {dec.hex()}")
        # Let's see the channel records
        hdr = dec[:6]
        print(f"Header: {hdr.hex()}")
        entry_size = 35 # let's check entry size
        rest = dec[6:]
        for i in range(0, len(rest), 35):
            entry = rest[i:i+35]
            print(f"  Entry {i//35} ({len(entry)}B): {entry.hex()}")
cp.close()
