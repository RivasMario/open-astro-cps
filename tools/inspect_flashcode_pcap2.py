import sys, os
repo = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(repo, "src"))
from open_astro.protocol import pcap_reader

pcap = os.path.join(repo, "captures", "depot_flashcode_20261024_214545.pcap")
reader = pcap_reader.PcapReader(pcap)
packets = list(reader.read_packets())
print(f"Total packets: {len(packets)}")
for p in packets[:10]:
    print(len(p.data), p.data[:30].hex())
