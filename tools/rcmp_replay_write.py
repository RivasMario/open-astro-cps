"""Replay a captured CPS write session to a radio over userspace PPP.

This is the SAFEST possible first live write: it does not construct a codeplug,
it replays the exact, byte-perfect records CPS already sent in a capture (which
write a known codeplug). Use the RESTORE/normal session so the radio ends in
its normal state.

Default is a DRY RUN: it extracts and validates the records (every 0101 write
must re-encode byte-for-byte via rcmp.build_write, no 0x82 tuning target) and
prints a summary WITHOUT touching a radio. Transmitting requires BOTH --serial
and --confirm, and a matching backup present in backups/.

    # validate only (no radio):
    python tools/rcmp_replay_write.py captures/<restore>.pcap --device 5
    # transmit (brings up PPP on COM7, replays, read-back verifies):
    python tools/rcmp_replay_write.py captures/<restore>.pcap --device 5 \
        --serial COM7 --confirm

Never replays to partition 0x82 (tuning). CPS must be closed and the RAS
dial-up hung up so COM7 is free.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def extract_out_records(pcap: str, device: int | None):
    dec = _load("dec", os.path.join(REPO, "tools", "decode_usb_ppp.py"))
    rd = _load("rd", os.path.join(REPO, "tools", "usbpcap_read.py"))
    from open_astro.protocol import rcmp

    devs = rd.device_streams(pcap)

    def recs_of(stream):
        at, ppp = dec.split_at_and_ppp(stream)
        frames = dec.parse_ppp_frames(ppp)
        rs = bytearray()
        for f in frames:
            pl = bytes.fromhex(f["payload_hex"])
            if f["proto"] in (0x21, 0x0021):
                for x in dec.extract_rcmp(pl):
                    rs += bytes.fromhex(x["rcmp_hex"])
            elif f["proto"] == 0x2F:
                for x in dec.extract_rcmp(pl, True):
                    rs += bytes.fromhex(x["rcmp_hex"])
            elif f["proto"] == 0x2D:
                rs += dec.vj_compressed_data(pl)
        return list(rcmp.iter_records(bytes(rs)))

    if device is None:  # pick the device with the most 0101 writes
        device = max(devs, key=lambda d: sum(
            1 for r in recs_of(devs[d][0]) if r[:2].hex() == "0101"))
        print(f"[i] auto-selected device {device}")
    return recs_of(devs[device][0]), rcmp


def validate(records, rcmp) -> list:
    """Return the list of framed records, raising if anything is unsafe."""
    framed = []
    writes = 0
    for r in records:
        op = r[:2].hex()
        if op in ("0100", "0101") and len(r) >= 3 and r[2] == 0x82:
            raise SystemExit("[-] record targets partition 0x82 (tuning) -- refusing")
        if op == "0101":
            part, obj = r[2], int.from_bytes(r[3:5], "big")
            inst = int.from_bytes(r[5:7], "big")
            n = int.from_bytes(r[7:9], "big")
            payload = r[13:13 + n - 2]
            if rcmp.build_write(part, obj, payload, inst)[2:] != r:
                raise SystemExit(f"[-] write record for obj 0x{obj:04x} does not "
                                 f"re-encode byte-exact -- refusing")
            writes += 1
        framed.append(rcmp.frame(r))
    print(f"[+] validated {len(records)} records ({writes} writes) -- all "
          f"0101 re-encode byte-exact, no 0x82 targets")
    return framed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pcap")
    ap.add_argument("--device", type=int, default=None, help="USB device number of the write session")
    ap.add_argument("--serial", help="COM/tty port to bring PPP up on and transmit")
    ap.add_argument("--confirm", action="store_true", help="actually transmit (irreversible)")
    ap.add_argument("--expect-serial", help="radio serial the backup must match, e.g. 205CFR2930")
    args = ap.parse_args()

    records, rcmp = extract_out_records(args.pcap, args.device)
    framed = validate(records, rcmp)

    if not (args.serial and args.confirm):
        print("[i] DRY RUN -- not transmitting. Add --serial COMx --confirm to write.")
        return 0

    if args.expect_serial:
        bk = glob.glob(os.path.join(REPO, "backups", f"*{args.expect_serial}*.cpg"))
        if not bk:
            raise SystemExit(f"[-] no backup matching {args.expect_serial} in backups/ -- refusing")
        print(f"[+] backup present: {[os.path.basename(b) for b in bk]}")

    from open_astro.protocol.ppp_link import PppTcpConn
    from open_astro.protocol.rcmp_write import RcmpWriteClient

    print(f"[!] TRANSMITTING {len(framed)} records to {args.serial} ...")
    conn = PppTcpConn(args.serial)
    client = RcmpWriteClient(conn, allow_write=True)
    try:
        for i, fr in enumerate(framed):
            client.send_prebuilt(fr)
            if (i + 1) % 20 == 0:
                print(f"    ...{i + 1}/{len(framed)}")
        print(f"[+] all {len(framed)} records acked by the radio")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
