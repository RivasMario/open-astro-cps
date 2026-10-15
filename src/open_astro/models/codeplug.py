from dataclasses import dataclass, field
from typing import List, Optional
from .channel import Channel

@dataclass
class Zone:
    zone_number: int
    name: str                           # 8 to 16 chars (e.g., "ZONE 1", "HAM 70CM")
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
    radio_model: str                    # e.g., "Motorola XTS 2500 / PRC-153"
    bandsplit: str                      # e.g., "UHF Range 1 (380-470 MHz)"
    serial_number: str = "OPENASTRO_001"
    flashcode: str = "500008-000488-4"  # Default: Digital P25 + FPP Enabled
    zones: List[Zone] = field(default_factory=list)

    def add_zone(self, zone: Zone) -> None:
        self.zones.append(zone)

    def get_zone(self, number: int) -> Optional[Zone]:
        for z in self.zones:
            if z.zone_number == number:
                return z
        return None

    def total_channels(self) -> int:
        return sum(len(z.channels) for z in self.zones)
