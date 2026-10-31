#!/usr/bin/env python3
"""Resilient full-codeplug RCMP read for wedge-prone XTS 5000 radios.

The stock `open-astro rcmp-dump` opens ONE RCMP session and reads every object
tag inside it. On the XTS 5000 (721CLZ0655) that single long session wedges the
radio's PPP stack partway through (observed: TCP retransmit limit reached, then
no SYN-ACK until a power-cycle). The radio also drops PPP after each session by
design.

This driver instead reads ONE tag per short PPP session, reconnecting a fresh
`PppTcpConn` for the next tag, and retries a batch on transient PPP/RCMP drops.
That matches the only stable live pattern we have (short batched reads +
reconnect-on-drop). It is READ-ONLY: it uses RcmpReadClient, which has no write
method.

Usage:
    python scratchpad/resilient_dump.py --serial COM9 -o scratchpad/dump.json
    python scratchpad/resilient_dump.py --serial /dev/ttyACM0 -o dump.json

Prereq: CPS closed and PPP lowered so the COM port is free. If the radio is
already wedged (probe shows no SYN-ACK), power-cycle it before running.
"""
from __future__ import annotations

import argparse
import sys
import time

from open_astro.protocol import rcmp
from open_astro.protocol.rcmp_transport import (
    RcmpReadClient, RcmpError, CODEPLUG_OBJECT_TAGS, RCMP_PORT,
)
from open_astro.protocol.ppp_link import PppTcpConn, PppError
from open_astro.parsers import CpgDecoder, JsonParser


def _wait_for_port(serial, deadline_s):
    """Block until `serial` can be opened, or deadline passes.

    The XTS 5000 re-enumerates its USB CDC-ACM interface after every PPP
    session, so the COM port briefly vanishes / returns 'Access is denied' /
    'device not functioning'. Opening too soon races that re-enumeration. Poll
    a cheap open until it succeeds."""
    import serial as _pyserial
    end = time.time() + deadline_s
    while time.time() < end:
        try:
            s = _pyserial.Serial(serial)
            s.close()
            return True
        except Exception:
            time.sleep(1.0)
    return False


def read_tag(serial, dport, timeout, tag, max_inst, block, retries, backoff):
    """Read all instances of one object tag in its own PPP session.

    Returns a list of (tag, inst, payload). Retries the whole tag on a PPP or
    RCMP drop (fresh session each attempt), since a mid-tag drop can leave the
    radio's TCP in a bad state. Waits out the per-session USB re-enumeration
    before each attempt so the port is actually openable."""
    last_err = None
    for attempt in range(1, retries + 1):
        conn = None
        got = []
        try:
            _wait_for_port(serial, deadline_s=max(10.0, backoff * attempt * 2))
            conn = PppTcpConn(serial, dport=dport, timeout=timeout)
            client = RcmpReadClient(conn, timeout=timeout)
            client.open_session()
            for inst in range(max_inst):
                data = client.read_object(rcmp.PART_CODEPLUG, tag, block, inst)
                if not data:
                    break
                got.append((tag, inst, data))
                print(f"    0x{tag:04x} inst {inst}: {len(data)} bytes",
                      file=sys.stderr)
            return got
        except (PppError, RcmpError, OSError) as e:
            last_err = e
            print(f"    0x{tag:04x}: attempt {attempt}/{retries} dropped ({e})",
                  file=sys.stderr)
            time.sleep(backoff * attempt)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    print(f"    0x{tag:04x}: GAVE UP after {retries} attempts ({last_err})",
          file=sys.stderr)
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serial", required=True,
                    help="radio COM port / tty (e.g. COM9, /dev/ttyACM0)")
    ap.add_argument("-o", "--output", required=True, help="output JSON path")
    ap.add_argument("--port", type=lambda x: int(x, 0), default=RCMP_PORT,
                    help="radio TCP port (default 8002)")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--max-inst", type=int, default=32)
    ap.add_argument("--block", type=lambda x: int(x, 0), default=0x0370)
    ap.add_argument("--retries", type=int, default=5,
                    help="attempts per tag before giving up")
    ap.add_argument("--backoff", type=float, default=4.0,
                    help="base seconds between retries (grows per attempt)")
    ap.add_argument("--settle", type=float, default=6.0,
                    help="seconds between tags (lets PPP drop + USB re-enumerate)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--serial-number", dest="serial_number", default=None)
    args = ap.parse_args()

    streams = []
    for tag in CODEPLUG_OBJECT_TAGS:
        print(f"[+] tag 0x{tag:04x} ...", file=sys.stderr)
        streams.extend(read_tag(args.serial, args.port, args.timeout, tag,
                                args.max_inst, args.block, args.retries,
                                args.backoff))
        time.sleep(args.settle)

    if not streams:
        print("[-] no objects read -- radio likely wedged; power-cycle and retry")
        sys.exit(1)

    print(f"[+] read {len(streams)} objects across "
          f"{len(CODEPLUG_OBJECT_TAGS)} short sessions")
    codeplug = CpgDecoder.build_from_streams(streams, model=args.model,
                                             serial=args.serial_number)
    JsonParser.save_file(codeplug, args.output)
    print(f"[+] decoded {len(codeplug.zones)} zones / "
          f"{codeplug.total_channels()} channels, bandsplit {codeplug.bandsplit}")
    print(f"[+] wrote typed codeplug JSON: {args.output}")


if __name__ == "__main__":
    main()
