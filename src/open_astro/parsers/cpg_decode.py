"""
Typed .cpg -> RadioCodeplug decoder (offline).

Builds on the structural reader in cpg_parser.py. Where cpg_parser dumps every
stream generically (tag / instance / payload / CRC), this module maps the
conventional-channel ISH records into the typed RadioCodeplug / Zone / Channel
models so the result round-trips through JsonParser and CsvParser.

Calibration (from backups/205CFR2930.cpg and Radio1_205CMB2249_codeplug.cpg):

  * tag 0x0FFF  = per-zone channel-name table. ONE INSTANCE PER ZONE (the
        stream's instance index is the zone index); on the Kent PD codeplug
        there are 10 instances, each a 16-slot table (VC KNT..., KC CALL...).
        payload = 00 00 00 00 | count(u16_be) | count * NAME_SLOT bytes
        each NAME_SLOT is a null-padded ASCII channel label (empty = unused).
  * tag 0x0FFD  = conventional personality (freq + NAC) table. A zone's
        channels span one OR MORE consecutive instances: on 407CHT0214 each
        16-channel zone is stored as a count-10 table immediately followed by
        a count-6 table. Records are overlaid positionally (slot index -> name
        slot) onto each zone, starting at the instance named by that zone's
        0x0FFC reference (ref_inst) and walking consecutive instances until the
        zone's channels are covered.
        payload = 00 00 00 00 | count(u16_be) | count * FREQ_REC bytes
        each FREQ_REC (35 bytes):
            owner(u16) link(u16) field(u16)
            nac_rx(u16) nac_tx(u16) nac3(u16)
            freq_rx(u32) freq_tx(u32) freq3(u32)
            options(3 bytes squelch/PL-DPL code) flags(u8) ... tail
        frequency = u32_be * 5 Hz  (docs/CPG_FILE_FORMAT.md). Full extraction
        verified against 407CHT0214: the NIFOG VTAC/VFIRE/VMED/VLAW/VCALL and
        MARINE 16 channels decode to their published national frequencies.

  * squelch / tones: rec[24] = RX squelch byte, rec[26] = TX squelch byte,
        rec[27] bit 0x80 = simplex/direct. Each squelch byte: 0 = carrier
        squelch (CSQ); 1..42 = CTCSS index into the standard EIA tone table
        (VALIDATED: 0x1a == 156.7 Hz, the NIFOG national interop PL on every
        V* channel of 407CHT0214); >42 (high bit set) = DPL, low 7 bits index
        the Motorola DPL list (octal mapping UNVERIFIED -- no ground-truth DPL
        channel was available). rec[25] is a squelch-mode byte, not yet
        resolved. See CTCSS_EIA / DPL_CODES / _decode_squelch.

  * modulation is NOT a decoded flag. A CTCSS or DPL tone proves the channel
        is analog FM; CSQ is ambiguous (analog carrier squelch OR a P25 channel
        squelching on NAC), so voice_type is "Analog" when a tone is present
        and "Unknown" for CSQ -- never a fabricated "digital". (An earlier
        "zero squelch => digital" guess was wrong: zero is carrier squelch.)

Everything the mapping does not yet cover (trunked talkgroups, scan lists, key
material) is left at model defaults; use `open-astro read-cpg` for the full
structural dump of those streams.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import re

from ..models import RadioCodeplug, Zone, Channel, Talkgroup, ScanList
from .cpg_parser import CpgParser, rc4, derive_rc4_key

TAG_CHANNEL_NAMES = 0x0FFF
TAG_CHANNEL_FREQS = 0x0FFD
TAG_PERSONALITY_REC = 0x0FFB # conventional personality record tag (in 0x0FFD tables)
TAG_TALKGROUPS = 0x0FF8   # ISH name list, entries like "TG 00002"
TAG_SITES = 0x0FDC        # ISH name list, trunking system/site aliases
TAG_SCAN_LISTS = (0x004C, 0x004D, 0x004F, 0x006C, 0x006E)  # "LIST N" tables
TAG_CHANNEL_REF = 0x0FFC   # conventional channel -> personality reference record

# A 0x0FFC record is: 0001 0023 00ff 000a <ref_tag:u16> <ref_inst:u16> 00 00 01
# where ref_tag is the referenced personality tag (0x0FFD freq) and ref_inst is
# its instance. Channels appear in instance order; ref_inst steps by 2.
CHREF_TAG_OFF = 8
CHREF_INST_OFF = 10

# ISH name-list header (distinct from the 0x0FFF channel-name header):
#   [0:2] reserved | [2:4] slot stride (u16) | [4:6] subtype | [6:8] count (u16)
#   then count * stride name slots (null-padded ASCII).
ISH_LIST_PREFIX = 8

NAME_TABLE_PREFIX = 6   # 4 reserved bytes + 2-byte count
FREQ_REC_LEN = 35

# Offsets inside a 35-byte FREQ_REC (big-endian):
OFF_NAC_RX = 6
OFF_NAC_TX = 8
OFF_FREQ_RX = 12
OFF_FREQ_TX = 16
# Per-channel option field. Confirmed against 407CHT0214 (VHF), 205CFR2930
# (800 P25) and Radio1 (700/800): rec[24:27] is a squelch/PL-DPL code and
# rec[27] bit 0x80 flags simplex/direct (rx==tx). The three P25 channels we
# can ground-truth (205CFR2930 800 MHz) carry 00 00 00 here, while analog VHF
# interop channels (NIFOG VTAC/MARINE on 407CHT0214) carry nonzero codes.
OFF_OPTIONS = 24
SIMPLEX_BIT = 0x80  # set in rec[27] when rx==tx (direct/talkaround)


def _freq_mhz(raw32: int) -> float:
    """ASTRO frequency word -> MHz (integer * 5 Hz)."""
    return round(raw32 * 5 / 1_000_000, 5)


# XTS 2500 bandsplits. The band is encoded as the model-number letter at index 3
# (right after the "H46" family prefix), confirmed against the RadioReference
# Motorola model-number table and the Motorola XTS 2500 spec sheet:
#   K=VHF  Q=UHF R1  S=UHF R2  U=700/800  W=900
# Each entry: (CPS-style label, low MHz, high MHz).
BANDS: List[Tuple[str, float, float]] = [
    ("VHF (136-174 MHz)", 136.0, 174.0),
    ("UHF Range 1 (380-470 MHz)", 380.0, 470.0),
    ("UHF Range 2 (450-520 MHz)", 450.0, 520.0),
    ("700/800 MHz (764-870 MHz)", 764.0, 870.0),
    ("900 MHz (896-941 MHz)", 896.0, 941.0),
]
BAND_BY_MODEL_LETTER: Dict[str, Tuple[str, float, float]] = {
    "K": BANDS[0],
    "Q": BANDS[1],
    "S": BANDS[2],
    "U": BANDS[3],
    "W": BANDS[4],
}


def _is_band(mhz: float) -> bool:
    # Sanity gate so a zeroed/placeholder record is not read as a 0 MHz channel.
    return 25.0 <= mhz <= 1000.0


def _band_from_model(model: str) -> Optional[Tuple[str, float, float]]:
    """Map an XTS 2500 model number to its bandsplit via the index-3 letter."""
    if model and len(model) >= 4 and model[:3].upper() == "H46":
        return BAND_BY_MODEL_LETTER.get(model[3].upper())
    return None


def _band_from_freqs(freqs: List[float]) -> Optional[Tuple[str, float, float]]:
    """Fallback: pick the bandsplit whose range holds the most decoded freqs.

    Ranges overlap (UHF R1/R2 share 450-470), so this is a best-effort hint
    used only when the model number does not resolve a band."""
    if not freqs:
        return None
    best, best_hits = None, 0
    for band in BANDS:
        _label, lo, hi = band
        hits = sum(1 for f in freqs if lo <= f <= hi)
        if hits > best_hits:
            best, best_hits = band, hits
    return best


def _resolve_bandsplit(model: str, freqs: List[float]) -> str:
    """Bandsplit label: model letter first (authoritative), freqs as fallback."""
    band = _band_from_model(model) or _band_from_freqs(freqs)
    return band[0] if band else "Unknown"


def _nac(raw16: int) -> str:
    """P25 Network Access Code as the CPS "$NNN" hex notation."""
    return f"${raw16:03X}"


# Standard 42-tone EIA/TIA CTCSS table, in the order Motorola indexes it
# (1-based: index 1 = 67.0 Hz). The per-channel squelch byte stores this index.
# VALIDATED against 407CHT0214: every NIFOG national interop channel stores
# 0x1a (26) == 156.7 Hz, the correct national PL.
CTCSS_EIA = [
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 162.2, 167.9, 173.8, 179.9,
    186.2, 192.8, 203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8,
    250.3, 254.1,
]

# Standard Motorola DPL (Digital Private Line) code list, octal, in index order.
# NOTE: UNVERIFIED for the byte->code mapping -- no ground-truth DPL channel was
# available in the sample codeplugs (all validated channels are CTCSS or CSQ).
# The squelch byte for DPL has its high bit set; we index this list by the low
# 7 bits. Treat the resulting octal code as best-effort until confirmed in CPS.
DPL_CODES = [
    23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74,
    114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155, 156, 162,
    165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246, 251, 252,
    255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325, 331, 332, 343,
    346, 351, 356, 364, 365, 371, 411, 412, 413, 423, 431, 432, 445, 446,
    452, 454, 455, 462, 464, 465, 466, 503, 506, 516, 523, 526, 532, 546,
    565, 606, 612, 624, 627, 631, 632, 654, 662, 664, 703, 712, 723, 731,
    732, 734, 743, 754,
]

CTCSS_MAX_INDEX = len(CTCSS_EIA)  # bytes 1..42 are CTCSS; 0 = CSQ; >42 = DPL


def _decode_squelch(byte: int) -> Dict[str, Any]:
    """Decode one per-channel squelch byte into {kind, pl_tone, dpl_code}.

    kind is 'CSQ' (carrier squelch, no tone), 'CTCSS' (analog tone, pl_tone in
    Hz) or 'DPL' (digital PL, dpl_code octal -- UNVERIFIED mapping). A CTCSS or
    DPL value proves the channel is analog; CSQ is ambiguous (analog carrier
    squelch OR a P25 channel that squelches on NAC)."""
    if byte == 0:
        return {"kind": "CSQ", "pl_tone": None, "dpl_code": None}
    if 1 <= byte <= CTCSS_MAX_INDEX:
        return {"kind": "CTCSS", "pl_tone": CTCSS_EIA[byte - 1], "dpl_code": None}
    idx = byte & 0x7F
    code = DPL_CODES[idx] if idx < len(DPL_CODES) else None
    return {"kind": "DPL", "pl_tone": None, "dpl_code": code}


# ---------------------------------------------------------------------------
# Field-Level Schema & Record Decoders (schema/field_layouts.json)
# ---------------------------------------------------------------------------

_FIELD_LAYOUTS_CACHE: Optional[Dict[str, Any]] = None


def get_default_schema_path() -> Path:
    """Find the field_layouts.json schema file."""
    env_path = os.environ.get("OPEN_ASTRO_SCHEMA_PATH")
    if env_path and os.path.exists(env_path):
        return Path(env_path)
    repo_schema = Path(__file__).resolve().parents[3] / "schema" / "field_layouts.json"
    if repo_schema.exists():
        return repo_schema
    cwd_schema = Path.cwd() / "schema" / "field_layouts.json"
    if cwd_schema.exists():
        return cwd_schema
    return repo_schema


def validate_field_layouts(schema: Dict[str, Any]) -> bool:
    """Validate structure and integrity of field layouts schema."""
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary")

    if "0x0FFB" not in schema:
        raise ValueError("Schema missing mandatory '0x0FFB' record definition")

    rec_layout = schema["0x0FFB"]
    rec_len = rec_layout.get("_record_len")
    if rec_len != FREQ_REC_LEN:
        raise ValueError(f"0x0FFB _record_len must be {FREQ_REC_LEN}, got {rec_len}")

    fields = rec_layout.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("0x0FFB must define non-empty 'fields' list")

    expected_offset = 0
    for f in fields:
        name = f.get("name")
        off = f.get("offset")
        flen = f.get("length")
        ftype = f.get("type")
        if not name or off is None or flen is None or not ftype:
            raise ValueError(f"Field definition missing required attributes: {f}")
        if off != expected_offset:
            raise ValueError(f"Field '{name}' offset mismatch: expected {expected_offset}, got {off}")
        expected_offset += flen

    if expected_offset != rec_len:
        raise ValueError(f"Sum of field lengths {expected_offset} != _record_len {rec_len}")

    if "0x0FFD" in schema:
        tbl_layout = schema["0x0FFD"]
        tbl_fields = tbl_layout.get("fields")
        if not isinstance(tbl_fields, list):
            raise ValueError("0x0FFD fields must be a list")

    return True


def load_field_layouts(path: Optional[Union[str, Path]] = None,
                       reload: bool = False,
                       validate: bool = True) -> Dict[str, Any]:
    """Load field-level decoding schema (schema/field_layouts.json)."""
    global _FIELD_LAYOUTS_CACHE
    if not reload and path is None and _FIELD_LAYOUTS_CACHE is not None:
        return _FIELD_LAYOUTS_CACHE

    schema_file = Path(path) if path is not None else get_default_schema_path()
    if not schema_file.exists():
        raise FileNotFoundError(f"Field layouts schema not found at: {schema_file}")

    data = json.loads(schema_file.read_text(encoding="utf-8"))
    if validate:
        validate_field_layouts(data)

    if path is None:
        _FIELD_LAYOUTS_CACHE = data
    return data


def normalize_tag(tag: Union[int, str]) -> str:
    """Normalize integer or string tag to '0xXXXX' format."""
    if isinstance(tag, int):
        return f"0x{tag:04X}"
    tag_str = str(tag).strip()
    if tag_str.startswith(("0x", "0X")):
        return f"0x{int(tag_str, 16):04X}"
    return f"0x{int(tag_str, 16):04X}"


def get_schema_layout(tag: Union[int, str] = "0x0FFB",
                      schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get field layout dictionary for a specific tag."""
    tag_key = normalize_tag(tag)
    if schema is None:
        schema = load_field_layouts()
    if tag_key not in schema:
        raise KeyError(f"Tag {tag_key} not defined in field layouts schema")
    return schema[tag_key]


class SquelchValue(int):
    """Per-channel squelch byte (0=CSQ, 1..42=CTCSS index, >42=DPL).

    Inherits from int so integer comparisons work directly (e.g. sq == 0x1A or sq == 0),
    while exposing decoded squelch properties.
    """
    _decoded: Dict[str, Any]

    def __new__(cls, val: int):
        obj = super().__new__(cls, val & 0xFF)
        obj._decoded = _decode_squelch(val & 0xFF)
        return obj

    @property
    def kind(self) -> str:
        return self._decoded["kind"]

    @property
    def pl_tone(self) -> Optional[float]:
        return self._decoded["pl_tone"]

    @property
    def dpl_code(self) -> Optional[int]:
        return self._decoded["dpl_code"]

    def to_dict(self) -> Dict[str, Any]:
        return {"raw": int(self), **self._decoded}

    def __repr__(self) -> str:
        if self.kind == "CTCSS":
            return f"SquelchValue(0x{int(self):02X}, CTCSS {self.pl_tone} Hz)"
        elif self.kind == "DPL":
            return f"SquelchValue(0x{int(self):02X}, DPL {self.dpl_code})"
        return f"SquelchValue(0x{int(self):02X}, CSQ)"


class NacValue(str):
    """P25 Network Access Code formatted as '$NNN' with .raw integer access."""
    raw: int

    def __new__(cls, raw: int):
        s = _nac(raw & 0xFFFF)
        obj = super().__new__(cls, s)
        obj.raw = raw & 0xFFFF
        return obj

    def __repr__(self) -> str:
        return f"NacValue('{self}', raw=0x{self.raw:03X})"


class PersonalityRecord(dict):
    """Decoded 35-byte 0x0FFB conventional personality record.

    Provides both dictionary item access (rec['freq_rx'], rec['rx_frequency'])
    and attribute access (rec.freq_rx, rec.rx_frequency, rec.simplex).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._populate_convenience_fields()

    def _populate_convenience_fields(self) -> None:
        flags = self.get("flags", 0)
        freq_rx = self.get("freq_rx", 0.0)
        freq_tx = self.get("freq_tx", 0.0)

        # Fallback for tx when not in band
        if not _is_band(freq_tx) and _is_band(freq_rx):
            freq_tx = freq_rx
            self["freq_tx"] = freq_rx

        # Simplex flag
        if "simplex" not in self:
            if flags & SIMPLEX_BIT:
                self["simplex"] = True
            elif flags == 0 and abs(freq_rx - freq_tx) < 1e-6 and freq_rx > 0:
                self["simplex"] = True
            else:
                self["simplex"] = False

        # Channel model aliases for backwards compatibility
        if "rx_frequency" not in self:
            self["rx_frequency"] = freq_rx
        if "tx_frequency" not in self:
            self["tx_frequency"] = freq_tx
        if "rx_nac" not in self and "nac_rx" in self:
            self["rx_nac"] = str(self["nac_rx"])
        if "tx_nac" not in self and "nac_tx" in self:
            self["tx_nac"] = str(self["nac_tx"])

        sq_rx = self.get("squelch_rx")
        sq_tx = self.get("squelch_tx")
        if "rx_pl_tone" not in self:
            self["rx_pl_tone"] = sq_rx.pl_tone if isinstance(sq_rx, SquelchValue) else None
        if "tx_pl_tone" not in self:
            self["tx_pl_tone"] = sq_tx.pl_tone if isinstance(sq_tx, SquelchValue) else None
        if "rx_dpl_code" not in self:
            self["rx_dpl_code"] = sq_rx.dpl_code if isinstance(sq_rx, SquelchValue) else None
        if "tx_dpl_code" not in self:
            self["tx_dpl_code"] = sq_tx.dpl_code if isinstance(sq_tx, SquelchValue) else None

        if "voice_type" not in self:
            rx_kind = sq_rx.kind if isinstance(sq_rx, SquelchValue) else "CSQ"
            tx_kind = sq_tx.kind if isinstance(sq_tx, SquelchValue) else "CSQ"
            has_tone = rx_kind != "CSQ" or tx_kind != "CSQ"
            self["voice_type"] = "Analog" if has_tone else "Unknown"

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'PersonalityRecord' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self[name] = value

    def to_dict(self, hex_bytes: bool = False) -> Dict[str, Any]:
        """Convert to standard dictionary, optionally converting bytes to hex strings."""
        out: Dict[str, Any] = {}
        for k, v in self.items():
            if isinstance(v, bytes):
                out[k] = v.hex() if hex_bytes else v
            elif isinstance(v, SquelchValue):
                out[k] = v.to_dict() if hex_bytes else int(v)
            elif isinstance(v, NacValue):
                out[k] = str(v)
            else:
                out[k] = v
        return out

    def as_dict(self, hex_bytes: bool = False) -> Dict[str, Any]:
        return self.to_dict(hex_bytes=hex_bytes)


def decode_record_with_schema(record_bytes: bytes,
                              tag: Union[int, str] = "0x0FFB",
                              strict: bool = False,
                              schema: Optional[Dict[str, Any]] = None) -> Optional[PersonalityRecord]:
    """Decode a record buffer using the field definitions from field_layouts.json.

    Args:
        record_bytes: The raw byte buffer for the record.
        tag: Schema tag identifying the layout (default: 0x0FFB).
        strict: When True, raises ValueError on length/tag mismatches; when False, returns None.
        schema: Optional pre-loaded schema dictionary.
    """
    tag_key = normalize_tag(tag)
    try:
        layout = get_schema_layout(tag_key, schema=schema)
    except KeyError:
        if strict:
            raise
        return None

    expected_len = layout.get("_record_len", FREQ_REC_LEN)
    if len(record_bytes) < expected_len:
        if strict:
            raise ValueError(f"Buffer length {len(record_bytes)} < expected record length {expected_len}")
        return None

    if tag_key == "0x0FFB":
        rec_tag = int.from_bytes(record_bytes[0:2], "big")
        rec_term = record_bytes[34]
        if strict:
            if rec_tag != 0x0FFB:
                raise ValueError(f"Record tag mismatch: expected 0x0FFB, got 0x{rec_tag:04X}")
            if rec_term != 0x01:
                raise ValueError(f"Record terminator mismatch: expected 0x01, got 0x{rec_term:02X}")

    field_values: Dict[str, Any] = {}
    for f in layout.get("fields", []):
        name = f["name"]
        off = f["offset"]
        flen = f["length"]
        ftype = f["type"]
        raw = record_bytes[off:off + flen]

        if ftype == "u16be":
            val = int.from_bytes(raw, "big")
        elif ftype == "u8":
            val = raw[0]
        elif ftype == "u32be":
            val = int.from_bytes(raw, "big")
        elif ftype == "bytes":
            val = bytes(raw)
        elif ftype == "nac":
            val = NacValue(int.from_bytes(raw, "big"))
        elif ftype == "freq_x5hz":
            val = _freq_mhz(int.from_bytes(raw, "big"))
        elif ftype == "squelch":
            val = SquelchValue(raw[0])
        else:
            val = bytes(raw)
        field_values[name] = val

    if tag_key == "0x0FFB":
        return PersonalityRecord(field_values)
    return field_values  # type: ignore[return-value]


def decode_table_with_schema(payload: bytes,
                             tag: Union[int, str] = "0x0FFD",
                             strict: bool = False,
                             schema: Optional[Dict[str, Any]] = None) -> List[PersonalityRecord]:
    """Decode a container table payload (tag 0x0FFD) into a list of PersonalityRecords."""
    tag_key = normalize_tag(tag)
    if tag_key != "0x0FFD":
        if strict:
            raise ValueError(f"decode_table_with_schema currently supports container 0x0FFD, got {tag_key}")
        return []

    if len(payload) < NAME_TABLE_PREFIX:
        if strict:
            raise ValueError(f"Payload length {len(payload)} < table header prefix {NAME_TABLE_PREFIX}")
        return []

    count = int.from_bytes(payload[4:6], "big")
    body = payload[NAME_TABLE_PREFIX:]
    if count <= 0 or len(body) < count * FREQ_REC_LEN:
        if strict and count > 0:
            raise ValueError(f"Payload body length {len(body)} < expected {count * FREQ_REC_LEN}")
        return []

    records: List[PersonalityRecord] = []
    for i in range(count):
        chunk = body[i * FREQ_REC_LEN:(i + 1) * FREQ_REC_LEN]
        rec = decode_record_with_schema(chunk, tag="0x0FFB", strict=strict, schema=schema)
        if rec is not None:
            records.append(rec)
    return records


class CpgDecoder:
    """Decode a .cpg into a typed RadioCodeplug (conventional channels)."""

    def __init__(self, path: str):
        self._parser = CpgParser(path)   # validates OLE + imports olefile
        self._ole = self._parser._ole
        self._key = derive_rc4_key()
        self._header: Dict[str, Any] = {}

    # -- low level -------------------------------------------------------
    def _decoded_streams(self) -> List[Tuple[int, int, bytes]]:
        """Yield (tag, instance, payload) for every decrypted data stream."""
        out: List[Tuple[int, int, bytes]] = []
        for p in self._parser._streams():
            raw = self._parser._read(p)
            if p and p[-1] == "AdkFileHeader":
                self._header = self._parse_header(raw)
                continue
            if len(raw) < 8:
                continue
            dec = rc4(self._key, raw)
            tag = int.from_bytes(dec[:2], "big")
            inst = int.from_bytes(dec[2:4], "big")
            payload = dec[6:-2]
            out.append((tag, inst, payload))
        return out

    @staticmethod
    def _parse_header(blob: bytes) -> Dict[str, Any]:
        from .cpg_parser import parse_header
        return parse_header(blob)

    # -- record tables ---------------------------------------------------
    @staticmethod
    def _name_table(payload: bytes) -> List[str]:
        if len(payload) < NAME_TABLE_PREFIX:
            return []
        count = int.from_bytes(payload[4:6], "big")
        body = payload[NAME_TABLE_PREFIX:]
        if count <= 0:
            return []
        slot = len(body) // count
        if slot <= 0:
            return []
        names: List[str] = []
        for i in range(count):
            rec = body[i * slot:(i + 1) * slot]
            # Keep only printable ASCII. Trunked-zone slots (0x0FFF instance > 0)
            # carry a leading status byte before the label; dropping non-printable
            # bytes yields a clean label without guessing that field's meaning.
            text = "".join(chr(b) for b in rec.split(b"\x00", 1)[0] if 0x20 <= b < 0x7F)
            names.append(text.strip())
        return names

    @staticmethod
    def _freq_records(payload: bytes) -> List[bytes]:
        if len(payload) < NAME_TABLE_PREFIX:
            return []
        count = int.from_bytes(payload[4:6], "big")
        body = payload[NAME_TABLE_PREFIX:]
        if count <= 0 or len(body) < count * FREQ_REC_LEN:
            return []
        return [body[i * FREQ_REC_LEN:(i + 1) * FREQ_REC_LEN] for i in range(count)]

    @staticmethod
    def _channel_ref(payload: bytes) -> Optional[Dict[str, int]]:
        """Decode a 0x0FFC channel->personality reference record."""
        if len(payload) < CHREF_INST_OFF + 2:
            return None
        return {
            "ref_tag": int.from_bytes(payload[CHREF_TAG_OFF:CHREF_TAG_OFF + 2], "big"),
            "ref_inst": int.from_bytes(payload[CHREF_INST_OFF:CHREF_INST_OFF + 2], "big"),
        }

    @staticmethod
    def _ish_name_list(payload: bytes) -> List[str]:
        """Decode an ISH name-list table (tags 0x0FF8 / 0x0FDC / LIST tags)."""
        if len(payload) < ISH_LIST_PREFIX:
            return []
        stride = int.from_bytes(payload[2:4], "big")
        count = int.from_bytes(payload[6:8], "big")
        body = payload[ISH_LIST_PREFIX:]
        if stride <= 0 or count <= 0 or len(body) < count * stride:
            return []
        names: List[str] = []
        for i in range(count):
            rec = body[i * stride:(i + 1) * stride]
            text = "".join(chr(b) for b in rec.split(b"\x00", 1)[0] if 0x20 <= b < 0x7F)
            text = text.strip()
            if text:
                names.append(text)
        return names

    @classmethod
    def _decode_freq_rec(cls, rec: bytes) -> Optional[PersonalityRecord]:
        if len(rec) < FREQ_REC_LEN:
            return None
        tag = int.from_bytes(rec[:2], "big")
        # Real conventional records carry 0x0FFB; synthetic tests may carry 0x0000.
        if tag not in (TAG_PERSONALITY_REC, 0):
            return None
        decoded = decode_record_with_schema(rec, tag=TAG_PERSONALITY_REC, strict=False)
        if decoded is None:
            return None
        if not _is_band(decoded.freq_rx):
            return None
        return decoded

    PersonalityRecord = PersonalityRecord
    decode_record_with_schema = staticmethod(decode_record_with_schema)
    decode_table_with_schema = staticmethod(decode_table_with_schema)
    load_field_layouts = staticmethod(load_field_layouts)

    # -- public ----------------------------------------------------------
    def decode(self) -> RadioCodeplug:
        streams = self._decoded_streams()
        model = self._header.get("model") or "Motorola XTS 2500"
        serial = self._header.get("serial") or "UNKNOWN"
        return self.build_from_streams(streams, model, serial)

    @classmethod
    def build_from_streams(cls, streams: List[Tuple[int, int, bytes]],
                           model: str = "Motorola XTS 2500",
                           serial: str = "UNKNOWN") -> RadioCodeplug:
        """Build a RadioCodeplug from decoded (tag, instance, payload) records.

        Shared by the offline .cpg path (decode) and the live RCMP path, where
        each RCMP object id == stream tag and read_object() returns the same
        payload the OLE reader yields. Verified: live 0x0fff payload is
        byte-identical to the backup's decrypted 0x0fff stream."""
        # One zone per 0x0FFF instance (instance index == zone index). Keep
        # instance order; drop exact-duplicate tables (some codeplugs store a
        # mirror copy under a second instance).
        zone_tables: List[List[str]] = []
        for _inst, payload in sorted(
            ((i, pl) for tag, i, pl in streams if tag == TAG_CHANNEL_NAMES)
        ):
            names = cls._name_table(payload)
            if any(n for n in names) and names not in zone_tables:
                zone_tables.append(names)

        # Conventional freq/NAC personality records, decoded per 0x0FFD
        # instance. A zone's channels span one or more consecutive instances
        # (e.g. 407CHT0214 stores each 16-channel zone as a count-10 table
        # followed by a count-6 table), so keep them keyed by instance and
        # concatenate per zone below.
        freq_tables: Dict[int, List[Dict[str, Any]]] = {}
        for tag, inst, payload in streams:
            if tag != TAG_CHANNEL_FREQS:
                continue
            freq_tables[inst] = [d for d in (cls._decode_freq_rec(r)
                                             for r in cls._freq_records(payload)) if d]

        # Conventional channel->personality references (0x0FFC), in zone order.
        # Each record's ref_inst is the FIRST 0x0FFD instance for that zone.
        zone_refs = [cls._channel_ref(pl) for _t, _i, pl in
                     sorted(((t, i, pl) for t, i, pl in streams
                             if t == TAG_CHANNEL_REF), key=lambda x: x[1])]
        zone_start_inst = [r["ref_inst"] for r in zone_refs if r]

        def _zone_records(zi: int, needed: int) -> List[Dict[str, Any]]:
            """Freq records for zone zi: start at its 0x0FFC-referenced instance
            and walk consecutive instances until `needed` channels are covered.
            Falls back to instance == zi when no reference records exist."""
            start = zone_start_inst[zi] if zi < len(zone_start_inst) else zi
            out: List[Dict[str, Any]] = []
            inst = start
            while len(out) < needed and inst in freq_tables:
                out.extend(freq_tables[inst])
                inst += 1
            return out

        zones: List[Zone] = []
        for zi, names in enumerate(zone_tables):
            recs = _zone_records(zi, len(names))  # positional: slot index -> record
            channels: List[Channel] = []
            cn = 0
            for si, raw_name in enumerate(names):
                name = raw_name.strip()
                if not name:
                    continue
                cn += 1
                rec = recs[si] if si < len(recs) else None
                channels.append(Channel(
                    channel_number=cn,
                    name=name[:14],
                    rx_frequency=rec["rx_frequency"] if rec else 0.0,
                    tx_frequency=rec["tx_frequency"] if rec else 0.0,
                    voice_type=rec["voice_type"] if rec else "Unknown",
                    rx_pl_tone=rec["rx_pl_tone"] if rec else None,
                    tx_pl_tone=rec["tx_pl_tone"] if rec else None,
                    rx_dpl_code=rec["rx_dpl_code"] if rec else None,
                    tx_dpl_code=rec["tx_dpl_code"] if rec else None,
                    rx_nac=rec["rx_nac"] if rec else "$293",
                    tx_nac=rec["tx_nac"] if rec else "$293",
                ))
            if channels:
                zones.append(Zone(zone_number=zi + 1, name=f"ZONE {zi + 1}", channels=channels))

        # Talkgroups (0x0FF8), sites (0x0FDC), scan lists (LIST tags).
        talkgroups: List[Talkgroup] = []
        sites: List[str] = []
        scan_lists: List[ScanList] = []
        seen_scan: set = set()
        for tag, _inst, payload in streams:
            if tag == TAG_TALKGROUPS:
                for n in cls._ish_name_list(payload):
                    m = re.search(r"(\d+)", n)
                    talkgroups.append(Talkgroup(tg_id=int(m.group(1)) if m else None, name=n))
            elif tag == TAG_SITES:
                sites.extend(cls._ish_name_list(payload))
            elif tag in TAG_SCAN_LISTS:
                for n in cls._ish_name_list(payload):
                    if n not in seen_scan:
                        seen_scan.add(n)
                        scan_lists.append(ScanList(name=n))

        decoded_freqs = [c.rx_frequency for z in zones for c in z.channels
                         if c.rx_frequency and _is_band(c.rx_frequency)]
        return RadioCodeplug(
            radio_model=model,
            bandsplit=_resolve_bandsplit(model, decoded_freqs),
            serial_number=serial,
            flashcode="",
            zones=zones,
            talkgroups=talkgroups,
            sites=sites,
            scan_lists=scan_lists,
        )

    # -- conventional personalities (ALL 0x0FFD instances) ---------------
    @classmethod
    def personality_records_from_streams(
        cls,
        streams: List[Tuple[int, int, bytes]],
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[PersonalityRecord]:
        """Every 0x0FFB conventional personality record across ALL 0x0FFD instances.

        This returns the full set of UNIQUE conventional personalities, a
        different view from the zone-walking channel decoder in decode() (which
        yields per-zone channel instances and may repeat a personality across
        zones). The personalities are spread across many 0x0FFD instances. On a
        fully flashed fleet codeplug (backups/Radio1_205CMB2249_codeplug.cpg,
        partition 0x80) they span 19 instances of (0x80, 0x0FFD, *): even
        instances carry up to a 10-record table, odd instances a 6-record table,
        and the last instance is short -- 43 0x0FFB records in all. The 800 MHz
        ADP SECURE personality (851.5125 MHz) lives in insts 4/14.

        This walks every (0x0FFD) instance in stream order, slices each 35-byte
        record, and keeps only records that self-tag as 0x0FFB -- any slot whose
        first u16 != 0x0FFB is skipped. Records are returned in (instance, slot)
        order. NO de-duplication is applied: the odd/even tables are distinct
        physical personalities (43 unique slots: 3+6+10+6+10+6+2), not mirror
        copies of one table, so all 43 are returned. The per-record decode is the
        same schema-driven PersonalityRecord path used everywhere else, so field
        offsets stay governed by schema/field_layouts.json.
        """
        records: List[PersonalityRecord] = []
        for tag, _inst, payload in streams:
            if tag != TAG_CHANNEL_FREQS:
                continue
            for raw in cls._freq_records(payload):
                if int.from_bytes(raw[:2], "big") != TAG_PERSONALITY_REC:
                    continue  # skip non-0x0FFB slots (padding / foreign records)
                rec = decode_record_with_schema(
                    raw, tag=TAG_PERSONALITY_REC, strict=False, schema=schema
                )
                if rec is not None:
                    records.append(rec)
        return records

    def personality_records(
        self, schema: Optional[Dict[str, Any]] = None
    ) -> List[PersonalityRecord]:
        """All 0x0FFB personality records decoded from this .cpg (every 0x0FFD instance)."""
        return self.personality_records_from_streams(self._decoded_streams(), schema=schema)

    def close(self) -> None:
        self._parser.close()

    def __enter__(self) -> "CpgDecoder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
