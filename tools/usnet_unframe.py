#!/usr/bin/env python3
"""Unframe Motorola Depot's device-13 USNET link into RCMP records.

Background
----------
CPS talks to a radio over USB CDC-ACM "device 5" (Windows-RAS PPP), which
``tools/decode_usb_ppp.py`` decodes end-to-end (RFC1662 async-HDLC + VJ + TCP
to port 8002 -> RCMP). Depot instead programs over a *different* USB interface,
observed as "device 13" (OUT) paired with "device 35" (IN) -- the US Software
"USNET" embedded PPP stack wrapped by ``RadioCustStack10.dll``
(``CUSNETppp::PPPConnect/PPPHandshake``). See ``docs/SESSION_LOG_20261101.md``.

Why the device-5 decoder returned "noise" on these captures: it sources bytes
from tshark's ``usb.capdata`` field, which is EMPTY for device 13 (Wireshark
never saw that interface's descriptors mid-capture). The bytes are in the file
though -- ``tools/usbpcap_read.py`` parses the USBPcap framing natively and
recovers them per device. This module is the small glue that was missing: pull
device 13/35 natively, then run the *same* HDLC+VJ+RCMP pipeline the device-5
decoder already uses (and which is byte-validated on a real write session).

The link layer (USNET async-HDLC PPP) is interchangeable with RAS PPP: both
carry identical RCMP to the radio at 192.168.128.1:8002 (RE confirmed, 11-01).
So once device 13 is unframed, its records are ordinary RCMP -- read with the
existing ``open_astro.protocol.rcmp`` parser.

This is read-only: it only parses a .pcap. It does not touch a radio.

Usage:
    python tools/usnet_unframe.py captures/depot_write_<ts>.pcap
    python tools/usnet_unframe.py captures/depot_adp_<ts>.pcap --out-dev 13 --in-dev 35
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List, Optional

# Repo layout: put src/ ahead of the repo root so `open_astro` resolves to the
# package, not any stray top-level module.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
if _REPO not in sys.path:
    sys.path.insert(1, _REPO)

from open_astro.protocol import rcmp  # noqa: E402
from tools.usbpcap_read import device_streams  # noqa: E402
from tools.decode_usb_ppp import (  # noqa: E402
    split_at_and_ppp, parse_ppp_frames, extract_rcmp, vj_compressed_data,
)


def frames_to_rcmp_stream(ppp_region: bytes) -> bytes:
    """Run the validated PPP+VJ pipeline over one device's HDLC region and
    return the reassembled RCMP byte stream (TCP:8002 data in frame order)."""
    stream = bytearray()
    for f in parse_ppp_frames(ppp_region):
        pl = bytes.fromhex(f["payload_hex"])
        if f["proto"] in (0x21, 0x0021):                 # plain IP
            for seg in extract_rcmp(pl):
                stream += bytes.fromhex(seg["rcmp_hex"])
        elif f["proto"] == 0x002F:                       # VJ uncompressed TCP/IP
            for seg in extract_rcmp(pl, vj_uncompressed=True):
                stream += bytes.fromhex(seg["rcmp_hex"])
        elif f["proto"] == 0x002D:                       # VJ compressed TCP/IP
            stream += vj_compressed_data(pl)
    return bytes(stream)


def unframe_device(pcap: str, out_dev: int = 13,
                   in_dev: Optional[int] = 35) -> Dict[str, object]:
    """Decode the Depot device-13/35 USNET link in `pcap` to RCMP.

    Returns a dict with, per direction, the PPP proto histogram, the decoded
    RCMP records (parsed), and flags for the interesting opcodes."""
    streams = device_streams(pcap)
    result: Dict[str, object] = {"pcap": pcap, "devices_present": sorted(streams),
                                 "out_dev": out_dev, "in_dev": in_dev}
    directions = [("OUT host->radio", out_dev, 0)]
    if in_dev is not None:
        directions.append(("IN radio->host", in_dev, 1))

    for label, dev, idx in directions:
        dev_stream = streams.get(dev, {}).get(idx, b"")
        at_region, ppp_region = split_at_and_ppp(dev_stream)
        frames = parse_ppp_frames(ppp_region) if ppp_region else []
        proto_hist = Counter(f["proto_name"] for f in frames)
        rcmp_stream = frames_to_rcmp_stream(ppp_region) if ppp_region else b""
        records = [rcmp.parse_record(r) for r in rcmp.iter_records(rcmp_stream)]
        result[label] = {
            "device": dev,
            "bytes_total": len(dev_stream),
            "hdlc_flags": dev_stream.count(0x7E),
            "ppp_frame_count": len(frames),
            "ppp_proto_histogram": dict(proto_hist),
            "rcmp_stream_hex": rcmp_stream.hex(),
            "rcmp_records": records,
        }
    result["findings"] = _findings(result)
    return result


def _findings(result: Dict[str, object]) -> Dict[str, object]:
    """Flag the things we are hunting: a 0x0107 UnlockSecurity record and any
    write (0x0101) to the locked security partition 0x81."""
    has_0107 = False
    writes_81: List[Dict[str, object]] = []
    opcodes: Counter = Counter()
    for label in ("OUT host->radio", "IN radio->host"):
        side = result.get(label)
        if not isinstance(side, dict):
            continue
        for rec in side.get("rcmp_records", []):
            op = rec.get("opcode")
            if op is None:
                continue
            opcodes[f"0x{op:04x}"] += 1
            base = op & 0x7FFF
            if base == rcmp.OP_CHECKSUM:            # 0x0107
                has_0107 = True
            if base == rcmp.OP_WRITE and rec.get("partition") == 0x81:
                writes_81.append({"object": rec.get("object"),
                                  "instance": rec.get("instance")})
    return {
        "unlock_0107_present": has_0107,
        "partition_0x81_writes": writes_81,
        "opcode_histogram": dict(opcodes),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcap", help="USBPcap capture of a Depot session")
    ap.add_argument("--out-dev", type=int, default=13,
                    help="USB device number of the OUT (host->radio) stream")
    ap.add_argument("--in-dev", type=int, default=35,
                    help="USB device number of the IN (radio->host) stream; "
                         "pass -1 if the capture has no IN device")
    ap.add_argument("-o", "--output", default=None,
                    help="write decoded JSON here (default: alongside the pcap)")
    args = ap.parse_args()

    if not os.path.exists(args.pcap):
        print(f"[-] no such capture: {args.pcap}")
        return 2
    in_dev = None if args.in_dev < 0 else args.in_dev
    res = unframe_device(args.pcap, out_dev=args.out_dev, in_dev=in_dev)

    print(f"[i] devices in capture: {res['devices_present']}")
    for label in ("OUT host->radio", "IN radio->host"):
        side = res.get(label)
        if not isinstance(side, dict):
            continue
        print(f"[i] {label}: dev {side['device']}  {side['bytes_total']} B  "
              f"{side['hdlc_flags']} HDLC flags  {side['ppp_frame_count']} PPP frames  "
              f"protos={side['ppp_proto_histogram']}  "
              f"{len(side['rcmp_records'])} RCMP records")
    f = res["findings"]
    print(f"[i] opcodes: {f['opcode_histogram']}")
    print(f"[{'+' if f['unlock_0107_present'] else '-'}] "
          f"0x0107 UnlockSecurity present: {f['unlock_0107_present']}")
    print(f"[{'+' if f['partition_0x81_writes'] else '-'}] "
          f"partition 0x81 writes: {f['partition_0x81_writes'] or 'none'}")

    out = args.output or (os.path.splitext(args.pcap)[0] + "_usnet_decoded.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(f"[i] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
