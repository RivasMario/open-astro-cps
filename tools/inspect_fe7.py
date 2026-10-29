import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

for cpg_name in ["407CHT0214.cpg", "depot_buttons.cpg"]:
    cp = CpgParser(os.path.join(repo, "backups", cpg_name))
    for entry in cp.directory():
        if (entry['partition'], entry['item_id']) == (0x80, 0x0fe7):
            strm = cp._read(['DataStg', f"Strm_{entry['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"{cpg_name} 0xfe7:{entry['instance']}: len={len(dec)} hex={dec.hex()} ascii={dec}")
    cp._ole.close()
