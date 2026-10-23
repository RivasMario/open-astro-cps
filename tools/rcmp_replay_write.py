"""Replay a captured CPS write session to a radio over userspace PPP.

This is the SAFEST possible first live write: it does not construct a codeplug,
it replays the exact, byte-perfect records CPS already sent in a capture (which
write a known codeplug). Use the RESTORE/normal session so the radio ends in
its normal state.

Default is a DRY RUN: it extracts and validates the records (every 0101 write
must re-encode byte-for-byte via rcmp.build_write, no 0x82 tuning target) and
prints a summary WITHOUT touching a radio. Transmitting requires --confirm, a
transport, and a matching backup present in backups/.

Two write transports:
  * --socket  : OS TCP over an already-up RAS/pppd PPP link. VERIFIED on
                hardware (205CFR2930 recovery). Needs the RAS dial-up modem.
  * --serial COMx --serial-write : our own hardened userspace PPP/TCP straight
                on the COM port -- NO modem. The TCP retransmits + paces
                (offline-proven, tests/test_ppp_link_tcp.py) but is UNVERIFIED
                on a real radio, so it is blocked without the explicit
                --serial-write opt-in. Clearing it is the one-time on-hardware
                check in docs/HANDOFF_RCMP_LIVE.md.

    # validate only (no radio):
    python tools/rcmp_replay_write.py captures/<restore>.pcap --device 5
    # transmit over the modem (verified path):
    python tools/rcmp_replay_write.py captures/<restore>.pcap \
        --socket --confirm --expect-serial 205CFR2930
    # transmit without the modem (experimental; recoverable radio + backup):
    python tools/rcmp_replay_write.py captures/<restore>.pcap --device 5 \
        --serial COM7 --serial-write --confirm --expect-serial 205CFR2930

Never replays to partition 0x82 (tuning). CPS must be closed so COM7 is free.
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


def apply_edits(records, edits, rcmp):
    """Substitute write-object payloads from --edit PART:OBJ:INST:PAYLOADHEX.
    Only matching 0101 records are rebuilt (via build_write, so length+CRC are
    recomputed); every other record is left byte-identical to the capture, so
    the session structure/prepare/commit are unchanged."""
    if not edits:
        return records
    wanted = {}
    for e in edits:
        try:
            p, o, i, hx = e.split(":")
            wanted[(int(p, 16), int(o, 16), int(i, 16))] = bytes.fromhex(hx)
        except Exception:
            raise SystemExit(f"[-] bad --edit '{e}' (want PART:OBJ:INST:PAYLOADHEX hex)")
    out = []
    applied = set()
    for r in records:
        if r[:2].hex() == "0101":
            key = (r[2], int.from_bytes(r[3:5], "big"), int.from_bytes(r[5:7], "big"))
            if key in wanted:
                out.append(rcmp.build_write(key[0], key[1], wanted[key], key[2])[2:])
                applied.add(key)
                print(f"[+] edit applied: part 0x{key[0]:02x} obj 0x{key[1]:04x} "
                      f"inst {key[2]} -> {len(wanted[key])}-byte payload")
                continue
        out.append(r)
    missing = set(wanted) - applied
    if missing:
        raise SystemExit(f"[-] --edit targets not found in capture: "
                         f"{[(hex(p),hex(o),i) for p,o,i in missing]}")
    return out


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
    ap.add_argument("--port", type=int, default=8002, help="RCMP TCP port on the radio")
    ap.add_argument("--serial-write", action="store_true",
                    help="EXPERIMENTAL, UNVERIFIED ON HARDWARE: write over the "
                         "hardened userspace PPP (--serial), no RAS modem. The TCP "
                         "layer now retransmits + paces (offline-proven), but this "
                         "has never driven a real write. Required to unblock a "
                         "--serial write; without it --serial writes stay refused.")
    ap.add_argument("--confirm", action="store_true", help="actually transmit (irreversible)")
    ap.add_argument("--expect-serial", help="radio serial the backup must match, e.g. 205CFR2930")
    ap.add_argument("--delay", type=float, default=0.03,
                    help="seconds between records (paces the slow link; default 0.03)")
    ap.add_argument("--retries", type=int, default=6,
                    help="full-session retries if the radio drops mid-write (default 6)")
    ap.add_argument("--edit", action="append", default=[], metavar="PART:OBJ:INST:PAYLOADHEX",
                    help="replace one write object's payload, e.g. 80:0fff:1:<hex>. "
                         "Repeatable. The record is rebuilt (length+CRC) via build_write; "
                         "all other records stay byte-identical to the capture.")
    args = ap.parse_args()

    records, rcmp = extract_out_records(args.pcap, args.device)
    records = apply_edits(records, args.edit, rcmp)
    framed = validate(records, rcmp)

    transport_selected = bool(args.serial) or bool(args.socket)
    if not (args.confirm and transport_selected):
        print("[i] DRY RUN -- not transmitting.")
        print("    OS-socket (modem):  --socket --confirm   (RAS/pppd link up)")
        print("    serial (no modem):  --serial COMx --serial-write --confirm "
              "(experimental; recoverable radio + backup)")
        return 0

    # The ORIGINAL userspace PPP had a fire-and-forget TCP that desynced on the
    # write burst and watchdog-rebooted the radio mid-write, corrupting the
    # codeplug (observed on 205CFR2930). That TCP is now hardened (ACK-tracked
    # retransmit + send window, offline-proven in tests/test_ppp_link_tcp.py) --
    # but it has NEVER driven a real write, so a --serial write stays blocked
    # unless the operator explicitly opts in with --serial-write.
    serial_write = bool(args.serial) and not args.socket
    if args.confirm and serial_write and not args.serial_write:
        raise SystemExit(
            "[-] refusing to WRITE over userspace PPP (--serial): the hardened "
            "TCP is offline-proven but UNVERIFIED on hardware. If you are at a "
            "recoverable radio (e.g. 205CFR2930) with a verified backup, re-run "
            "with --serial-write to opt in. Otherwise use --socket (RAS/pppd).")
    if args.confirm and serial_write and args.serial_write:
        print("=" * 70)
        print("[!] SERIAL WRITE (NO MODEM) -- EXPERIMENTAL, UNVERIFIED ON HARDWARE")
        print("[!] The hardened userspace TCP has never driven a real write.")
        print("[!] Proceed ONLY on a recoverable radio with a verified backup.")
        print("[!] This is the one-time validation that clears serial writes.")
        print("=" * 70)

    if args.expect_serial:
        bk = glob.glob(os.path.join(REPO, "backups", f"*{args.expect_serial}*.cpg"))
        if not bk:
            raise SystemExit(f"[-] no backup matching {args.expect_serial} in backups/ -- refusing")
        print(f"[+] backup present: {[os.path.basename(b) for b in bk]}")

    from open_astro.protocol.rcmp_write import RcmpWriteClient

    def _open_client():
        if serial_write:
            # No modem: our own hardened PPP/TCP directly on the COM port.
            from open_astro.protocol.ppp_link import PppTcpConn
            conn = PppTcpConn(args.serial, dport=args.port, timeout=15.0)
            return RcmpWriteClient(conn, allow_write=True)
        # OS TCP stack over an already-up RAS/pppd PPP link.
        return RcmpWriteClient.connect(host=args.host, port=args.port,
                                       allow_write=True)

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
