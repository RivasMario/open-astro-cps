import sys
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/src')
sys.path.insert(0, 'C:/Users/skyway/open-astro-cps/tools')
import flash_radio_adp

framed = flash_radio_adp.build_flash_stream(
    '205CFR2930',
    'C:/Users/skyway/open-astro-cps/backups/Radio1_205CMB2249_codeplug.cpg',
    'C:/Users/skyway/open-astro-cps/backups/205CMB2249_ADP.cpg',
    'C:/Users/skyway/open-astro-cps/captures/cps_20261023_101302.pcap'
)

for fr in framed:
    if fr[:2] == b'\x01\x01':
        part = fr[2]
        item = int.from_bytes(fr[3:5], 'big')
        inst = int.from_bytes(fr[5:7], 'big')
        payload = fr[7:]
        if item in (0x0fff, 0x000d, 0x0020):
            import re
            strs = re.findall(rb'[\x20-\x7e]{3,}', payload)
            print(f"part 0x{part:02x} obj 0x{item:04x} inst {inst}: strings={strs}")
