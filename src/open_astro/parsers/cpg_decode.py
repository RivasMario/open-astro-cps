"""
Typed .cpg -> RadioCodeplug decoder (offline).

Builds on the structural reader in cpg_parser.py. Where cpg_parser dumps every
stream generically (tag / instance / payload / CRC), this module maps the
ISH records into the typed RadioCodeplug / Zone / Channel / Talkgroup / ScanList
models so the result round-trips through JsonParser and CsvParser.

Calibration (from backups/205CFR2930.cpg and Radio1_205CMB2249_codeplug.cpg):

  * tag 0x1004  = radio identity record: serial at payload[2:12] (null-padded
        ASCII), model at payload[13:25] (null-padded ASCII).
  * tag 0x1006  = feature/flashcode record: 13-digit flashcode string at
        payload[8:] (null-terminated ASCII, e.g. "000008-002410-2").
  * tag 0x000D  = ISH name-list table of zone labels (e.g. ["Z1", "Z2"] or
        ["A", "B", "C", "E", "F", "G", "H", "I", "J", "RB"]).
  * tag 0x0FFE  = per-zone descriptor pointing to the zone's channel-name table
        (ref_tag=0x0FFF, ref_inst at payload[10:12]).
  * tag 0x0FFF  = per-zone channel-name table. ONE INSTANCE PER ZONE (the
        stream's instance index is the zone index); on the Kent PD codeplug
        there are 10 instances, each a 16-slot table (VC KNT..., KC CALL...).
        payload = 00 00 00 00 | count(u16_be) | count * NAME_SLOT bytes
        each NAME_SLOT is a null-padded ASCII channel label (empty = unused).
  * tag 0x0FFC  = per-zone channel->personality reference record pointing to the
        zone's first 0x0FFD table instance (ref_tag=0x0FFD, ref_inst at
        payload[10:12], stepping by 2 when a zone spans two 0x0FFD instances).
  * tag 0x0FFD  = per-zone channel record table (up to 10 records per stream;
        payload[0:2]=next_tag, payload[2:4]=next_inst when a 16-channel zone
        chains a 10-record even instance to a 6-record odd instance).
        payload = next_tag(u16_be) | next_inst(u16_be) | count(u16_be) | count * FREQ_REC bytes
        each FREQ_REC (35 bytes):
            owner(u16) link(u16) field(u16)
            nac_rx(u16) nac_tx(u16) nac3(u16)
            freq_rx(u32) freq_tx(u32) freq3(u32)
            flags(u32) ... tail
        - Conventional channels have owner=0x0FFB and non-zero frequencies:
          frequency = u32_be * 5 Hz (docs/CPG_FILE_FORMAT.md).
        - Trunked channels have owner=0x0FE4, link=trunked personality instance,
          and field[0] (rec[4]) = 1-based talkgroup slot index into the
          personality's talkgroup list (tag 0x0FD5 default TG at payload[13:15]
          for slot 1, plus tag 0x0FD4 11-byte records for slots 2..N).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import re

from ..models import RadioCodeplug, Zone, Channel, Talkgroup, ScanList
from .cpg_parser import CpgParser, rc4, derive_rc4_key

TAG_RADIO_ID = 0x1004      # serial + model record
TAG_FLASHCODE = 0x1006     # ASCII flashcode record (e.g. "000008-002410-2")
TAG_ZONE_NAMES = 0x000D    # ISH name-list table of zone aliases
TAG_ZONE_DESC = 0x0FFE     # per-zone descriptor -> 0x0FFF instance
TAG_CHANNEL_NAMES = 0x0FFF
TAG_CHANNEL_FREQS = 0x0FFD
TAG_CHANNEL_REF = 0x0FFC   # per-zone channel -> 0x0FFD chain head pointer
TAG_TRUNK_PERS = 0x0FE4    # trunked personality owner tag in 0x0FFD records
TAG_CONV_PERS = 0x0FFB     # conventional personality owner tag in 0x0FFD records
TAG_TRUNK_TG_HDR = 0x0FD5  # trunked personality talkgroup header (slot 1 default TG + 0x0FD4 pointer)
TAG_TRUNK_TG_TBL = 0x0FD4  # trunked personality talkgroup table (slots 2..N, 11B records)
TAG_TALKGROUPS = 0x0FF8    # ISH name list, entries like "TG 00002"
TAG_SITES = 0x0FDC         # ISH name list, trunking system/site aliases
TAG_SCAN_LISTS = (0x004C, 0x004D, 0x004F, 0x006C, 0x006E)  # "LIST N" tables

# A 0x0FFC record is: 0001 0023 00ff 000a <ref_tag:u16> <ref_inst:u16> 00 00 01
# where ref_tag is the referenced personality tag (0x0FFD freq) and ref_inst is
# its head instance for that zone.
CHREF_TAG_OFF = 8
CHREF_INST_OFF = 10

# ISH name-list header (distinct from the 0x0FFF channel-name header):
#   [0:2] reserved | [2:4] slot stride (u16) | [4:6] subtype | [6:8] count (u16)
#   then count * stride name slots (null-padded ASCII).
ISH_LIST_PREFIX = 8

NAME_TABLE_PREFIX = 6   # 4 header/chain bytes + 2-byte count
FREQ_REC_LEN = 35
TRUNK_TG_REC_LEN = 11

# Offsets inside a 35-byte FREQ_REC (big-endian):
OFF_OWNER_TAG = 0
OFF_OWNER_INST = 2
OFF_TG_SLOT = 4
OFF_NAC_RX = 6
OFF_NAC_TX = 8
OFF_FREQ_RX = 12
OFF_FREQ_TX = 16

BANDSPLIT_BY_PREFIX: Dict[str, str] = {
    "U": "700/800 MHz (764-870 MHz)",
    "K": "VHF (136-174 MHz)",
    "R": "UHF Range 1 (380-470 MHz)",
    "S": "UHF Range 2 (450-520 MHz)",
    "F": "700 MHz (764-806 MHz)",
    "W": "800 MHz (806-870 MHz)",
}


def infer_bandsplit(model: Optional[str]) -> str:
    """Infer radio bandsplit description from Motorola ASTRO 25 model number."""
    if model and len(model) >= 4:
        band_char = model[3].upper()
        if band_char in BANDSPLIT_BY_PREFIX:
            return BANDSPLIT_BY_PREFIX[band_char]
    return "700/800 MHz (764-870 MHz)"


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
    """Decode a .cpg into a typed RadioCodeplug."""

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
            if p and p[-1] == "Strm_0":
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
        """Decode an ISH name-list table (tags 0x000D / 0x0FF8 / 0x0FDC / LIST tags)."""
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
    def _decode_radio_id_stream(payload: bytes) -> Dict[str, Optional[str]]:
        """Decode serial and model number from tag 0x1004 payload."""
        info: Dict[str, Optional[str]] = {"serial": None, "model": None}
        if len(payload) >= 12:
            raw_ser = payload[2:12].split(b"\x00", 1)[0]
            ser = "".join(chr(b) for b in raw_ser if 0x20 <= b < 0x7F).strip()
            if ser:
                info["serial"] = ser
        if len(payload) >= 25:
            raw_mod = payload[13:25].split(b"\x00", 1)[0]
            mod = "".join(chr(b) for b in raw_mod if 0x20 <= b < 0x7F).strip()
            if mod:
                info["model"] = mod
        return info

    @staticmethod
    def _decode_flashcode_stream(payload: bytes) -> Optional[str]:
        """Decode the 13-character flashcode string from tag 0x1006 payload."""
        if len(payload) < 9:
            return None
        raw = payload[8:].split(b"\x00", 1)[0]
        text = "".join(chr(b) for b in raw if 0x20 <= b < 0x7F).strip()
        if re.fullmatch(r"[0-9A-Fa-f]{6}-[0-9A-Fa-f]{6}-\d", text):
            return text.upper()
        return text or None

    @staticmethod
    def _decode_trunk_tg_tables(
        by_tag_inst: Dict[Tuple[int, int], bytes]
    ) -> Dict[int, List[int]]:
        """Build {trunk_pers_inst: [tg_slot_1, tg_slot_2, ...]} from 0x0FD5 + 0x0FD4."""
        tables: Dict[int, List[int]] = {}
        for (tag, inst), pl in sorted(by_tag_inst.items()):
            if tag != TAG_TRUNK_TG_HDR or len(pl) < 15:
                continue
            fd4_tag = int.from_bytes(pl[8:10], "big")
            fd4_inst = int.from_bytes(pl[10:12], "big")
            tg0 = int.from_bytes(pl[13:15], "big")
            tgs: List[int] = [tg0]
            pl4 = by_tag_inst.get((fd4_tag, fd4_inst))
            if pl4 and len(pl4) >= NAME_TABLE_PREFIX:
                cnt4 = int.from_bytes(pl4[4:6], "big")
                body4 = pl4[NAME_TABLE_PREFIX:]
                for i in range(cnt4):
                    rec4 = body4[i * TRUNK_TG_REC_LEN:(i + 1) * TRUNK_TG_REC_LEN]
                    if len(rec4) >= 2:
                        tgs.append(int.from_bytes(rec4[0:2], "big"))
            tables[inst] = tgs
        return tables

    @classmethod
    def _follow_ffd_chain(
        cls,
        head_inst: int,
        by_tag_inst: Dict[Tuple[int, int], bytes],
    ) -> List[bytes]:
        """Follow a 0x0FFD linked-list chain starting at head_inst."""
        recs: List[bytes] = []
        seen: set = set()
        cur_tag = TAG_CHANNEL_FREQS
        cur_inst = head_inst
        while cur_tag == TAG_CHANNEL_FREQS and (cur_tag, cur_inst) in by_tag_inst and cur_inst not in seen:
            seen.add(cur_inst)
            pl = by_tag_inst[(cur_tag, cur_inst)]
            recs.extend(cls._freq_records(pl))
            cur_tag = int.from_bytes(pl[0:2], "big")
            cur_inst = int.from_bytes(pl[2:4], "big")
        return recs

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
        by_tag_inst: Dict[Tuple[int, int], bytes] = {
            (tag, inst): pl for tag, inst, pl in streams
        }

        # Zone names from tag 0x000D (ISH name list), with fallback to "ZONE N".
        raw_zone_names: List[str] = []
        for tag, _inst, payload in sorted(
            ((t, i, pl) for t, i, pl in streams if t == TAG_ZONE_NAMES),
            key=lambda x: x[1],
        ):
            raw_zone_names.extend(self._ish_name_list(payload))

        # Trunked personality -> talkgroup ID tables (0x0FD5 + 0x0FD4).
        trunk_tg_tables = self._decode_trunk_tg_tables(by_tag_inst)

        # Zone channel-name tables (0x0FFF), preserving original instance index
        # while dropping exact-duplicate mirror tables (e.g. 205CFR2930 stores
        # ["CHAN 1", "CHAN 2"] in both instance 0 and instance 1).
        zone_entries: List[Tuple[int, List[str]]] = []
        seen_tables: List[List[str]] = []
        for inst, payload in sorted(
            ((i, pl) for tag, i, pl in streams if tag == TAG_CHANNEL_NAMES)
        ):
            names = self._name_table(payload)
            if any(n for n in names) and names not in seen_tables:
                seen_tables.append(names)
                zone_entries.append((inst, names))

        # Per-zone 0x0FFC -> 0x0FFD reference records.
        channel_refs: Dict[int, Dict[str, int]] = {}
        for _tag, inst, pl in sorted(
            ((t, i, pl) for t, i, pl in streams if t == TAG_CHANNEL_REF),
            key=lambda x: x[1],
        ):
            ref = self._channel_ref(pl)
            if ref:
                channel_refs[inst] = ref

        # Fallback: highest-count conventional 0x0FFD record list (used when a
        # single deduplicated zone's own 0x0FFD chain has no conventional freqs,
        # as in 205CFR2930 where inst 0 and inst 1 share identical channel names
        # and the conventional freqs live in inst 1).
        best_conv_recs: List[Dict[str, Any]] = []
        for tag, _inst, payload in streams:
            if tag != TAG_CHANNEL_FREQS:
                continue
            decoded = [d for d in (self._decode_freq_rec(r)
                                   for r in self._freq_records(payload)) if d]
            if len(decoded) > len(best_conv_recs):
                best_conv_recs = decoded

        zones: List[Zone] = []
        for zi, (orig_inst, names) in enumerate(zone_entries):
            ref = channel_refs.get(orig_inst)
            raw_recs: List[bytes] = []
            if ref and ref["ref_tag"] == TAG_CHANNEL_FREQS:
                raw_recs = self._follow_ffd_chain(ref["ref_inst"], by_tag_inst)

            # Check if this zone has no conventional frequency records of its
            # own; for zone 0, fall back to the highest-count conventional
            # 0x0FFD table so single-zone or CpgWriter-patched codeplugs overlay
            # conventional frequencies onto zone 0 as calibrated.
            use_fallback_conv = (
                zi == 0
                and best_conv_recs
                and not any(self._decode_freq_rec(r) for r in raw_recs)
            )

            channels: List[Channel] = []
            cn = 0
            for si, raw_name in enumerate(names):
                name = raw_name.strip()
                if not name:
                    continue
                cn += 1
                raw_rec = raw_recs[si] if si < len(raw_recs) else None
                conv_rec = (
                    best_conv_recs[si]
                    if (use_fallback_conv and si < len(best_conv_recs))
                    else (self._decode_freq_rec(raw_rec) if raw_rec else None)
                )

                tg_id = 1
                if raw_rec is not None and len(raw_rec) >= OFF_TG_SLOT + 2:
                    owner = int.from_bytes(raw_rec[OFF_OWNER_TAG:OFF_OWNER_TAG + 2], "big")
                    link = int.from_bytes(raw_rec[OFF_OWNER_INST:OFF_OWNER_INST + 2], "big")
                    slot = raw_rec[OFF_TG_SLOT]
                    if owner == TAG_TRUNK_PERS and link in trunk_tg_tables:
                        tgs = trunk_tg_tables[link]
                        if 1 <= slot <= len(tgs):
                            tg_id = tgs[slot - 1]

                channels.append(Channel(
                    channel_number=cn,
                    name=name[:14],
                    rx_frequency=conv_rec["rx_frequency"] if conv_rec else 0.0,
                    tx_frequency=conv_rec["tx_frequency"] if conv_rec else 0.0,
                    voice_type="ASTRO P25",
                    rx_nac=conv_rec["rx_nac"] if conv_rec else "$293",
                    tx_nac=conv_rec["tx_nac"] if conv_rec else "$293",
                    talkgroup_id=tg_id,
                ))
            if channels:
                zlabel = (
                    raw_zone_names[orig_inst].strip()
                    if orig_inst < len(raw_zone_names) and raw_zone_names[orig_inst].strip()
                    else (
                        raw_zone_names[zi].strip()
                        if zi < len(raw_zone_names) and raw_zone_names[zi].strip()
                        else f"ZONE {zi + 1}"
                    )
                )
                zones.append(Zone(zone_number=zi + 1, name=zlabel, channels=channels))

        # Talkgroups (0x0FF8), sites (0x0FDC), scan lists (LIST tags),
        # plus radio identity (0x1004) and flashcode (0x1006).
        talkgroups: List[Talkgroup] = []
        sites: List[str] = []
        scan_lists: List[ScanList] = []
        seen_scan: set = set()
        ish_model: Optional[str] = None
        ish_serial: Optional[str] = None
        flashcode: str = ""

        for tag, _inst, payload in streams:
            if tag == TAG_RADIO_ID:
                rid = self._decode_radio_id_stream(payload)
                ish_model = ish_model or rid.get("model")
                ish_serial = ish_serial or rid.get("serial")
            elif tag == TAG_FLASHCODE:
                fc = self._decode_flashcode_stream(payload)
                if fc:
                    flashcode = fc
            elif tag == TAG_TALKGROUPS:
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

        model = self._header.get("model") or ish_model or "Motorola XTS 2500"
        serial = self._header.get("serial") or ish_serial or "UNKNOWN"
        bandsplit = infer_bandsplit(model)
        return RadioCodeplug(
            radio_model=model,
            bandsplit=bandsplit,
            serial_number=serial,
            flashcode=flashcode,
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
