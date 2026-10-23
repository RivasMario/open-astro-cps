"""
Offline .cpg codeplug reader (no radio needed).

Built from the reverse-engineered format in docs/CPG_FILE_FORMAT.md:
  * container  = OLE Structured Storage (compound file, magic D0CF11E0)
  * header     = AdkMotFhHeader, 800 bytes (model/serial/UUID/encrypt flags)
  * payload    = named ISH data streams, each encrypted + CRC-16-CCITT checked
  * crypto     = legacy RC4 keyed by MD5("A8Z6J9QP5")[:5] + 11 zero bytes
                 (the CryptDeriveKey 40-bit derivation), OR the newer SdkCrypto.

STATUS: UNTESTED against a real .cpg (none available when written, 2026-10-22).
Structurally faithful to the format doc, but these need a real file to confirm:
  * the exact field offsets inside the 800-byte header,
  * the exact stream encryption (fhAdk's CFhAdkEncrypt expands output and carries
    a random salt via encryptChar -- the plain-RC4 path below is the documented
    best guess; adjust once a sample decrypts cleanly),
  * which streams are header vs data, and the stream->content map.
It degrades gracefully: it will always dump structure even if decryption is off.

Usage:
    pip install --user olefile
    python cpg_reader.py path/to/Codeplug.cpg
    python cpg_reader.py path/to/Codeplug.cpg --raw   # hexdump streams, no decrypt
"""
from __future__ import annotations

import hashlib
import sys
from typing import Dict, List, Optional

try:
    import olefile
except ImportError:
    print("olefile required: pip install --user olefile")
    sys.exit(1)

HEADER_SIZE = 0x320  # 800 bytes, from CFhAdkFileHeader::GetHeaderSize
MASTER_PASSPHRASE = b"A8Z6J9QP5"  # from fhAdk10c.dll @0x10012018


def derive_rc4_key(passphrase: bytes = MASTER_PASSPHRASE) -> bytes:
    """40-bit key: MD5(passphrase)[:5] padded to 16 bytes with zeros
    (Windows CryptDeriveKey(CALG_RC4, CALG_MD5) with an 11-byte zero salt)."""
    return hashlib.md5(passphrase).digest()[:5] + b"\x00" * 11


def rc4(key: bytes, data: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i] + S[j]) & 0xFF])
    return bytes(out)


def crc16_ccitt(data: bytes, init: int = 0x0000) -> int:
    """CRC-16-CCITT, poly 0x1021, as in cgIsh10c.dll (@0x100077AA)."""
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc


class CpgReader:
    def __init__(self, path: str):
        if not olefile.isOleFile(path):
            raise ValueError(f"{path} is not an OLE compound file (.cpg should be)")
        self.ole = olefile.OleFileIO(path)
        self.key = derive_rc4_key()

    def streams(self) -> List[List[str]]:
        return self.ole.listdir(streams=True, storages=False)

    def read_stream(self, path: List[str]) -> bytes:
        with self.ole.openstream(path) as s:
            return s.read()

    def find_header(self) -> Optional[bytes]:
        """Best-effort: the stream whose size matches the 800-byte header, or the
        largest small stream. (Exact header stream name needs a sample.)"""
        best = None
        for p in self.streams():
            data = self.read_stream(p)
            if len(data) == HEADER_SIZE:
                return data
            if best is None or abs(len(data) - HEADER_SIZE) < abs(len(best) - HEADER_SIZE):
                best = data
        return best

    @staticmethod
    def ascii_fields(blob: bytes, minlen: int = 3) -> List[str]:
        out, cur = [], bytearray()
        for b in blob:
            if 0x20 <= b < 0x7f:
                cur.append(b)
            else:
                if len(cur) >= minlen:
                    out.append(cur.decode("latin1"))
                cur.clear()
        if len(cur) >= minlen:
            out.append(cur.decode("latin1"))
        return out

    def dump(self, decrypt: bool = True) -> None:
        print(f"[+] OLE compound file. RC4 key = {self.key[:5].hex()} (40-bit)")
        hdr = self.find_header()
        if hdr:
            print(f"[+] header candidate ({len(hdr)} B). ASCII fields (model/serial/UUID likely):")
            for f in self.ascii_fields(hdr):
                print(f"      {f}")
        print(f"[+] {len(self.streams())} streams:")
        for p in self.streams():
            name = "/".join(p)
            raw = self.read_stream(p)
            line = f"    {name:28s} {len(raw):6d} B"
            if decrypt and len(raw) > 2:
                dec = rc4(self.key, raw)
                # last 2 bytes often the CRC-16 over the body
                body, tail = dec[:-2], dec[-2:]
                got = crc16_ccitt(body)
                want = int.from_bytes(tail, "big")
                line += f"  crc={'OK' if got == want else f'{got:04x}!={want:04x}'}"
                preview = self.ascii_fields(dec, 4)[:3]
                if preview:
                    line += "  " + " | ".join(preview)
            print(line)
        print("\nNOTE: untested format -- if CRCs all fail, the stream crypto isn't "
              "plain RC4 (see module docstring) and needs a sample to calibrate.")

    def close(self) -> None:
        self.ole.close()


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    path = next(a for a in args if not a.startswith("-"))
    decrypt = "--raw" not in args
    r = CpgReader(path)
    try:
        r.dump(decrypt=decrypt)
    finally:
        r.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
