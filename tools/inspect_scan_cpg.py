import sys
sys.path.insert(0, 'src')
from open_astro.parsers.cpg_parser import CpgParser, rc4

for name, path in [('kent', 'backups/205CFR2930_KENT-PD_XTS 2500-II_160406-RB2D.cpg'), ('depot', 'backups/depot_buttons.cpg')]:
    cp = CpgParser(path)
    for e in cp.directory():
        if e['item_id'] in [0x0049, 0x004a, 0x004b, 0x004c, 0x004e]:
            s_name = 'Strm_' + str(e['stream'])
            strm = cp._read(['DataStg', s_name])
            dec = rc4(cp.key, strm)[6:-2]
            print(f"{name} {e['partition']:02x}:{e['item_id']:04x}:{e['instance']} len={len(dec)}: {dec.hex()}")
    cp._ole.close()
