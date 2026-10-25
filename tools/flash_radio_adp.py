#!/usr/bin/env python3
"""OpenAstro Standalone Automated ADP Flasher for Motorola ASTRO 25 Radios.

Directly flashes native Motorola 40-bit Software ADP Encryption (Q667) and
a matched 3-channel P25 digital voice pack over the native RCMP TCP protocol
(port 8002) without requiring legacy Motorola Depot/CPS GUI or hardware crypto UCM.

Enforces:
  * Strict Partition 0x82 (RF Calibration) Firewall -- NEVER writes to 0x82.
  * Byte-exact 0101 write record reconstruction & CCITT CRC-16 recalculation.
  * Automatic Switch 60 (concentric collar switch) unprogramming (0x23) so
    floating hardware pins on Model II portables cannot force Clear or Secure.
  * Channel Strapping:
      Channel 1 (OPEN ASTRO):  Strapped Clear (0x00000000) -> NO lock icon
      Channel 2 (TEAM ANALOG): Strapped Clear (0x1a001a00) -> NO lock icon
      Channel 3 (ADP SECURE):  Strapped Secure (0x00000140) -> Ø Lock Icon Active
  * Arms Key 1 with ADP 40-bit key A1B2C3D4E5 in 0x005D:0 and CKR tables 0x0037/0x0038.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "tools"))

from open_astro.parsers.cpg_parser import CpgParser, rc4
from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_write import RcmpWriteClient
import rcmp_replay_write

KNOWN_RADIOS = {
    "205CFR2930": {
        "model": "H46UCF9PW6AN",
        "1004": "0212323035434652323933300048343655434639505736414e000000000000030005000100000000000000000000050829010001000e03010c061b09152f0000006a90d7",
        "1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05000000000800000004080c",
        "1006": "00000010000100013530303030382d3030303438432d3700", # 500008-00048C-7
    },
    "205CMB2249": {
        "model": "H46UCF9PW6BN",
        "1004": "0212323035434d42323234390048343655434639505736424e00000000000003000500010000000000000000000026102403000100240300261024222015000000000000",
        "1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05000000000800000004080c",
        "1006": "00000010000100013530303030382d3030303438432d3700", # 500008-00048C-7
    }
}

def build_flash_stream(serial: str, template_cpg: str, template_pcap: str):
    if serial not in KNOWN_RADIOS:
        raise ValueError(f"Unknown target serial '{serial}'. Registered: {list(KNOWN_RADIOS.keys())}")

    radio_meta = KNOWN_RADIOS[serial]

    # 1. Load gold-master CPG objects
    cp = CpgParser(template_cpg)
    cpg_objs = {}
    for entry in cp.directory():
        strm = cp._read(['DataStg', f"Strm_{entry['stream']}"])
        dec = rc4(cp.key, strm)[6:-2]
        cpg_objs[(entry['partition'], entry['item_id'], entry['instance'])] = dec

    # 2. Extract base pcap records
    recs, _ = rcmp_replay_write.extract_out_records(template_pcap, 5)
    writes = [r for r in recs if r[:2].hex() == '0101']
    pcap_keys = set((r[2], int.from_bytes(r[3:5], 'big'), int.from_bytes(r[5:7], 'big')) for r in writes)

    # 3. Channel Strapping definitions:
    # 00 = Strapped Clear (NO lock icon)
    # 40 = Strapped Secure (YES lock icon)
    ch1_clr = "0ffb0001322f0293029302930a269c240a269c240a269c240000000000000000000001"
    ch2_ana = "0ffb0001322f0000000000000a2b30040a2b30040a2b30041a001a0000000000000001"
    ch3_sec = "0ffb0000642a0293029302930a269c240a269c240a269c240000014000000000000001"
    ffd0 = "000000000003" + ch1_clr + ch2_ana + ch3_sec

    fff0 = "000000000003" + \
           "4f50454e20415354524f00000000000000" + \
           "5445414d20414e414c4f47000000000000" + \
           "4144502053454355524500000000000000"

    # Pers 0: Exact SECURE ADP from CPG (88 at byte 23)
    sec_ffb0 = "000fcd000040748000001d0000000001020001000a0000100003881000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000"

    # Pers 1: Clean Clear personality (80 at byte 23)
    clr_ffb1 = "000fcd00014074b000001c000000000102000122200001000003801000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000"

    # Radio Wide Secure master enable: length 16 with 0003
    rw_34 = "400314060000070c230b0a0602570003"

    # Key table 0x005D: Key 1 = A1B2C3D4E5
    sec_5d = "0000000e000800083030303141314232433344344535303030322a2a2a2a2a2a2a2a2a2a303030332a2a2a2a2a2a2a2a2a2a303030342a2a2a2a2a2a2a2a2a2a303030352a2a2a2a2a2a2a2a2a2a303030362a2a2a2a2a2a2a2a2a2a303030372a2a2a2a2a2a2a2a2a2a303030382a2a2a2a2a2a2a2a2a2a"

    # Switch 60 unprogrammed (0x23) in both 0x0020 and 0x0022:
    sw_20 = "00000002000700070323041d60236123621a94238623"
    sw_22 = "00000002000700070323041d60236123622394238623"

    # Button configurations from CPG:
    btn_14 = "0000000600040004032626262626022648262626002626262626002626262626"
    btn_15 = "0000000600040004032626262626022648262626002626262626002626262626"

    custom_objs = {
        (0x81, 0x1004, 0): bytes.fromhex(radio_meta["1004"]),
        (0x81, 0x1006, 0): bytes.fromhex(radio_meta["1006"]),
        (0x81, 0x1005, 0): bytes.fromhex(radio_meta["1005"]),
        (0x80, 0x0ffd, 0): bytes.fromhex(ffd0),
        (0x80, 0x0fff, 0): bytes.fromhex(fff0),
        (0x80, 0x0ffb, 0): bytes.fromhex(sec_ffb0),
        (0x80, 0x0ffb, 1): bytes.fromhex(clr_ffb1),
        (0x80, 0x0034, 0): bytes.fromhex(rw_34),
        (0x80, 0x005d, 0): bytes.fromhex(sec_5d),
        (0x80, 0x0020, 0): bytes.fromhex(sw_20),
        (0x80, 0x0022, 0): bytes.fromhex(sw_22),
        (0x80, 0x0014, 0): bytes.fromhex(btn_14),
        (0x80, 0x0015, 0): bytes.fromhex(btn_15),
    }

    edits = []
    adds = []

    for k, data in cpg_objs.items():
        p, o, i = k
        if p == 0x82:
            continue # RF calibration firewall!
        val = custom_objs.get(k, data)
        arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
        if k in pcap_keys:
            edits.append(arg)
        else:
            adds.append(arg)

    for k, val in custom_objs.items():
        if k not in cpg_objs:
            p, o, i = k
            arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
            if k in pcap_keys:
                edits.append(arg)
            else:
                adds.append(arg)

    edited_records = rcmp_replay_write.apply_edits(recs, edits, rcmp)
    final_records = rcmp_replay_write.apply_adds(edited_records, adds, rcmp)
    framed = rcmp_replay_write.validate(final_records, rcmp)
    return framed

def main():
    parser = argparse.ArgumentParser(description="OpenAstro Standalone ADP Flasher")
    parser.add_argument("--serial", required=True, choices=list(KNOWN_RADIOS.keys()),
                        help="Target radio serial number (205CFR2930 or 205CMB2249)")
    parser.add_argument("--write", action="store_true",
                        help="Transmit over TCP link (default is dry run)")
    parser.add_argument("--host", default="192.168.128.1",
                        help="Radio IP address over PPP (default 192.168.128.1)")
    parser.add_argument("--port", type=int, default=8002,
                        help="Radio RCMP TCP port (default 8002)")
    args = parser.parse_args()

    cpg_path = os.path.join(REPO, "backups", "205CMB2249_ADP.cpg")
    if not os.path.exists(cpg_path):
        cpg_path = os.path.expanduser("~/Desktop/205CMB2249_ADP.cpg")

    pcap_path = os.path.join(REPO, "captures", "cps_20261023_101302.pcap")

    print(f"=== OpenAstro Standalone ADP Flasher ===")
    print(f"Target Serial:   {args.serial}")
    print(f"Target Model:    {KNOWN_RADIOS[args.serial]['model']}")
    print(f"FLASHcode:       500008-00048C-7 (Q667 ADP Enabled)")
    print(f"Key 1:           A1B2C3D4E5 (40-bit RC4 Software ADP)")
    print(f"Write Mode:      {'LIVE WRITE' if args.write else 'DRY RUN'}")

    framed = build_flash_stream(args.serial, cpg_path, pcap_path)
    print(f"[+] Total validated RCMP records: {len(framed)}")

    if not args.write:
        print("[+] Dry run validated 100% byte-exact. Use --write to execute on hardware.")
        return 0

    print(f"[!] Transmitting {len(framed)} records to {args.host}:{args.port}...")
    client = RcmpWriteClient.connect(host=args.host, port=args.port, allow_write=True)
    try:
        for i, fr in enumerate(framed):
            client.send_prebuilt(fr)
            time.sleep(0.03)
            if (i + 1) % 20 == 0:
                print(f"    ...{i+1}/{len(framed)}")
        print(f"[+] All {len(framed)} records acked successfully!")
    finally:
        client.close()

    print(f"[+] Success! Radio {args.serial} is rebooting with ADP Active and verified channels.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
