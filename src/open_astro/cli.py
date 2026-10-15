"""
OpenAstro Command Line Interface (CLI)
"""
import argparse
import sys
from .models import RadioCodeplug, Zone, Channel, EncryptionKey
from .parsers import JsonParser, CsvParser
from .protocol import RadioSerialLink

def cmd_new(args):
    codeplug = RadioCodeplug(
        radio_model=args.model,
        bandsplit=args.bandsplit,
        serial_number="OPENASTRO_SURPLUS",
        flashcode="500008-000488-4",
        encryption_keys=[
            EncryptionKey(key_id=1, name="TEAM_ADP_1", algorithm="ADP", key_data="A1B2C3D4E5")
        ],
        zones=[
            Zone(
                zone_number=1,
                name="TEAM SECURE",
                channels=[
                    Channel(1, "TEAM CLEAR", 851.51250, 851.51250, voice_type="ASTRO P25", rx_nac="$293", tx_nac="$293"),
                    Channel(2, "TEAM ENCRYPT", 852.01250, 852.01250, voice_type="ASTRO P25", rx_nac="$293", tx_nac="$293", secure_strapping="Secure", key_id=1, key_name="TEAM_ADP_1"),
                    Channel(3, "TEAM ANALOG", 853.01250, 853.01250, voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7)
                ]
            ),
            Zone(
                zone_number=2,
                name="800 INTEROP",
                channels=[
                    Channel(1, "8CALL90", 851.01250, 806.01250, voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7),
                    Channel(2, "8TAC91", 851.51250, 806.51250, voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7),
                    Channel(3, "8TAC92", 852.01250, 807.01250, voice_type="Analog", rx_pl_tone=156.7, tx_pl_tone=156.7)
                ]
            ),
            Zone(
                zone_number=3,
                name="PS MONITOR",
                channels=[
                    Channel(1, "PSERN CTRL 1", 851.88750, 851.88750, voice_type="ASTRO P25", rx_only=True),
                    Channel(2, "PSERN CTRL 2", 852.86250, 852.86250, voice_type="ASTRO P25", rx_only=True),
                    Channel(3, "PSERN CTRL 3", 853.82500, 853.82500, voice_type="ASTRO P25", rx_only=True)
                ]
            )
        ]
    )
    JsonParser.save_file(codeplug, args.output)
    print(f"[+] Successfully generated template codeplug: {args.output}")

def cmd_to_csv(args):
    codeplug = JsonParser.load_file(args.input)
    CsvParser.export_csv(codeplug, args.output)
    print(f"[+] Exported {codeplug.total_channels()} channels to CSV: {args.output}")

def cmd_from_csv(args):
    codeplug = CsvParser.import_csv(args.input, radio_model=args.model, bandsplit=args.bandsplit)
    JsonParser.save_file(codeplug, args.output)
    print(f"[+] Imported {codeplug.total_channels()} channels across {len(codeplug.zones)} zones to JSON: {args.output}")

def cmd_info(args):
    codeplug = JsonParser.load_file(args.input)
    print(f"\n==========================================")
    print(f" Radio Model  : {codeplug.radio_model}")
    print(f" Bandsplit    : {codeplug.bandsplit}")
    print(f" Serial Number: {codeplug.serial_number}")
    print(f" Flashcode    : {codeplug.flashcode}")
    print(f" Total Zones  : {len(codeplug.zones)}")
    print(f" Total Chans  : {codeplug.total_channels()}")
    if codeplug.encryption_keys:
        print(f" Crypto Keys  : {len(codeplug.encryption_keys)} defined")
        for k in codeplug.encryption_keys:
            print(f"   -> Key {k.key_id:d} ({k.name}): {k.algorithm} [Hash: {k.key_data[:4]}****]")
    print(f"==========================================")
    for z in codeplug.zones:
        print(f"\n[Zone {z.zone_number}: {z.name}] ({len(z.channels)} channels)")
        for ch in z.channels:
            tone_info = ""
            if ch.rx_pl_tone or ch.tx_pl_tone:
                tone_info = f" PL:{ch.rx_pl_tone}/{ch.tx_pl_tone}Hz"
            elif ch.voice_type == "ASTRO P25":
                enc_tag = f" [ENC:{ch.key_name or ch.key_id}]" if ch.secure_strapping == "Secure" else ""
                tone_info = f" NAC:{ch.rx_nac} TG:{ch.talkgroup_id}{enc_tag}"
            
            rx_lock = " [RX-ONLY LOCK]" if ch.rx_only else ""
            print(f"  Ch {ch.channel_number:2d}: {ch.name:<14} | Rx: {ch.rx_frequency:9.5f} | Tx: {ch.tx_frequency:9.5f} | {ch.voice_type}{tone_info}{rx_lock}")

def cmd_ports(args):
    ports = RadioSerialLink.list_ports()
    if not ports:
        print("[-] No COM / Serial ports detected. Connect your USB programming cable and retry.")
    else:
        print("[+] Detected Serial Ports:")
        for p in ports:
            print(f"  -> {p}")

def main():
    parser = argparse.ArgumentParser(description="OpenAstro: Open Source Motorola ASTRO 25 Codeplug Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = subparsers.add_parser("new", help="Generate a new template codeplug (JSON)")
    p_new.add_argument("-o", "--output", default="template.json", help="Output JSON filename")
    p_new.add_argument("--model", default="Motorola XTS 2500 Model II", help="Radio model name")
    p_new.add_argument("--bandsplit", default="700/800 MHz (764-870 MHz)", help="Radio frequency bandsplit")
    p_new.set_defaults(func=cmd_new)

    # to-csv
    p_to_csv = subparsers.add_parser("to-csv", help="Convert JSON codeplug to CSV spreadsheet")
    p_to_csv.add_argument("input", help="Input JSON file")
    p_to_csv.add_argument("output", help="Output CSV file")
    p_to_csv.set_defaults(func=cmd_to_csv)

    # from-csv
    p_from_csv = subparsers.add_parser("from-csv", help="Convert CSV spreadsheet to JSON codeplug")
    p_from_csv.add_argument("input", help="Input CSV file")
    p_from_csv.add_argument("output", help="Output JSON file")
    p_from_csv.add_argument("--model", default="Motorola XTS 2500 Model II")
    p_from_csv.add_argument("--bandsplit", default="700/800 MHz (764-870 MHz)")
    p_from_csv.set_defaults(func=cmd_from_csv)

    # info
    p_info = subparsers.add_parser("info", help="Display codeplug channel plan summary")
    p_info.add_argument("input", help="Input JSON codeplug file")
    p_info.set_defaults(func=cmd_info)

    # ports
    p_ports = subparsers.add_parser("ports", help="List detected USB programming cables / COM ports")
    p_ports.set_defaults(func=cmd_ports)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
