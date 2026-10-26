import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

path = os.path.join(repo, "backups", "Radio1_205CMB2249_codeplug.cpg")
cp = CpgParser(path)

items_by_id = {}
for e in cp.directory():
    items_by_id.setdefault(e['item_id'], []).append(e['instance'])

print("Items with multiple instances in Radio1_205CMB2249_codeplug:")
for item_id, insts in sorted(items_by_id.items()):
    if len(insts) > 1:
        print(f"  Item {hex(item_id)}: instances {insts}")
