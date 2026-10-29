import sys
import os

repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

for cpg_name in ["407CHT0214.cpg", "depot_buttons.cpg", "205CFR2930.cpg", "Radio1_205CMB2249_codeplug.cpg"]:
    path = os.path.join(repo, "backups", cpg_name)
    if not os.path.exists(path):
        continue
    print(f"=== {cpg_name} ===")
    cp = CpgParser(path)
    for entry in cp.directory():
        p, item, inst = entry['partition'], entry['item_id'], entry['instance']
        if (p, item) in [(0x80, 0x0ff1), (0x80, 0x0ffb), (0x80, 0x0ff0)]:
            strm = cp._read(['DataStg', f"Strm_{entry['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"  {hex(item)}:{inst} (len {len(dec)}): {dec.hex()}")
    cp._ole.close()
