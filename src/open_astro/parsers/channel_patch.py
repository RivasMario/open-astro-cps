"""Channel patching for ASTRO 25 codeplugs.

Allows programmatically modifying channels (name, RX/TX frequency, CTCSS/DPL
squelch tones, NAC, simplex mode) in decoded codeplug objects (from .cpg or live
RCMP read).

Payload modifications:
  * TAG_CHANNEL_NAMES (0x0FFF): updates channel label within the zone's slot.
  * TAG_CHANNEL_FREQS (0x0FFD): updates the 35-byte FREQ_REC at the mapped slot
    (frequencies encoded as Hz / 5, CTCSS index or DPL octal code, simplex bit).
"""
from __future__ import annotations

import copy
import struct
from typing import Any, Dict, List, Optional, Tuple

from .cpg_decode import (
    TAG_CHANNEL_NAMES,
    TAG_CHANNEL_FREQS,
    TAG_CHANNEL_REF,
    NAME_TABLE_PREFIX,
    FREQ_REC_LEN,
    OFF_NAC_RX,
    OFF_NAC_TX,
    OFF_FREQ_RX,
    OFF_FREQ_TX,
    OFF_OPTIONS,
    SIMPLEX_BIT,
    CTCSS_EIA,
    DPL_CODES,
)
from ..protocol.write_session import CpgWriteAssembler, WriteObject, PartitionPolicy


class ChannelPatchError(Exception):
    pass


def encode_squelch_byte(pl_tone: Optional[float] = None,
                        dpl_code: Optional[int] = None) -> int:
    """Encode a squelch tone into the ASTRO 25 squelch byte.
    0 = CSQ (carrier squelch)
    1..42 = CTCSS tone index from EIA table
    >42 (bit 7 set) = DPL octal code index
    """
    if pl_tone is not None:
        # Find closest match in CTCSS_EIA
        for idx, freq in enumerate(CTCSS_EIA):
            if abs(freq - pl_tone) < 0.15:
                return idx + 1
        raise ChannelPatchError(f"unsupported CTCSS frequency {pl_tone} Hz")

    if dpl_code is not None:
        if dpl_code in DPL_CODES:
            idx = DPL_CODES.index(dpl_code)
            return 0x80 | idx
        raise ChannelPatchError(f"unsupported DPL code {dpl_code}")

    return 0  # CSQ


def _parse_nac_int(nac_str: str) -> int:
    """Parse '$293' or '0x293' or '293' into integer."""
    clean = nac_str.strip().replace("$", "").replace("0x", "")
    return int(clean, 16)


class ChannelPatcher:
    """Modify conventional channel objects in-place or generate RCMP write diffs."""

    def __init__(self, objects: List[Dict[str, Any]]):
        """`objects` is a list of dicts with keys: tag, instance, partition, payload."""
        self.objects = [dict(o) for o in objects]

    def _find_name_obj(self, zone_idx: int) -> Optional[Dict[str, Any]]:
        for o in self.objects:
            if o.get("tag") == TAG_CHANNEL_NAMES and o.get("instance") == zone_idx:
                return o
        return None

    def _find_zone_freq_target(self, zone_idx: int, chan_idx: int) -> Tuple[Dict[str, Any], int]:
        """Find the exact 0x0FFD object and the record offset for (zone_idx, chan_idx)."""
        refs = [o for o in sorted(self.objects, key=lambda x: x.get("instance", 0))
                if o.get("tag") == TAG_CHANNEL_REF]
        start_inst = zone_idx
        if zone_idx < len(refs):
            pl = refs[zone_idx]["payload"]
            if len(pl) >= 12:
                start_inst = int.from_bytes(pl[10:12], "big")

        inst = start_inst
        rem = chan_idx
        while True:
            target_obj = next((o for o in self.objects
                               if o.get("tag") == TAG_CHANNEL_FREQS and o.get("instance") == inst), None)
            if not target_obj:
                raise ChannelPatchError(f"freq object 0x0ffd instance {inst} not found for zone {zone_idx+1}")
            pl = target_obj["payload"]
            count = int.from_bytes(pl[4:6], "big")
            if rem < count:
                return target_obj, rem
            rem -= count
            inst += 1

    def patch_channel(self, zone_num: int, chan_num: int, *,
                      name: Optional[str] = None,
                      rx_frequency: Optional[float] = None,
                      tx_frequency: Optional[float] = None,
                      rx_pl_tone: Optional[float] = None,
                      tx_pl_tone: Optional[float] = None,
                      rx_dpl_code: Optional[int] = None,
                      tx_dpl_code: Optional[int] = None,
                      rx_nac: Optional[str] = None,
                      tx_nac: Optional[str] = None,
                      simplex: Optional[bool] = None) -> None:
        """Modify a specific channel in place. Zone and Channel numbers are 1-based."""
        zone_idx = zone_num - 1
        chan_idx = chan_num - 1

        # 1. Update name if requested
        if name is not None:
            name_obj = self._find_name_obj(zone_idx)
            if not name_obj:
                raise ChannelPatchError(f"zone {zone_num} name table not found")
            pl = bytearray(name_obj["payload"])
            count = int.from_bytes(pl[4:6], "big")
            if chan_idx >= count:
                raise ChannelPatchError(f"channel {chan_num} exceeds zone {zone_num} count {count}")
            slot_size = (len(pl) - NAME_TABLE_PREFIX) // count
            slot_start = NAME_TABLE_PREFIX + chan_idx * slot_size

            # Retain leading non-ASCII status byte if present (e.g. trunked zones)
            lead = b""
            if pl[slot_start] < 0x20 or pl[slot_start] > 0x7E:
                lead = bytes([pl[slot_start]])
            max_ascii_len = slot_size - len(lead)
            ascii_bytes = name.encode("ascii", errors="replace")[:max_ascii_len]
            padded = lead + ascii_bytes.ljust(slot_size - len(lead), b"\x00")
            pl[slot_start:slot_start + slot_size] = padded
            name_obj["payload"] = bytes(pl)

        # 2. Update frequency and parameters if requested
        freq_updates = any(x is not None for x in (
            rx_frequency, tx_frequency, rx_pl_tone, tx_pl_tone,
            rx_dpl_code, tx_dpl_code, rx_nac, tx_nac, simplex
        ))
        if freq_updates:
            freq_obj, rec_idx = self._find_zone_freq_target(zone_idx, chan_idx)
            pl = bytearray(freq_obj["payload"])
            rec_start = NAME_TABLE_PREFIX + rec_idx * FREQ_REC_LEN

            if rx_frequency is not None:
                pl[rec_start + OFF_FREQ_RX:rec_start + OFF_FREQ_RX + 4] = \
                    struct.pack(">I", int(round(rx_frequency * 200_000)))
            if tx_frequency is not None:
                pl[rec_start + OFF_FREQ_TX:rec_start + OFF_FREQ_TX + 4] = \
                    struct.pack(">I", int(round(tx_frequency * 200_000)))
            if rx_nac is not None:
                pl[rec_start + OFF_NAC_RX:rec_start + OFF_NAC_RX + 2] = \
                    struct.pack(">H", _parse_nac_int(rx_nac))
            if tx_nac is not None:
                pl[rec_start + OFF_NAC_TX:rec_start + OFF_NAC_TX + 2] = \
                    struct.pack(">H", _parse_nac_int(tx_nac))

            if rx_pl_tone is not None or rx_dpl_code is not None:
                pl[rec_start + OFF_OPTIONS] = encode_squelch_byte(rx_pl_tone, rx_dpl_code)
            if tx_pl_tone is not None or tx_dpl_code is not None:
                pl[rec_start + OFF_OPTIONS + 2] = encode_squelch_byte(tx_pl_tone, tx_dpl_code)

            if simplex is not None:
                if simplex:
                    pl[rec_start + OFF_OPTIONS + 3] |= SIMPLEX_BIT
                else:
                    pl[rec_start + OFF_OPTIONS + 3] &= ~SIMPLEX_BIT

            freq_obj["payload"] = bytes(pl)

    def generate_edits(self, original_objects: List[Dict[str, Any]]) -> List[str]:
        """Compare current objects against originals, returning --edit strings for rcmp_replay_write.py."""
        orig_map = {(o.get("tag"), o.get("instance")): o.get("payload") for o in original_objects}
        edits = []
        for o in self.objects:
            key = (o.get("tag"), o.get("instance"))
            orig_pl = orig_map.get(key)
            if orig_pl is not None and orig_pl != o.get("payload"):
                part = o.get("partition", 0x80)
                edits.append(f"{part:02x}:{o['tag']:04x}:{o['instance']:x}:{o['payload'].hex()}")
        return edits

    def to_write_assembler(self, policy: Optional[PartitionPolicy] = None) -> CpgWriteAssembler:
        """Create a CpgWriteAssembler from the modified objects."""
        write_objs = []
        for o in self.objects:
            part = o.get("partition", 0x80)
            write_objs.append(WriteObject(part, o["tag"], o["instance"], o["payload"]))
        return CpgWriteAssembler(write_objs, policy=policy)
