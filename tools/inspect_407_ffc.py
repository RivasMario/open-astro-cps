import os, sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

REPO = r"C:\Users\skyway\open-astro-cps"
path = os.path.join(REPO, 'backups', '407CHT0214.cpg')
cp = CpgParser(path)

print("=== 407CHT0214.cpg 0x0FFC instances ===")
for e in sorted(cp.directory(), key=lambda x: x['instance']):
    if e['item_id'] == 0x0ffc:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"  0x0ffc:{e['instance']} ({len(dec)}B): {dec.hex()}")

print("\n=== 0x0FF0:0 ===")
for e in cp.directory():
    if e['item_id'] == 0x0ff0:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"  0x0ff0:0 ({len(dec)}B): {dec.hex()}")

print("\n=== 0x0FF1:0 ===")
for e in cp.directory():
    if e['item_id'] == 0x0ff1:
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"  0x0ff1:0 ({len(dec)}B): {dec.hex()}")

cp.close()
