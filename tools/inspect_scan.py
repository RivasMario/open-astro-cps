import sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

cp = CpgParser('C:/Users/skyway/open-astro-cps/backups/depot_buttons.cpg')
for e in cp.directory():
    if e['item_id'] in (0x0049, 0x004a, 0x004b, 0x004c, 0x004e, 0x004f, 0x0ffb):
        strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        print(f"{e['item_id']:04x}:{e['instance']} ({len(dec)}B): {dec.hex()}")
