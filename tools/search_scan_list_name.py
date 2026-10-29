import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

path = os.path.join(repo, "backups", "407CHT0214.cpg")
cp = CpgParser(path)

# Let's inspect the names stream (Strm_1 or Strm_2)
for name in cp._read_dir():
    if 'Strm' in name:
        data = cp._read(['DataStg', name])
        dec = rc4(cp.key, data)
        if b'Scan List' in dec:
            print(f"Found 'Scan List' in {name} at offset {dec.find(b'Scan List')}")
            idx = dec.find(b'Scan List')
            print(repr(dec[max(0, idx-20):idx+30]))
