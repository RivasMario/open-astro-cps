"""Native reader for USBPcap pcap files (DLT_USBPCAP = 249).

tshark's `usb.capdata` field is unreliable for devices that enumerate in the
middle of a capture (as the radio does when a codeplug WRITE reboots it into
programming mode) -- Wireshark never saw their descriptors, so it does not tag
their bulk payload and `-T fields -e usb.capdata` comes back empty. The bytes
are still in the file, so we parse the USBPcap framing ourselves.

USBPcap packet header (little-endian), per the USBPcap format:
    0  headerLen  u16   (total header length; payload starts here)
    2  irpId      u64
    10 status     u32
    14 function   u16
    16 info       u8    (bit0: 1 = PDO->FDO, i.e. from device / IN)
    17 bus        u16
    19 device     u16
    21 endpoint   u8    (bit7: 1 = IN)
    22 transfer   u8    (0=iso 1=int 2=control 3=bulk)
    23 dataLength u32
Payload = packet[headerLen : headerLen + dataLength].

This is read-only: it only parses a capture file.
"""
from __future__ import annotations

import struct
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


def read_usbpcap(path: str) -> Dict[int, List[Tuple[int, int, bytes]]]:
    """Return {device: [(endpoint, direction, payload)]} in capture order.
    direction: 0 = OUT (host->device), 1 = IN (device->host)."""
    with open(path, "rb") as f:
        blob = f.read()
    if len(blob) < 24:
        return {}
    magic = blob[:4]
    if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        end = "<"
    elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        end = ">"
    else:
        end = "<"  # USBPcap is little-endian in practice
    off = 24  # global header
    out: Dict[int, List[Tuple[int, int, bytes]]] = defaultdict(list)
    while off + 16 <= len(blob):
        _ts, _tu, incl, _orig = struct.unpack_from(end + "IIII", blob, off)
        off += 16
        pkt = blob[off:off + incl]
        off += incl
        if len(pkt) < 27:
            continue
        header_len = struct.unpack_from("<H", pkt, 0)[0]
        device = struct.unpack_from("<H", pkt, 19)[0]
        endpoint = pkt[21]
        data_len = struct.unpack_from("<I", pkt, 23)[0]
        if data_len == 0 or header_len + data_len > len(pkt):
            continue
        payload = pkt[header_len:header_len + data_len]
        direction = 1 if (endpoint & 0x80) else 0
        out[device].append((endpoint, direction, payload))
    return out


def device_streams(path: str) -> Dict[int, Dict[int, bytes]]:
    """Return {device: {0: out_bytes, 1: in_bytes}} reassembled in order."""
    raw = read_usbpcap(path)
    streams: Dict[int, Dict[int, bytes]] = {}
    for dev, items in raw.items():
        agg = {0: bytearray(), 1: bytearray()}
        for _ep, direction, payload in items:
            agg[direction].extend(payload)
        streams[dev] = {0: bytes(agg[0]), 1: bytes(agg[1])}
    return streams


if __name__ == "__main__":
    for dev, s in sorted(device_streams(sys.argv[1]).items()):
        o, i = s[0], s[1]
        print(f"device {dev:>3}: OUT={len(o):<7} IN={len(i):<7} "
              f"7e_out={o.count(0x7e):<5} CLIENT={b'CLIENT' in o + i}")
