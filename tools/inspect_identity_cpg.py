import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

for cpg_name in ["407CHT0214.cpg", "Radio1_205CMB2249_codeplug.cpg", "depot_buttons.cpg", "205CFR2930.cpg"]:
    path = os.path.join(repo, "backups", cpg_name)
    if not os.path.exists(path):
        continue
    cp = CpgParser(path)
    print(f"=== {cpg_name} ===")
    for e in cp.directory():
        if e['partition'] == 0x81 and e['item_id'] in (0x1004, 0x1005, 0x1006):
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"  {hex(e['item_id'])}:{e['instance']} len={len(dec)}: {dec}")
