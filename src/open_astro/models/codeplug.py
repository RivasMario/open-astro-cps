from dataclasses import dataclass, field
from typing import List, Optional
from .channel import Channel

@dataclass
class EncryptionKey:
    key_id: int                         # Key ID (1 to 255)
    name: str                           # Key label (e.g., "TEAM_ADP_KEY")
    algorithm: str = "ADP"              # "ADP" (Software 40-bit RC4) or "AES-256"
    key_data: str = "A1B2C3D4E5"        # 10 hex characters for ADP (or 64 for AES-256)

@dataclass
class Talkgroup:
    tg_id: Optional[int]                # P25 talkgroup ID (parsed from name where present)
    name: str                           # Alias as stored (e.g., "TG 00002")

@dataclass
class ScanList:
    name: str                           # Scan-list alias (e.g., "LIST 1")

@dataclass
class Zone:
    zone_number: int
    name: str                           # 8 to 16 chars (e.g., "TEAM SECURE", "800 INTEROP")
    channels: List[Channel] = field(default_factory=list)

    def add_channel(self, channel: Channel) -> None:
        self.channels.append(channel)

    def get_channel(self, number: int) -> Optional[Channel]:
        for ch in self.channels:
            if ch.channel_number == number:
                return ch
        return None

@dataclass
class RadioCodeplug:
    radio_model: str                    # e.g., "Motorola XTS 2500 Model II"
    bandsplit: str                      # e.g., "700/800 MHz (764-870 MHz)"
    serial_number: str = "OPENASTRO_001"
    flashcode: str = "500008-000488-2"  # Default: Digital P25 + FPP Enabled (Luhn-valid check digit)
    zones: List[Zone] = field(default_factory=list)
    encryption_keys: List[EncryptionKey] = field(default_factory=list)
    talkgroups: List["Talkgroup"] = field(default_factory=list)
    sites: List[str] = field(default_factory=list)
    scan_lists: List["ScanList"] = field(default_factory=list)

    def add_zone(self, zone: Zone) -> None:
        self.zones.append(zone)

    def add_encryption_key(self, key: EncryptionKey) -> None:
        self.encryption_keys.append(key)

    def get_zone(self, number: int) -> Optional[Zone]:
        for z in self.zones:
            if z.zone_number == number:
                return z
        return None

    def total_channels(self) -> int:
        return sum(len(z.channels) for z in self.zones)
