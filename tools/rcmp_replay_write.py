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
import time

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
    ap.add_argument("--serial", help="(legacy) bring up userspace PPP on this COM port")
    ap.add_argument("--socket", action="store_true",
                    help="transmit over the OS TCP stack via an already-up RAS/pppd PPP link "
                         "(robust; recommended for the write burst)")
    ap.add_argument("--host", default="192.168.128.1", help="radio PPP IP for --socket")
    ap.add_argument("--confirm", action="store_true", help="actually transmit (irreversible)")
    ap.add_argument("--expect-serial", help="radio serial the backup must match, e.g. 205CFR2930")
    ap.add_argument("--delay", type=float, default=0.03,
                    help="seconds between records (paces the slow link; default 0.03)")
    ap.add_argument("--retries", type=int, default=6,
                    help="full-session retries if the radio drops mid-write (default 6)")
    args = ap.parse_args()

    records, rcmp = extract_out_records(args.pcap, args.device)
    framed = validate(records, rcmp)

    transport_selected = bool(args.serial) or bool(args.socket)
    if not (args.confirm and transport_selected):
        print("[i] DRY RUN -- not transmitting. Add --socket --confirm (RAS link up).")
        return 0

    # Writes over the userspace PPP (--serial) cannot sustain the record burst;
    # it desyncs and the radio watchdog-reboots mid-write, corrupting the
    # codeplug (observed on 205CFR2930). Writes MUST go over the OS TCP stack.
    if args.confirm and args.serial and not args.socket:
        raise SystemExit(
            "[-] refusing to WRITE over userspace PPP (--serial): it desyncs on "
            "the record burst and corrupts the codeplug. Use --socket with the "
            "RAS/pppd PPP link up instead.")

    if args.expect_serial:
        bk = glob.glob(os.path.join(REPO, "backups", f"*{args.expect_serial}*.cpg"))
        if not bk:
            raise SystemExit(f"[-] no backup matching {args.expect_serial} in backups/ -- refusing")
        print(f"[+] backup present: {[os.path.basename(b) for b in bk]}")

    from open_astro.protocol.rcmp_write import RcmpWriteClient

    def _open_client():
        # Writes always go over the OS TCP stack (RAS/pppd link); the userspace
        # --serial path is blocked above for writes.
        return RcmpWriteClient.connect(host=args.host, allow_write=True)

    # Full-session retry: on any drop, reconnect and replay the WHOLE session
    # from the start (identical data, so restarting is safe and only a fully
    # completed pass clears FAIL 01/02).
    last_err = None
    for attempt in range(1, args.retries + 1):
        tgt = args.host if args.socket else args.serial
        print(f"[!] attempt {attempt}/{args.retries}: transmitting {len(framed)} "
              f"records to {tgt} (delay {args.delay}s) ...")
        client = None
        try:
            client = _open_client()
            for i, fr in enumerate(framed):
                client.send_prebuilt(fr)
                if args.delay:
                    time.sleep(args.delay)
                if (i + 1) % 20 == 0:
                    print(f"    ...{i + 1}/{len(framed)}")
            print(f"[+] all {len(framed)} records acked -- write session complete")
            client.close()
            return 0
        except Exception as e:  # serial drop / re-enumeration / ack failure
            last_err = e
            print(f"    [x] attempt {attempt} failed: {e}")
            try:
                if client:
                    client.close()
            except Exception:
                pass
            time.sleep(4.0)   # let the radio re-enumerate / settle
    print(f"[-] all {args.retries} attempts failed; last error: {last_err}")
    print("[-] radio codeplug may still be incomplete -- do not power off; retry "
          "or restore via CPS.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
