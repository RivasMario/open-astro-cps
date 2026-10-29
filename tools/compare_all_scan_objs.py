import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

cpgs = {
    "407CHT0214": os.path.join(repo, "backups", "407CHT0214.cpg"),
    "Radio1_CMB": os.path.join(repo, "backups", "Radio1_205CMB2249_codeplug.cpg"),
    "depot_buttons": os.path.join(repo, "backups", "depot_buttons.cpg"),
}

scan_items = [0x0049, 0x004a, 0x004b, 0x004c, 0x0059, 0x005a, 0x005b, 0x0ff0, 0x0ff1, 0x0ffb, 0x0fcd]

for name, path in cpgs.items():
    if not os.path.exists(path):
        continue
    print(f"=== {name} ===")
    cp = CpgParser(path)
    objs = {}
    for e in cp.directory():
        if e['item_id'] in scan_items:
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            objs[(e['partition'], e['item_id'], e['instance'])] = dec
    for (p, item, inst), val in sorted(objs.items()):
        print(f"  {hex(item)}:{inst} len={len(val)}: {val.hex()}")
