#!/usr/bin/env python3
"""OpenAstro Standalone Automated ADP & Multi-Zone Flasher for Motorola ASTRO 25 Radios.

Directly flashes native Motorola 40-bit Software ADP Encryption (Q667) and
a complete 10-Zone fleet configuration (Zone 1: TEAM OPS, Zone 2: 800 INTEROP,
Zone 3: TAC OPS, plus regional tactical zones 4-10) with mapped physical controls:
  * Front LCD softkey [ZONE] active
  * Side buttons 1-dot (ZnUp) and 2-dot (ZnDn) active
  * Top 3-position toggle switch mapped to Zone Select (A/B/C)
  * Concentric collar switch (Switch 60) unprogrammed (0x23) so floating pins
    on Model II hardware cannot override channel strapping
  * Channel Strapping:
      Channel 1 (OPEN ASTRO):  Strapped Clear (0x00000000) -> NO lock icon
      Channel 2 (TEAM ANALOG): Strapped Clear (0x1a001a00) -> NO lock icon
      Channel 3 (ADP SECURE):  Strapped Secure (0x00000140) -> Ø Lock Icon Active
  * Software ADP Key 1: A1B2C3D4E5 in 0x005D:0 and CKR tables 0x0037/0x0038
  * Strict Partition 0x82 (RF Calibration) Firewall -- NEVER writes to 0x82.
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
from open_astro.protocol import rcmp, unlock_session
from open_astro.protocol.rcmp_write import RcmpWriteClient
from open_astro.protocol.rcmp_transport import RcmpReadClient
from open_astro.protocol.write_session import CpgWriteAssembler
import rcmp_replay_write

KNOWN_RADIOS = {
    "205CFR2930": {
        "model": "H46UCF9PW6AN",
        "1004": "0212323035434652323933300048343655434639505736414e000000000000030005000100000000000000000000050829010001000e03010c061b09152f0000006a90d7",
        "1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05040004000800000007080c",
        "1006": "00000010000100013534303430382d3030303738432d3600",  # 540408-00078C-6
    },
    "205CMB2249": {
        "model": "H46UCF9PW6BN",
        "1004": "0212323035434d42323234390048343655434639505736424e00000000000003000500010000000000000000000026102403000100240300261024222015000000000000",
        "1005": "1d1632597ef5b534fbebb9e20258c53800000084980001a31066000000000c05040004000800000007080c",
        "1006": "00000010000100013534303430382d3030303738432d3600",  # 540408-00078C-6
    }
}

SECURITY_OBJECT_IDS = [0x0035, 0x0036, 0x0037, 0x0038, 0x004e, 0x005d, 0x0f9f, 0x0fa0, 0x0fe8, 0x0fe9, 0x0fea, 0x0feb]


def detect_connected_serial(host="192.168.128.1", port=8002) -> str | None:
    """Read 0x1004 identity block from radio to detect serial number."""
    try:
        client = RcmpReadClient.connect(host=host, port=port, src_port=0)
        client.open_session()
        payload = client.read_object(0x81, 0x1004, 0x0044)
        client.close()
        for s in KNOWN_RADIOS:
            if s.encode('ascii') in payload:
                return s
    except Exception:
        pass
    return None


def build_flash_stream(serial: str, kent_cpg: str, adp_cpg: str, template_pcap: str | None = None):
    if serial not in KNOWN_RADIOS:
        raise ValueError(f"Unknown target serial '{serial}'. Registered: {list(KNOWN_RADIOS.keys())}")

    radio_meta = KNOWN_RADIOS[serial]

    # 1. Load multi-zone base from Kent CPG
    kent_cp = CpgParser(kent_cpg)
    cpg_objs = {}
    for entry in kent_cp.directory():
        p, item, inst = entry['partition'], entry['item_id'], entry['instance']
        if p == 0x82:
            continue
        strm = kent_cp._read(['DataStg', f"Strm_{entry['stream']}"])
        dec = rc4(kent_cp.key, strm)[6:-2]
        cpg_objs[(p, item, inst)] = dec
    kent_cp.close()

    # 2. Load ADP security objects
    adp_cp = CpgParser(adp_cpg)
    adp_objs = {}
    for entry in adp_cp.directory():
        strm = adp_cp._read(['DataStg', f"Strm_{entry['stream']}"])
        dec = rc4(adp_cp.key, strm)[6:-2]
        adp_objs[(entry['partition'], entry['item_id'], entry['instance'])] = dec
    adp_cp.close()

    for item in SECURITY_OBJECT_IDS:
        k = (0x80, item, 0)
        if k in adp_objs:
            cpg_objs[k] = adp_objs[k]

    # 3. Zone & Channel definitions:
    ch1_z1 = "0ffb0000322f0293029302930a269c240a269c240a269c240000008000000000000001"
    ch2_z1 = "0ffb0000322f0000000000000a2b30040a2b30040a2b30041a001a8000000000000001"
    ch3_z1 = "0ffb0001642a0293029302930a2822c40a2822c40a2822c40000014000000000000001"
    ffd0 = "000000000003" + ch1_z1 + ch2_z1 + ch3_z1

    fff0 = "000000000003" + \
           "4f50454e20415354524f00000000000000" + \
           "5445414d20414e414c4f47000000000000" + \
           "4144502053454355524500000000000000"

    ch1_z2 = "0ffb0000322f0000000000000a2515840a2515840a2515841a001a8000000000000001"
    ch2_z2 = "0ffb0000322f0000000000000a269c240a269c240a269c241a001a8000000000000001"
    ch3_z2 = "0ffb0000322f0000000000000a2822c40a2822c40a2822c41a001a8000000000000001"
    ffd2 = "000000000003" + ch1_z2 + ch2_z2 + ch3_z2

    fff1 = "000000000003" + \
           "3843414c4c393000000000000000000000" + \
           "3854414339310000000000000000000000" + \
           "3854414339320000000000000000000000"

    ch1_z3 = "0ffb0000322f0293029302930a269c240a269c240a269c240000008000000000000001"
    ch2_z3 = "0ffb0000322f0000000000000a2b30040a2b30040a2b30041a001a8000000000000001"
    ch3_z3 = "0ffb0001642a0293029302930a2822c40a2822c40a2822c40000014000000000000001"
    ffd4 = "000000000003" + ch1_z3 + ch2_z3 + ch3_z3

    fff2 = "000000000003" + \
           "54414320434c4541520000000000000000" + \
           "54414320414e414c4f4700000000000000" + \
           "5441432053454355524500000000000000"

    clr_ffb0 = "000fcd00004c748011001d0ff100000182000022220000010203801000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000"
    sec_ffb1 = "000fcd00014c748011001d0ff1000001020001000a0000100003881000000fbe00000000000001010101000ffa00000ff30000000000000ff7000000000000262626260000000000000000"
    rw_34 = "400314060000070c230b0a0602570003"
    sec_5d = "0000000e000800083030303141314232433344344535303030322a2a2a2a2a2a2a2a2a2a303030332a2a2a2a2a2a2a2a2a2a303030342a2a2a2a2a2a2a2a2a2a303030352a2a2a2a2a2a2a2a2a2a303030362a2a2a2a2a2a2a2a2a2a303030372a2a2a2a2a2a2a2a2a2a303030382a2a2a2a2a2a2a2a2a2a"
    sw_20 = "00000002000700070329041d60186121621994298623"
    sw_22 = "00000002000700070329041d60186121621994298623"
    btn_14 = "0000000600040004031e1e1e2626022648262626002626262626002626262626"
    btn_15 = "0000000600040004031e1e1e2626022648262626002626262626002626262626"
    btn_16 = "00000001001000041e1c8e37"
    btn_17 = "00000001001000041e1c8e37"
    menu_3e = "0affc00150300a9580343c141438873d1e000400210e28144d000f0100"
    menu_3f = "344046507850ff090808141a206a660a0a4d03"

    val_0d = bytearray(cpg_objs[(0x80, 0x000d, 0)])
    val_0d[8:25] = b"TEAM OPS".ljust(17, b"\x00")
    val_0d[25:42] = b"800 INTEROP".ljust(17, b"\x00")
    val_0d[42:59] = b"TAC OPS".ljust(17, b"\x00")

    val_ff1 = bytes.fromhex("00010003000f000f0ff000008000ff00ff0000000002000000000000000a")
    val_ff0 = bytes.fromhex("00000000000f010001010002010003000000000000000000000000000000000000000000000000000000000000000000000000")

    v_ffc0 = bytes.fromhex("0001002300ff00030ffd0000000001")
    v_ffc1 = bytes.fromhex("0001002300ff00030ffd0002000001")
    v_ffc2 = bytes.fromhex("0001002300ff00030ffd0004000001")

    v_ffe0 = bytes.fromhex("0001001100ff00030fff0000")
    v_ffe1 = bytes.fromhex("0001001100ff00030fff0001")
    v_ffe2 = bytes.fromhex("0001001100ff00030fff0002")

    custom_objs = {
        (0x81, 0x1004, 0): bytes.fromhex(radio_meta["1004"]),
        (0x81, 0x1006, 0): bytes.fromhex(radio_meta["1006"]),
        (0x81, 0x1005, 0): bytes.fromhex(radio_meta["1005"]),
        (0x80, 0x0ffd, 0): bytes.fromhex(ffd0),
        (0x80, 0x0ffd, 2): bytes.fromhex(ffd2),
        (0x80, 0x0ffd, 4): bytes.fromhex(ffd4),
        (0x80, 0x0fff, 0): bytes.fromhex(fff0),
        (0x80, 0x0fff, 1): bytes.fromhex(fff1),
        (0x80, 0x0fff, 2): bytes.fromhex(fff2),
        (0x80, 0x0ffc, 0): v_ffc0,
        (0x80, 0x0ffc, 1): v_ffc1,
        (0x80, 0x0ffc, 2): v_ffc2,
        (0x80, 0x0ffe, 0): v_ffe0,
        (0x80, 0x0ffe, 1): v_ffe1,
        (0x80, 0x0ffe, 2): v_ffe2,
        (0x80, 0x0ffb, 0): bytes.fromhex(clr_ffb0),
        (0x80, 0x0ffb, 1): bytes.fromhex(sec_ffb1),
        (0x80, 0x0034, 0): bytes.fromhex(rw_34),
        (0x80, 0x005d, 0): bytes.fromhex(sec_5d),
        (0x80, 0x0020, 0): bytes.fromhex(sw_20),
        (0x80, 0x0022, 0): bytes.fromhex(sw_22),
        (0x80, 0x0014, 0): bytes.fromhex(btn_14),
        (0x80, 0x0015, 0): bytes.fromhex(btn_15),
        (0x80, 0x0016, 0): bytes.fromhex(btn_16),
        (0x80, 0x0017, 0): bytes.fromhex(btn_17),
        (0x80, 0x003e, 0): bytes.fromhex(menu_3e),
        (0x80, 0x003f, 0): bytes.fromhex(menu_3f),
        (0x80, 0x000d, 0): bytes(val_0d),
        (0x80, 0x0ff0, 0): val_ff0,
        (0x80, 0x0ff1, 0): val_ff1,
    }

    if template_pcap and os.path.exists(template_pcap):
        recs, _ = rcmp_replay_write.extract_out_records(template_pcap, 5)
        writes = [r for r in recs if r[:2].hex() == '0101']
        pcap_keys = set((r[2], int.from_bytes(r[3:5], 'big'), int.from_bytes(r[5:7], 'big')) for r in writes)

        edits, adds = [], []
        for k, data in cpg_objs.items():
            p, o, i = k
            if p == 0x82:
                continue
            val = custom_objs.get(k, data)
            arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
            (edits if k in pcap_keys else adds).append(arg)

        for k, val in custom_objs.items():
            if k not in cpg_objs:
                p, o, i = k
                if p == 0x82:
                    continue
                arg = f"{p:x}:{o:x}:{i}:{val.hex()}"
                (edits if k in pcap_keys else adds).append(arg)

        edited_records = rcmp_replay_write.apply_edits(recs, edits, rcmp)
        final_records = rcmp_replay_write.apply_adds(edited_records, adds, rcmp)
        return rcmp_replay_write.validate(final_records, rcmp)

    # Pure-Python cross-platform synthesis (no gitignored .pcap needed)
    merged = dict(cpg_objs)
    merged.update(custom_objs)
    raw_records: list[bytes] = [bytes([0x01, 0x06, 0x00])]
    for pr in CpgWriteAssembler.default_prepare_records():
        raw_records.append(pr[2:])
    for (p, o, i) in sorted(merged.keys(), key=lambda x: (x[0] == 0x81, x[0], x[1], x[2])):
        if p == 0x82:
            continue
        raw_records.append(rcmp.build_write(p, o, merged[(p, o, i)], i)[2:])
    raw_records.append(bytes([0x01, 0x06, 0x01]))
    return rcmp_replay_write.validate(raw_records, rcmp)


def main():
    parser = argparse.ArgumentParser(description="OpenAstro Standalone ADP & Multi-Zone Flasher")
    parser.add_argument("--serial", choices=list(KNOWN_RADIOS.keys()),
                        help="Target radio serial number (auto-detected if omitted)")
    parser.add_argument("--write", action="store_true",
                        help="Transmit over TCP link (default is dry run)")
    parser.add_argument("--host", default="192.168.128.1",
                        help="Radio IP address over PPP (default 192.168.128.1)")
    parser.add_argument("--port", type=int, default=8002,
                        help="Radio RCMP TCP port (default 8002)")
    args = parser.parse_args()

    serial = args.serial
    if not serial:
        print("[*] Probing connected radio serial over RCMP...")
        serial = detect_connected_serial(host=args.host, port=args.port)
        if serial:
            print(f"[+] Detected radio serial: {serial} ({KNOWN_RADIOS[serial]['model']})")
        else:
            print("[-] Auto-detection failed (radio offline or PPP down). Please specify --serial.")
            return 1

    base_cpg = os.path.join(REPO, "backups", "407CHT0214.cpg")
    adp_cpg = os.path.join(REPO, "backups", "205CMB2249_ADP.cpg")
    if not os.path.exists(adp_cpg):
        adp_cpg = os.path.expanduser("~/Desktop/205CMB2249_ADP.cpg")
    pcap_path = os.path.join(REPO, "captures", "cps_20261023_101302.pcap")

    print(f"=== OpenAstro Standalone Multi-Zone & ADP Flasher ===")
    print(f"Target Serial:   {serial}")
    print(f"Target Model:    {KNOWN_RADIOS[serial]['model']}")
    print(f"FLASHcode:       540408-00078C-6 (Kitchen Sink: Q387 Scan + Q53 FPP + Q667 ADP + H869 AES)")
    print(f"Key 1:           A1B2C3D4E5 (40-bit RC4 Software ADP)")
    print(f"Zones:           Zone 1: TEAM OPS | Zone 2: 800 INTEROP | Zone 3: TAC OPS (+ Zones 4-10)")
    print(f"Controls:        [ZONE] softkey | 1-dot ZnUp | 2-dot ZnDn | Switch 62 Zone Select")
    print(f"Write Mode:      {'LIVE WRITE' if args.write else 'DRY RUN'}")

    framed = build_flash_stream(serial, base_cpg, adp_cpg, pcap_path)
    print(f"[+] Total validated RCMP records: {len(framed)}")

    if not args.write:
        print("[+] Dry run validated 100% byte-exact. Use --write to execute on hardware.")
        return 0

    print(f"[!] Transmitting {len(framed)} records to {args.host}:{args.port}...")
    time.sleep(0.5)
    client = RcmpWriteClient.connect(host=args.host, port=args.port, allow_write=True, src_port=0)
    try:
        def _send_raw(fr: bytes) -> None:
            client._conn.sendall(fr)

        def _recv_body() -> bytes:
            rec = client._recv_record()
            return rec[2:] if len(rec) > 2 else b""

        usess = unlock_session.UnlockSession(_send_raw, _recv_body, part=0x81, inst=0)
        usess.exchange()
        ack_rec = client._recv_record()
        print(f"[+] UnlockSecurity (0x0107) 32-byte LFSR seed->response ACKed: {ack_rec.hex()}")

        for i, fr in enumerate(framed):
            client.send_prebuilt(fr)
            time.sleep(0.005)
            if (i + 1) % 50 == 0 or (i + 1) == len(framed):
                print(f"    ...{i+1}/{len(framed)}")
        print(f"[+] All {len(framed)} records acked successfully!")
    finally:
        client.close()

    print(f"[+] Success! Radio {serial} is rebooting with Multi-Zone & ADP Active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
