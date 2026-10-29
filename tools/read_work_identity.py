import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

path = os.path.join(repo, "backups", "depot_fuzzer_work.cpg")
cp = CpgParser(path)
print("=== depot_fuzzer_work.cpg ===")
for e in cp.directory():
    if e['partition'] == 0x81 and e['item_id'] in (0x1004, 0x1005, 0x1006):
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"  {hex(e['item_id'])}:{e['instance']} len={len(dec)}: {dec.hex()}")
        if e['item_id'] in (0x1004, 0x1006):
            print(f"     ASCII: {dec.decode('latin1', errors='replace')}")
