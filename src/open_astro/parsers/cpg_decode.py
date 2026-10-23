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
  * tag 0x0FFD  = conventional personality (freq + NAC) table, overlaid
        positionally onto the first zone's channels. The real data lives in
        the instance whose records carry non-zero frequencies.
        payload = 00 00 00 00 | count(u16_be) | count * FREQ_REC bytes
        each FREQ_REC (35 bytes):
            owner(u16) link(u16) field(u16)
            nac_rx(u16) nac_tx(u16) nac3(u16)
            freq_rx(u32) freq_tx(u32) freq3(u32)
            flags(u32) ... tail
        frequency = u32_be * 5 Hz  (docs/CPG_FILE_FORMAT.md).

Everything the mapping does not yet cover (trunked talkgroups, scan lists, key
material) is left at model defaults; use `open-astro read-cpg` for the full
structural dump of those streams.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import re

from ..models import RadioCodeplug, Zone, Channel, Talkgroup, ScanList
from .cpg_parser import CpgParser, rc4, derive_rc4_key

TAG_CHANNEL_NAMES = 0x0FFF
TAG_CHANNEL_FREQS = 0x0FFD
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


def _freq_mhz(raw32: int) -> float:
    """ASTRO frequency word -> MHz (integer * 5 Hz)."""
    return round(raw32 * 5 / 1_000_000, 5)


def _is_band(mhz: float) -> bool:
    # Sanity gate so a zeroed/placeholder record is not read as a 0 MHz channel.
    return 25.0 <= mhz <= 1000.0


def _nac(raw16: int) -> str:
    """P25 Network Access Code as the CPS "$NNN" hex notation."""
    return f"${raw16:03X}"


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

    @staticmethod
    def _decode_freq_rec(rec: bytes) -> Optional[Dict[str, Any]]:
        if len(rec) < OFF_FREQ_TX + 4:
            return None
        rx = _freq_mhz(int.from_bytes(rec[OFF_FREQ_RX:OFF_FREQ_RX + 4], "big"))
        tx = _freq_mhz(int.from_bytes(rec[OFF_FREQ_TX:OFF_FREQ_TX + 4], "big"))
        if not _is_band(rx):
            return None
        if not _is_band(tx):
            tx = rx
        return {
            "rx_frequency": rx,
            "tx_frequency": tx,
            "rx_nac": _nac(int.from_bytes(rec[OFF_NAC_RX:OFF_NAC_RX + 2], "big")),
            "tx_nac": _nac(int.from_bytes(rec[OFF_NAC_TX:OFF_NAC_TX + 2], "big")),
        }

    # -- public ----------------------------------------------------------
    def decode(self) -> RadioCodeplug:
        streams = self._decoded_streams()

        # One zone per 0x0FFF instance (instance index == zone index). Keep
        # instance order; drop exact-duplicate tables (some codeplugs store a
        # mirror copy under a second instance).
        zone_tables: List[List[str]] = []
        for _inst, payload in sorted(
            ((i, pl) for tag, i, pl in streams if tag == TAG_CHANNEL_NAMES)
        ):
            names = self._name_table(payload)
            if any(n for n in names) and names not in zone_tables:
                zone_tables.append(names)

        # Conventional freq/NAC records, overlaid positionally onto zone 0.
        conv_recs: List[Dict[str, Any]] = []
        for tag, _inst, payload in streams:
            if tag != TAG_CHANNEL_FREQS:
                continue
            decoded = [d for d in (self._decode_freq_rec(r)
                                   for r in self._freq_records(payload)) if d]
            if len(decoded) > len(conv_recs):
                conv_recs = decoded

        # Conventional channel->personality references (0x0FFC), in channel
        # order. These confirm the conventional-channel count/order; trunked
        # zones have no equivalent per-channel personality record in these
        # samples, so their talkgroup IDs are not resolvable here.
        channel_refs = [self._channel_ref(pl) for tag, _i, pl in
                        sorted(((t, i, pl) for t, i, pl in streams
                                if t == TAG_CHANNEL_REF), key=lambda x: x[1])]
        channel_refs = [r for r in channel_refs if r]

        # Overlay conventional freq/NAC only onto as many zone-0 channels as the
        # 0x0FFC reference records vouch for (falls back to the freq-record count
        # when no reference records are present).
        conv_count = min(len(conv_recs), len(channel_refs)) if channel_refs else len(conv_recs)

        zones: List[Zone] = []
        for zi, names in enumerate(zone_tables):
            channels: List[Channel] = []
            cn = 0
            for si, raw_name in enumerate(names):
                name = raw_name.strip()
                if not name:
                    continue
                cn += 1
                rec = conv_recs[si] if (zi == 0 and si < conv_count) else None
                channels.append(Channel(
                    channel_number=cn,
                    name=name[:14],
                    rx_frequency=rec["rx_frequency"] if rec else 0.0,
                    tx_frequency=rec["tx_frequency"] if rec else 0.0,
                    voice_type="ASTRO P25",
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
                for n in self._ish_name_list(payload):
                    m = re.search(r"(\d+)", n)
                    talkgroups.append(Talkgroup(tg_id=int(m.group(1)) if m else None, name=n))
            elif tag == TAG_SITES:
                sites.extend(self._ish_name_list(payload))
            elif tag in TAG_SCAN_LISTS:
                for n in self._ish_name_list(payload):
                    if n not in seen_scan:
                        seen_scan.add(n)
                        scan_lists.append(ScanList(name=n))

        model = self._header.get("model") or "Motorola XTS 2500"
        serial = self._header.get("serial") or "UNKNOWN"
        return RadioCodeplug(
            radio_model=model,
            bandsplit="700/800 MHz (764-870 MHz)",
            serial_number=serial,
            flashcode="",
            zones=zones,
            talkgroups=talkgroups,
            sites=sites,
            scan_lists=scan_lists,
        )

    def close(self) -> None:
        self._parser.close()

    def __enter__(self) -> "CpgDecoder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
