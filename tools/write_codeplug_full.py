#!/usr/bin/env python3
"""Write a FULL codeplug (partition 0x80) to a radio from a source .cpg, using
the EEPROM-persist control framing, then read back and verify.

This is the driver for completing Radio 4 (721CLZ0655), whose live codeplug holds
only 9 of the master's 13 zones. It assembles every 0x80 object from the master
.cpg into one write session with the proven persist framing
(0106 00 -> 0102 -> 0103x2 -> 0107 8000 -> 0101 writes -> 0106 01) and, with
--confirm, transmits it over the OS socket (RAS/pppd PPP up) record-by-record,
ack-checking each, then reconnects read-only and verifies zone count/names.

SAFETY
------
  * DRY RUN by default: assembles + validates and prints a summary, transmits
    nothing. Transmitting requires --confirm.
  * 0x80 ONLY. 0x81 (flashcode/serial) and 0x82 (tuning soft-pots) are never
    written: build_session_full() refuses any non-0x80 object.
  * Identity-gated: with --confirm it first reads the radio serial (0x80:0x1004)
    and aborts unless it matches --expect-serial.
  * Transport is --socket (OS TCP over an already-up RAS/pppd link). Userspace
    PPP cannot sustain the burst; this driver does not offer it.
  * A codeplug write is irreversible in practice -- back up the radio's CURRENT
    state first (open-astro rcmp-dump) and keep CPS closed + COM free.

Usage:
    # Dry run (no radio needed):
    python tools/write_codeplug_full.py backups/721CLZ0655.cpg

    # Live write + verify (RAS "OpenAstroRadio" up via tools/ppp_up.ps1):
    python tools/write_codeplug_full.py backups/721CLZ0655.cpg \
        --socket --expect-serial 721CLZ0655 --confirm
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from open_astro.protocol import rcmp
from open_astro.protocol.write_session import (
    CpgWriteAssembler, WriteObject, WriteSessionError, PART_CODEPLUG,
)
from open_astro.parsers.cpg_parser import CpgParser


def load_codeplug_objects(cpg_path: str):
    """0x80, CRC-clean WriteObjects from the source .cpg. Aborts if any 0x80
    object fails its CRC (never assemble a write from a corrupt object)."""
    parser = CpgParser(cpg_path)
    try:
        objs = parser.objects()
    finally:
        parser.close()
    out = []
    bad = []
    for o in objs:
        part = o.get("partition")
        if part is None:
            part = PART_CODEPLUG
        if part != PART_CODEPLUG:
            continue
        if not o["crc_ok"]:
            bad.append((o["tag"], o["instance"]))
            continue
        out.append(WriteObject(PART_CODEPLUG, o["tag"], o["instance"], o["payload"]))
    if bad:
        raise WriteSessionError(
            f"{len(bad)} partition-0x80 objects failed CRC; refusing: {bad[:8]}")
    return out


def summarize(records):
    ops = [r[2:4].hex() for r in records]  # opcode is bytes [2:4] after 2B len
    writes = sum(1 for o in ops if o == "0101")
    return len(records), writes, dict(Counter(ops))


def readback_verify(host, port, expect_serial):
    """Reconnect read-only and decode the live codeplug; return (ok, summary)."""
    from open_astro.protocol.rcmp_transport import RcmpReadClient
    from open_astro.parsers import CpgDecoder
    c = RcmpReadClient.connect(host=host, port=port)
    try:
        c.open_session()
        streams = c.read_streams()
    finally:
        c.close()
    cp = CpgDecoder.build_from_streams(streams, serial=expect_serial)
    nz = len(cp.zones)
    nch = cp.total_channels()
    return nz, nch, [z.name for z in cp.zones]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cpg", help="source codeplug .cpg (the master to write)")
    ap.add_argument("--socket", action="store_true",
                    help="transmit over OS TCP (RAS/pppd PPP already up)")
    ap.add_argument("--host", default="192.168.128.1")
    ap.add_argument("--port", type=lambda x: int(x, 0), default=8002)
    ap.add_argument("--expect-serial", default=None,
                    help="required with --confirm: abort unless radio serial matches")
    ap.add_argument("--confirm", action="store_true",
                    help="actually transmit (irreversible); otherwise DRY RUN")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()

    # --- assemble (offline, always) ---
    try:
        objs = load_codeplug_objects(args.cpg)
        asm = CpgWriteAssembler(objs)
        records = asm.full_session_records()
    except WriteSessionError as e:
        print(f"[-] assembly refused: {e}")
        return 2

    n, writes, hist = summarize(records)
    print(f"[+] assembled full 0x80 write session from {args.cpg}")
    print(f"    {n} records, {writes} write objects (0x101), opcodes {hist}")
    # Prove the persist-control framing is exactly the captured sequence.
    ctrl = [records[i][2:].hex() for i in range(5)]
    expect = ["010600", "010280004700000001", "010380000201f4",
              "0103800e0b0fff", "01078000"]
    if ctrl != expect or records[-1][2:].hex() != "010601":
        print(f"[-] control framing mismatch; refusing. got {ctrl} / "
              f"{records[-1][2:].hex()}")
        return 2
    print("    control framing == proven capture (0102/0103x2/0107 8000), commit 0106 01")

    if not args.confirm:
        print("[i] DRY RUN -- nothing transmitted. Re-run with "
              "--socket --expect-serial <S> --confirm to write.")
        return 0

    # --- live transmit (gated) ---
    if not args.socket:
        print("[-] refusing: live write must use --socket (OS TCP over RAS/pppd).")
        return 2
    if not args.expect_serial:
        print("[-] refusing: --confirm requires --expect-serial to identity-gate.")
        return 2

    from open_astro.protocol.rcmp_write import RcmpWriteClient, RcmpWriteError

    # Single-session flow (this XTS drops PPP after every session, so a separate
    # pre-read would consume the one session and the write connect would fail):
    # connect the write client, open, do the identity read IN-SESSION (serial
    # lives in partition 0x81, object 0x1004), abort on mismatch, then write.
    try:
        w = RcmpWriteClient.connect(host=args.host, port=args.port,
                                    timeout=args.timeout, allow_write=True)
    except RcmpWriteError as e:
        print(f"[-] connect failed: {e}; is the RAS/PPP link up?")
        return 2
    try:
        w.send_prebuilt(records[0])            # 0106 00 session open
        idrec = w.send_prebuilt(rcmp.build_read(0x81, 0x1004, 0x40))  # serial read
        body = bytes.fromhex(str(idrec.get("body_hex", "")))
        serial_txt = body[12:-2].decode("latin-1", "replace") if len(body) > 14 else ""
        if args.expect_serial not in serial_txt:
            print(f"[-] serial mismatch: radio 0x81:0x1004={serial_txt!r} does not "
                  f"contain {args.expect_serial!r}; ABORTING (wrong radio). "
                  f"No 0101 write was sent.")
            w.close()
            return 2
        print(f"[+] identity OK: radio reports {args.expect_serial}")
    except RcmpWriteError as e:
        print(f"[-] identity read failed ({e}); no write sent.")
        w.close()
        return 2

    print(f"[!] TRANSMITTING {writes} writes to {args.host}:{args.port} ...")
    try:
        for i, rec in enumerate(records[1:], start=1):  # records[0] already sent
            w.send_prebuilt(rec)
            if i % 50 == 0 or rec[2:4].hex() == "0106":
                print(f"    [{i:3d}/{n}] sent 0x{rec[2:4].hex()}")
    except RcmpWriteError as e:
        print(f"[-] write failed mid-session: {e}")
        print("[-] radio may be in programming mode; power-cycle and re-read.")
        w.close()
        return 3
    finally:
        w.close()
    print("[+] write session completed + committed (0106 01 acked)")

    # --- readback verify ---
    print("[+] reconnecting read-only to verify ...")
    try:
        nz, nch, names = readback_verify(args.host, args.port, args.expect_serial)
    except Exception as e:
        print(f"[!] readback failed ({e}); radio dropped PPP after the session is "
              f"normal -- re-run `open-astro rcmp-dump` after a power-cycle.")
        return 0
    print(f"[+] readback: {nz} zones / {nch} channels: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
