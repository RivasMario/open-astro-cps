import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "tools"))
import rcmp_replay_write

pcap = os.path.join(repo, "captures", "depot_flashcode_20261024_214545.pcap")
recs, _ = rcmp_replay_write.extract_out_records(pcap, 5)
writes = [r for r in recs if r[:2].hex() == '0101']
print(f"Total writes in flashcode pcap: {len(writes)}")
for r in writes:
    part = r[2]
    obj = int.from_bytes(r[3:5], 'big')
    inst = int.from_bytes(r[5:7], 'big')
    pl = r[7:]
    if part == 0x81 or obj in (0x1004, 0x1005, 0x1006):
        print(f"  part 0x{part:02x} obj 0x{obj:04x}:{inst} len={len(pl)}: {pl.hex()}")
        if obj == 0x1006:
            print(f"    String: {pl}")
