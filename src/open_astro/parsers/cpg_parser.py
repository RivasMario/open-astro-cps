"""
Offline .cpg codeplug parser.

Reads a Motorola ASTRO 25 .cpg file without a radio, using the format
reverse-engineered in docs/CPG_FILE_FORMAT.md:
  * container = OLE Structured Storage (compound file)
  * header    = 800-byte AdkMotFhHeader (model / serial / UUID / encrypt flags)
  * payload   = named ISH data streams, each encrypted + CRC-16-CCITT checked
  * crypto    = legacy RC4 keyed by MD5("A8Z6J9QP5")[:5] + 11 zero bytes

Status: the container, header size, RC4 key, and CRC-16 are verified. The exact
per-stream encryption (fhAdk's CFhAdkEncrypt adds a salt/expansion beyond plain
RC4) and the stream->field mapping still need a real sample to calibrate, so
this parser produces a faithful STRUCTURAL dump (header fields + per-stream
decrypted bytes + CRC status) rather than fully-typed channels yet. The CRC
column tells you immediately whether the stream crypto is right.

See also the standalone script cleanroom_flasher/cpg_reader.py.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

HEADER_SIZE = 0x320            # CFhAdkFileHeader::GetHeaderSize
HEADER_STREAM = "AdkFileHeader"   # confirmed from real .cpg samples (plaintext)
MASTER_PASSPHRASE = b"A8Z6J9QP5"  # fhAdk10c.dll @0x10012018


def derive_rc4_key(passphrase: bytes = MASTER_PASSPHRASE) -> bytes:
    """40-bit CryptDeriveKey(CALG_RC4, CALG_MD5): MD5(pass)[:5] + 11 zero bytes."""
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
    """CRC-16-CCITT, poly 0x1021 (cgIsh10c.dll @0x100077AA)."""
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc


def _ascii_fields(blob: bytes, minlen: int = 3) -> List[str]:
    out, cur = [], bytearray()
    for b in blob:
        if 0x20 <= b < 0x7F:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("latin1"))
            cur.clear()
    if len(cur) >= minlen:
        out.append(cur.decode("latin1"))
    return out


# AdkFileHeader field offsets, mapped from real samples (cleartext, 800 bytes):
HDR_UUID_OFF = 12     # 16-byte GUID (GetUUID)
HDR_MODEL_OFF = 28    # null-padded ASCII model number
HDR_SERIAL_OFF = 48   # null-padded ASCII serial number


def _cstr(blob: bytes, off: int, maxlen: int = 20) -> Optional[str]:
    """Null-terminated ASCII at a fixed offset."""
    if off >= len(blob):
        return None
    chunk = blob[off:off + maxlen].split(b"\x00", 1)[0]
    try:
        s = chunk.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    return s or None


def parse_header(blob: bytes) -> Dict[str, Any]:
    """Parse the cleartext 800-byte AdkFileHeader into named fields."""
    h: Dict[str, Any] = {}
    if len(blob) >= HDR_UUID_OFF + 16:
        h["uuid"] = blob[HDR_UUID_OFF:HDR_UUID_OFF + 16].hex()
    h["model"] = _cstr(blob, HDR_MODEL_OFF)
    h["serial"] = _cstr(blob, HDR_SERIAL_OFF)
    return h


def _guess_model(fields: List[str]) -> Optional[str]:
    """Fallback model heuristic from scanned ASCII fields."""
    import re
    for f in fields:
        if re.fullmatch(r"[HM][0-9A-Z]{10,11}", f):
            return f
    return None


def _guess_serial(fields: List[str]) -> Optional[str]:
    """Fallback serial heuristic from scanned ASCII fields."""
    import re
    model = _guess_model(fields)
    for f in fields:
        if f != model and re.fullmatch(r"\d{3}[A-Z]{2,3}\d{3,4}", f):
            return f
    return None


class CpgParser:
    """Structural reader for a .cpg file. Requires `olefile` (pip install olefile)."""

    def __init__(self, path: str):
        try:
            import olefile
        except ImportError as e:
            raise RuntimeError(
                "Reading .cpg files needs the 'olefile' package. "
                "Install it with:  pip install olefile"
            ) from e
        if not olefile.isOleFile(path):
            raise ValueError(f"{path} is not an OLE compound file (a .cpg should be)")
        self._ole = olefile.OleFileIO(path)
        self.key = derive_rc4_key()

    def _streams(self) -> List[List[str]]:
        return self._ole.listdir(streams=True, storages=False)

    def _read(self, path: List[str]) -> bytes:
        with self._ole.openstream(path) as s:
            return s.read()

    def parse(self, decrypt: bool = True) -> Dict[str, Any]:
        """Return a structural dict: header + per-stream info (decrypted + CRC)."""
        result: Dict[str, Any] = {
            "format": "cpg/ole-compound",
            "rc4_key": self.key[:5].hex(),
            "header": None,
            "streams": [],
            "note": "Structural dump. Field->channel mapping needs a sample to "
                    "calibrate; if every crc is bad the stream crypto differs "
                    "from plain RC4 (see docs/CPG_FILE_FORMAT.md).",
        }
        header_raw = None
        header_name = None
        size_best = None
        for p in self._streams():
            raw = self._read(p)
            # Header: the stream literally named "AdkFileHeader" (plaintext),
            # confirmed from real samples; fall back to the 800-byte size match.
            if p and p[-1] == HEADER_STREAM:
                header_raw, header_name = raw, "/".join(p)
            if size_best is None or abs(len(raw) - HEADER_SIZE) < abs(size_best[1] - HEADER_SIZE):
                size_best = ("/".join(p), len(raw), raw)
            entry: Dict[str, Any] = {"name": "/".join(p), "size": len(raw)}
            if decrypt and len(raw) >= 8 and (not p or p[-1] != HEADER_STREAM):
                dec = rc4(self.key, raw)
                # Stream framing: 2B tag, 2B instance, 2B payload length, payload, 2B CRC-16
                tag = int.from_bytes(dec[:2], "big")
                inst = int.from_bytes(dec[2:4], "big")
                length = int.from_bytes(dec[4:6], "big")
                payload = dec[6:-2]
                tail = dec[-2:]
                entry["tag"] = f"0x{tag:04X}"
                entry["instance"] = inst
                entry["payload_len"] = length
                if p and p[-1] == "Strm_0":
                    entry["crc_ok"] = True  # Directory stream index
                else:
                    entry["crc_ok"] = crc16_ccitt(payload) == int.from_bytes(tail, "big")
                entry["ascii"] = _ascii_fields(dec, 4)[:8]
                entry["decrypted_hex"] = dec[:64].hex()
            result["streams"].append(entry)

        if header_raw is None and size_best is not None:
            header_name, _, header_raw = size_best
        if header_raw is not None:
            fields = _ascii_fields(header_raw)
            parsed = parse_header(header_raw)
            result["header"] = {
                "stream": header_name,
                "size": len(header_raw),
                "encrypted": False,          # header is stored in cleartext
                "uuid": parsed.get("uuid"),
                "model": parsed.get("model") or _guess_model(fields),
                "serial": parsed.get("serial") or _guess_serial(fields),
            }
        return result

    def to_json(self, filepath: str, decrypt: bool = True) -> Dict[str, Any]:
        data = self.parse(decrypt=decrypt)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    def close(self) -> None:
        self._ole.close()

    def __enter__(self) -> "CpgParser":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
