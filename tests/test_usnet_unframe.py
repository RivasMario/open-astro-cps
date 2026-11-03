"""Prove tools/usnet_unframe.py recovers RCMP from a device-13 USNET stream.

No real Depot capture is needed: we synthesise a minimal USBPcap file holding a
device-13 OUT bulk transfer whose payload is one async-HDLC PPP frame wrapping
an IPv4/TCP (port 8002) segment whose TCP data is a known RCMP record. The tool
must pull the device-13 bytes natively, unframe the HDLC+PPP, extract the TCP
payload, and hand back the exact RCMP record (and flag a partition-0x81 write).

This locks in the glue; the HDLC/VJ/TCP primitives themselves are the ones the
device-5 decoder already uses and which are byte-validated on a real session.
"""
import os
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "src"))
if REPO not in sys.path:
    sys.path.insert(1, REPO)

from open_astro.protocol import rcmp
from tools.decode_usb_ppp import fcs16
from tools.usnet_unframe import unframe_device


# -- builders: construct the exact bytes the real stack would put on the wire --
def _ppp_hdlc_frame(proto: int, payload: bytes) -> bytes:
    """A single async-HDLC PPP frame: 7E | FF 03 proto payload FCS16(le) | 7E,
    with 0x7E/0x7D byte-stuffed (the minimum the unstuffer reverses)."""
    inner = b"\xff\x03" + struct.pack(">H", proto) + payload
    inner += struct.pack("<H", fcs16(inner))
    stuffed = bytearray()
    for b in inner:
        if b in (0x7E, 0x7D):
            stuffed += bytes([0x7D, b ^ 0x20])
        else:
            stuffed.append(b)
    return b"\x7e" + bytes(stuffed) + b"\x7e"


def _ipv4_tcp(dport: int, data: bytes) -> bytes:
    """Minimal IPv4(proto=6)+TCP packet carrying `data` to `dport`. Checksums
    are left zero -- the decoder does not verify them."""
    tcp = struct.pack(">HHLLBBHHH", 40000, dport, 0, 0, (5 << 4), 0, 0, 0, 0) + data
    total = 20 + len(tcp)
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total, 0, 0, 64, 6, 0,
                     b"\xc0\xa8\x80\x02", b"\xc0\xa8\x80\x01")  # 192.168.128.2 -> .1
    return ip + tcp


def _usbpcap_file(path: str, device: int, payload: bytes) -> None:
    """Write a one-packet USBPcap (DLT 249) file with a bulk OUT transfer on
    `device` carrying `payload`, matching tools/usbpcap_read.py's parser."""
    # USBPcap packet: header_len(u16@0) ... device(u16@19) endpoint(@21)
    # transfer(@22) data_len(u32@23); payload starts at header_len.
    hdr_len = 27
    pkt = bytearray(hdr_len)
    struct.pack_into("<H", pkt, 0, hdr_len)      # headerLen
    struct.pack_into("<H", pkt, 19, device)      # device number
    pkt[21] = 0x00                               # endpoint (bit7=0 -> OUT)
    pkt[22] = 3                                  # transfer type: bulk
    struct.pack_into("<I", pkt, 23, len(payload))
    pkt += payload
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 0x40000, 249))
        f.write(struct.pack("<IIII", 0, 0, len(pkt), len(pkt)))  # record header
        f.write(pkt)


def test_device13_usnet_unframes_to_rcmp(tmp_path):
    # a real RCMP record: a write to the locked security partition 0x81,
    # object 0x1006 (the flashcode string) -- the thing we hunt in Depot caps.
    record = rcmp.build_write(0x81, 0x1006, b"000008-006410-3\x00", inst=0)
    frame = _ppp_hdlc_frame(0x0021, _ipv4_tcp(rcmp_port := 8002, record))
    pcap = str(tmp_path / "depot_fake.pcap")
    _usbpcap_file(pcap, device=13, payload=b"CLIENT" + frame)

    res = unframe_device(pcap, out_dev=13, in_dev=None)

    out = res["OUT host->radio"]
    assert out["bytes_total"] > 0, "device 13 bytes were not recovered"
    assert out["ppp_frame_count"] == 1
    assert out["ppp_proto_histogram"].get("IP") == 1
    # the reassembled RCMP stream must equal exactly the record we embedded
    assert out["rcmp_stream_hex"] == record.hex()
    assert len(out["rcmp_records"]) == 1
    rec = out["rcmp_records"][0]
    assert rec["opcode"] == rcmp.OP_WRITE
    assert rec["partition"] == 0x81
    assert rec["object"] == 0x1006
    # findings must flag the partition-0x81 write
    assert res["findings"]["partition_0x81_writes"] == [{"object": 0x1006, "instance": 0}]


def test_missing_device_is_empty_not_crash(tmp_path):
    # capture with only device 13; asking for a non-existent in-dev must be safe
    frame = _ppp_hdlc_frame(0x0021, _ipv4_tcp(8002, rcmp.build_read(0x81, 0x1006, 0x10)))
    pcap = str(tmp_path / "only13.pcap")
    _usbpcap_file(pcap, device=13, payload=frame)
    res = unframe_device(pcap, out_dev=13, in_dev=35)
    assert res["IN radio->host"]["bytes_total"] == 0
    assert res["OUT host->radio"]["ppp_frame_count"] == 1
