"""Typed P25 / Type II Trunking Decoder (0x0FD0..0x0FDF).

Decodes ASTRO 25 trunked systems, control channels, and talkgroups from
codeplug objects without requiring Motorola CPS or an Advanced System Key (ASK) dongle.

Calibrated against empirical data from backups/Radio1_205CMB2249_codeplug.cpg:
  * 0x0FD2: Control channel candidate list (6.25 kHz step above 851.000 MHz)
  * 0x0FD4: Voice / site channels table
  * 0x0FDC: System Name table (16-byte ASCII records)
  * 0x0FDD: System ID table (u16 system ID)
  * 0x0FDE: Relational link (0x0FDD <-> 0x0FDC)
  * 0x0FDF: Talkgroup table (u16 TGID + flags)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

TAG_SYSTEM_PARAMS = 0x0FD0
TAG_SYSTEM_SUB = 0x0FD1
TAG_CONTROL_FREQS = 0x0FD2
TAG_FREQ_LINK = 0x0FD3
TAG_SITE_CHANNELS = 0x0FD4
TAG_SITE_LINK = 0x0FD5
TAG_SYSTEM_NAMES = 0x0FDC
TAG_SYSTEM_IDS = 0x0FDD
TAG_SYSTEM_LINK = 0x0FDE
TAG_TALKGROUPS = 0x0FDF

# Frequency calculation constants (800 MHz Land Mobile Band)
BASE_FREQ_HZ = 851_000_000
STEP_SIZE_HZ = 6_250


def channel_id_to_freq_hz(channel_id: int) -> int:
    """Convert 16-bit 800 MHz trunking channel ID to frequency in Hz."""
    return BASE_FREQ_HZ + (channel_id * STEP_SIZE_HZ)


def channel_id_to_freq_mhz(channel_id: int) -> float:
    """Convert 16-bit 800 MHz trunking channel ID to frequency in MHz."""
    return channel_id_to_freq_hz(channel_id) / 1_000_000.0


def freq_hz_to_channel_id(freq_hz: int) -> int:
    """Convert frequency in Hz to 16-bit 800 MHz trunking channel ID."""
    diff = freq_hz - BASE_FREQ_HZ
    if diff < 0 or diff % STEP_SIZE_HZ != 0:
        raise ValueError(f"Frequency {freq_hz} Hz does not align with 6.25 kHz grid above {BASE_FREQ_HZ} Hz")
    return diff // STEP_SIZE_HZ


@dataclass
class TrunkingControlChannel:
    """A control-channel entry from 0x0FD2."""
    flags: int
    rx_channel_id: int
    tx_channel_id: int
    rx_freq_mhz: float = 0.0
    tx_freq_mhz: float = 0.0

    def __post_init__(self) -> None:
        if self.rx_freq_mhz == 0.0:
            self.rx_freq_mhz = channel_id_to_freq_mhz(self.rx_channel_id)
        if self.tx_freq_mhz == 0.0:
            self.tx_freq_mhz = channel_id_to_freq_mhz(self.tx_channel_id)


@dataclass
class TrunkingTalkgroup:
    """A trunked talkgroup entry from 0x0FDF."""
    flags: int
    tgid: int
    priority_flags: int


@dataclass
class TrunkingSystem:
    """A decoded P25 / Type II trunking system."""
    system_index: int
    name: str
    system_id: int
    control_channels: List[TrunkingControlChannel] = field(default_factory=list)


class TrunkingDecoder:
    """Decodes trunking streams from a parsed codeplug dictionary or CpgData."""

    @staticmethod
    def decode_control_channels(data: bytes) -> List[TrunkingControlChannel]:
        """Decode a 0x0FD2 candidate control-channel stream."""
        if len(data) < 6:
            return []
        count = int.from_bytes(data[4:6], "big")
        records = []
        offset = 6
        rec_len = 5
        for _ in range(count):
            if offset + rec_len > len(data):
                break
            rec = data[offset : offset + rec_len]
            flags = rec[0]
            rx_ch = int.from_bytes(rec[1:3], "big")
            tx_ch = int.from_bytes(rec[3:5], "big")
            records.append(TrunkingControlChannel(
                flags=flags,
                rx_channel_id=rx_ch,
                tx_channel_id=tx_ch,
            ))
            offset += rec_len
        return records

    @staticmethod
    def decode_talkgroups(data: bytes) -> List[TrunkingTalkgroup]:
        """Decode a 0x0FDF talkgroup stream."""
        if len(data) < 6:
            return []
        count = int.from_bytes(data[4:6], "big")
        records = []
        offset = 6
        rec_len = 5
        for _ in range(count):
            if offset + rec_len > len(data):
                break
            rec = data[offset : offset + rec_len]
            flags = rec[0]
            tgid = int.from_bytes(rec[1:3], "big")
            prio = int.from_bytes(rec[3:5], "big")
            records.append(TrunkingTalkgroup(
                flags=flags,
                tgid=tgid,
                priority_flags=prio,
            ))
            offset += rec_len
        return records

    @staticmethod
    def decode_system_names(data: bytes) -> List[str]:
        """Decode 0x0FDC system name table."""
        if len(data) < 8:
            return []
        # Header: 4 bytes marker, 2 bytes name_len (typically 50), 2 bytes count
        count = int.from_bytes(data[6:8], "big")
        names = []
        offset = 8
        name_stride = 17
        for _ in range(count):
            if offset + name_stride > len(data):
                break
            raw_name = data[offset : offset + 16]
            name = raw_name.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            names.append(name)
            offset += name_stride
        return names

    @staticmethod
    def decode_system_ids(data: bytes) -> List[int]:
        """Decode 0x0FDD system ID table."""
        if len(data) < 6:
            return []
        count = int.from_bytes(data[4:6], "big")
        sys_ids = []
        offset = 6
        stride = 9
        for _ in range(count):
            if offset + stride > len(data):
                break
            rec = data[offset : offset + stride]
            sys_id = int.from_bytes(rec[:2], "big")
            sys_ids.append(sys_id)
            offset += stride
        return sys_ids

    @classmethod
    def decode_all_systems(cls, objects: Dict[Tuple[int, int, int], bytes]) -> List[TrunkingSystem]:
        """Extract and correlate all trunking systems from partition 0x80 objects."""
        # 1. Decode System Names (0x0FDC:0)
        name_data = objects.get((128, TAG_SYSTEM_NAMES, 0)) or objects.get((0x80, TAG_SYSTEM_NAMES, 0))
        names = cls.decode_system_names(name_data) if name_data else []

        # 2. Decode System IDs (0x0FDD:0)
        id_data = objects.get((128, TAG_SYSTEM_IDS, 0)) or objects.get((0x80, TAG_SYSTEM_IDS, 0))
        sys_ids = cls.decode_system_ids(id_data) if id_data else []

        systems = []
        total = min(len(names), len(sys_ids)) if (names and sys_ids) else max(len(names), len(sys_ids))
        for i in range(total):
            s_name = names[i] if i < len(names) else f"SYSTEM_{i+1}"
            s_id = sys_ids[i] if i < len(sys_ids) else (i + 1)
            # Find control channels in 0x0FD2 instance i
            cc_data = objects.get((128, TAG_CONTROL_FREQS, i)) or objects.get((0x80, TAG_CONTROL_FREQS, i))
            ccs = cls.decode_control_channels(cc_data) if cc_data else []
            systems.append(TrunkingSystem(
                system_index=i,
                name=s_name,
                system_id=s_id,
                control_channels=ccs,
            ))
        return systems
