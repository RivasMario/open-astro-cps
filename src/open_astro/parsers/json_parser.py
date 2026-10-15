import json
from dataclasses import asdict
from typing import Dict, Any
from ..models import RadioCodeplug, Zone, Channel

class JsonParser:
    @staticmethod
    def to_dict(codeplug: RadioCodeplug) -> Dict[str, Any]:
        return asdict(codeplug)

    @staticmethod
    def to_json(codeplug: RadioCodeplug, indent: int = 2) -> str:
        return json.dumps(JsonParser.to_dict(codeplug), indent=indent)

    @staticmethod
    def save_file(codeplug: RadioCodeplug, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(JsonParser.to_json(codeplug))

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> RadioCodeplug:
        zones = []
        for z_data in data.get("zones", []):
            channels = []
            for ch_data in z_data.get("channels", []):
                channels.append(Channel(**ch_data))
            zones.append(Zone(
                zone_number=z_data["zone_number"],
                name=z_data["name"],
                channels=channels
            ))
        return RadioCodeplug(
            radio_model=data.get("radio_model", "Motorola XTS"),
            bandsplit=data.get("bandsplit", "UHF"),
            serial_number=data.get("serial_number", ""),
            flashcode=data.get("flashcode", ""),
            zones=zones
        )

    @staticmethod
    def load_file(filepath: str) -> RadioCodeplug:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JsonParser.from_dict(data)
