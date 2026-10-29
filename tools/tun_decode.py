"""Decoder for Motorola A25Tuner.exe `.tun` files (RF soft-pot calibration).

The `.tun` file is an MFC `CArchive` serialization of a `CSaveValues` object.
Format reverse-engineered from three real XTS 2500 tuner backups on 2026-10-23
(205CFR2930 = 700/800 MHz, 407CHT0214 = VHF/UHF):

  offset 0x00  Pascal-style (1-byte length + bytes) strings:
                 serial, model, a short flag ("No")
  byte  0x2f    POINTS = number of frequency calibration points per record
  ~0x4f         MFC class block: ff ff 01 00 <len16> "CSaveValues"
  records       each begins with the 6-byte marker 01 80 01 00 00 00,
                then uint32 record_index, then POINTS * (uint32 freq_raw,
                uint32 value) little-endian pairs.
                freq_hz = freq_raw * 5 (same scaling as the .cpg).

Each record is one tuning parameter (TX power / ref osc / deviation / etc.)
sampled across POINTS frequencies spanning the radio's band(s). The uint32
"value" is the soft-pot setting at that frequency. We do not yet have the
record_index -> parameter-name map from CPS, so records are reported by index.

Read-only: parses a file, prints/returns structured calibration data. Never
writes to a radio.
"""
import struct
import sys
from typing import Dict, List

MARKER = b"\x01\x80\x01\x00\x00\x00"


def _read_pstr(buf: bytes, off: int):
    n = buf[off]
    return buf[off + 1 : off + 1 + n].decode("latin1"), off + 1 + n


def decode_tun(path: str) -> Dict:
    with open(path, "rb") as f:
        buf = f.read()

    serial, off = _read_pstr(buf, 0)
    model, off = _read_pstr(buf, off)
    flag, off = _read_pstr(buf, off)
    points = buf[0x2F]

    records: List[Dict] = []
    pos = 0
    while True:
        pos = buf.find(MARKER, pos)
        if pos < 0:
            break
        idx = struct.unpack_from("<I", buf, pos + len(MARKER))[0]
        data_off = pos + len(MARKER) + 4
        pairs = []
        ok = True
        for i in range(points):
            base = data_off + i * 8
            if base + 8 > len(buf):
                ok = False
                break
            freq_raw, value = struct.unpack_from("<II", buf, base)
            pairs.append((freq_raw * 5, value))
        if ok:
            records.append({"index": idx, "points": pairs})
        pos = data_off + points * 8

    return {
        "serial": serial,
        "model": model,
        "flag": flag,
        "points_per_record": points,
        "records": records,
    }


def _fmt_mhz(hz: int) -> str:
    return f"{hz / 1e6:.4f}"


def main():
    if len(sys.argv) < 2:
        print("usage: tun_decode.py <file.tun> [file.tun ...]")
        sys.exit(2)
    for path in sys.argv[1:]:
        d = decode_tun(path)
        print(f"\n=== {path} ===")
        print(f"serial={d['serial']}  model={d['model']}  flag={d['flag']}  "
              f"points/record={d['points_per_record']}  records={len(d['records'])}")
        if d["records"]:
            freqs = [f for f, _ in d["records"][0]["points"]]
            print(f"cal frequencies (MHz): {', '.join(_fmt_mhz(f) for f in freqs)}")
            lo, hi = min(freqs), max(freqs)
            print(f"band span: {_fmt_mhz(lo)} - {_fmt_mhz(hi)} MHz")
        for r in d["records"]:
            vals = ", ".join(str(v) for _, v in r["points"])
            print(f"  record {r['index']:>3}: values=[{vals}]")


if __name__ == "__main__":
    main()
