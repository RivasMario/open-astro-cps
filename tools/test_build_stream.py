import os, sys, shutil
REPO = r"C:\Users\skyway\open-astro-cps"
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))

from open_astro.parsers.cpg_parser import CpgParser, rc4
import flash_radio_adp
from depot_auto_mapper import DepotController

# Let's see what build_flash_stream builds
stream = flash_radio_adp.build_flash_stream(
    "205CFR2930",
    os.path.join(REPO, "backups", "407CHT0214.cpg"),
    os.path.join(REPO, "backups", "205CMB2249_ADP.cpg"),
    os.path.join(REPO, "captures", "cps_20261023_101302.pcap")
)
print(f"[+] Total records built for flashing: {len(stream)}")
