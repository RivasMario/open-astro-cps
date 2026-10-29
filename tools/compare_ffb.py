import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.parsers.cpg_parser import CpgParser, rc4

def get_ffb(path):
    cp = CpgParser(path)
    res = {}
    for e in cp.directory():
        if (e['partition'], e['item_id']) == (0x80, 0x0ffb):
            strm = cp._read(['DataStg', f"Strm_{e['stream']}"])
            dec = rc4(cp.key, strm)[6:-2]
            res[e['instance']] = dec
    cp.close()
    return res

ref_407 = get_ffb(os.path.join(repo, "backups", "407CHT0214.cpg"))
ref_depot = get_ffb(os.path.join(repo, "backups", "depot_buttons.cpg"))
ref_cmb = get_ffb(os.path.join(repo, "backups", "Radio1_205CMB2249_codeplug.cpg"))

sec_ffb0 = bytes.fromhex("000fcd00004c748011001d0ff1000001820001000a0000100003881000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000")
clr_ffb1 = bytes.fromhex("000fcd00014c74b011001c0ff100000182000122200001000003801000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000")

print("407 (WORKING SCAN in DEPOT):")
v407 = ref_407[0]
print(" ", v407.hex())

print("\nclr_ffb1 (OUR CH 1 & 2):")
print(" ", clr_ffb1.hex())

print("\nsec_ffb0 (OUR CH 3 ADP):")
print(" ", sec_ffb0.hex())

diffs_407_clr = [(i, f"{v407[i]:02x}->{clr_ffb1[i]:02x}") for i in range(len(v407)) if v407[i] != clr_ffb1[i]]
print("\nDiffs 407 vs clr_ffb1:")
for idx, d in diffs_407_clr:
    print(f"  Byte {idx}: {d}")
