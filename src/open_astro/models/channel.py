from dataclasses import dataclass
from typing import Optional

@dataclass
class Channel:
    channel_number: int
    name: str                           # 8 to 14 characters displayed on XTS LCD
    rx_frequency: float                 # MHz (e.g., 446.00000)
    tx_frequency: float                 # MHz (e.g., 446.00000)
    channel_spacing_khz: float = 12.5   # 12.5 kHz (narrowband) or 25.0 kHz
    voice_type: str = "Analog"          # "Analog", "ASTRO P25", or "Mixed Mode"
    
    # Analog CTCSS / CDCSS Squelch
    rx_pl_tone: Optional[float] = None  # Hz (e.g., 67.0, 107.2)
    tx_pl_tone: Optional[float] = None
    rx_dpl_code: Optional[int] = None   # Octal (e.g., 23, 74, 131)
    tx_dpl_code: Optional[int] = None
    
    # Digital ASTRO P25 Parameters
    rx_nac: str = "$293"                # Network Access Code (Default $293 = unmuted P25)
    tx_nac: str = "$293"
    talkgroup_id: int = 1               # Default P25 talkgroup
    
    # Operational Options
    rx_only: bool = False
    power_level: str = "High"           # "High" (5W) or "Low" (1W)
    scan_list: Optional[str] = None
    secure_strapping: str = "Clear"     # "Clear", "Secure", "Selectable"

    def is_simplex(self) -> bool:
        return abs(self.rx_frequency - self.tx_frequency) < 1e-6

    def repeater_offset(self) -> float:
        return round(self.tx_frequency - self.rx_frequency, 5)
