import csv
from typing import List, Optional
from ..models import RadioCodeplug, Zone, Channel

CSV_FIELDNAMES = [
    "Zone", "ZoneName", "Channel", "Name", "RxFrequency", "TxFrequency",
    "Spacing", "VoiceType", "RxPL", "TxPL", "RxDPL", "TxDPL",
    "RxNAC", "TxNAC", "Talkgroup", "Secure", "KeyID", "KeyName",
    "Power", "RxOnly", "ScanList"
]

class CsvParser:
    @staticmethod
    def export_csv(codeplug: RadioCodeplug, filepath: str) -> None:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            for z in codeplug.zones:
                for ch in z.channels:
                    writer.writerow({
                        "Zone": z.zone_number,
                        "ZoneName": z.name,
                        "Channel": ch.channel_number,
                        "Name": ch.name,
                        "RxFrequency": f"{ch.rx_frequency:.5f}",
                        "TxFrequency": f"{ch.tx_frequency:.5f}",
                        "Spacing": ch.channel_spacing_khz,
                        "VoiceType": ch.voice_type,
                        "RxPL": ch.rx_pl_tone if ch.rx_pl_tone is not None else "",
                        "TxPL": ch.tx_pl_tone if ch.tx_pl_tone is not None else "",
                        "RxDPL": ch.rx_dpl_code if ch.rx_dpl_code is not None else "",
                        "TxDPL": ch.tx_dpl_code if ch.tx_dpl_code is not None else "",
                        "RxNAC": ch.rx_nac,
                        "TxNAC": ch.tx_nac,
                        "Talkgroup": ch.talkgroup_id,
                        "Secure": ch.secure_strapping,
                        "KeyID": ch.key_id if ch.key_id is not None else "",
                        "KeyName": ch.key_name or "",
                        "Power": ch.power_level,
                        "RxOnly": "TRUE" if ch.rx_only else "FALSE",
                        "ScanList": ch.scan_list or ""
                    })

    @staticmethod
    def import_csv(filepath: str, radio_model: str = "Motorola XTS 2500", bandsplit: str = "700/800 MHz (764-870 MHz)") -> RadioCodeplug:
        zones_dict = {}
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                z_num = int(row["Zone"])
                z_name = row.get("ZoneName", f"ZONE {z_num}")
                if z_num not in zones_dict:
                    zones_dict[z_num] = Zone(zone_number=z_num, name=z_name, channels=[])

                def parse_float(val: Optional[str]) -> Optional[float]:
                    return float(val) if val and val.strip() else None

                def parse_int(val: Optional[str]) -> Optional[int]:
                    return int(val) if val and val.strip() else None

                ch = Channel(
                    channel_number=int(row["Channel"]),
                    name=row["Name"][:14],
                    rx_frequency=float(row["RxFrequency"]),
                    tx_frequency=float(row["TxFrequency"]),
                    channel_spacing_khz=float(row.get("Spacing", 12.5)),
                    voice_type=row.get("VoiceType", "Analog"),
                    rx_pl_tone=parse_float(row.get("RxPL")),
                    tx_pl_tone=parse_float(row.get("TxPL")),
                    rx_dpl_code=parse_int(row.get("RxDPL")),
                    tx_dpl_code=parse_int(row.get("TxDPL")),
                    rx_nac=row.get("RxNAC", "$293"),
                    tx_nac=row.get("TxNAC", "$293"),
                    talkgroup_id=parse_int(row.get("Talkgroup")),
                    secure_strapping=row.get("Secure", "Clear"),
                    key_id=parse_int(row.get("KeyID")),
                    key_name=row.get("KeyName") or None,
                    power_level=row.get("Power", "High"),
                    rx_only=row.get("RxOnly", "").upper() in ("TRUE", "1", "YES"),
                    scan_list=row.get("ScanList") or None
                )
                zones_dict[z_num].add_channel(ch)

        sorted_zones = [zones_dict[k] for k in sorted(zones_dict.keys())]
        return RadioCodeplug(
            radio_model=radio_model,
            bandsplit=bandsplit,
            zones=sorted_zones
        )
