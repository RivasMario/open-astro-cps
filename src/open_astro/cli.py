"""
OpenAstro Command Line Interface (CLI)
"""
import argparse
import sys
from .models import RadioCodeplug, Zone, Channel
from .parsers import JsonParser, CsvParser
from .protocol import RadioSerialLink

def cmd_new(args):
    codeplug = RadioCodeplug(
        radio_model=args.model,
        bandsplit=args.bandsplit,
        serial_number="OPENASTRO_SURPLUS",
        flashcode="500008-000488-4",
        zones=[
            Zone(
                zone_number=1,
                name="HAM 70CM",
                channels=[
                    Channel(1, "CALL 446.0", 446.00000, 446.00000, voice_type="Analog"),
                    Channel(2, "RPT 444.1", 449.10000, 444.10000, voice_type="Analog", rx_pl_tone=107.2, tx_pl_tone=107.2),
                    Channel(3, "P25 CALL", 441.00000, 441.00000, voice_type="ASTRO P25", rx_nac="$293", tx_nac="$293")
                ]
            ),
            Zone(
                zone_number=2,
                name="GMRS CHANNELS",
                channels=[
                    Channel(1, "GMRS 15", 462.55000, 462.55000, voice_type="Analog", rx_pl_tone=67.0, tx_pl_tone=67.0),
                    Channel(2, "GMRS RPT15", 462.55000, 467.55000, voice_type="Analog", rx_pl_tone=141.3, tx_pl_tone=141.3)
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
    print(f"==========================================")
    for z in codeplug.zones:
        print(f"\n[Zone {z.zone_number}: {z.name}] ({len(z.channels)} channels)")
        for ch in z.channels:
            tone_info = ""
            if ch.rx_pl_tone or ch.tx_pl_tone:
                tone_info = f" PL:{ch.rx_pl_tone}/{ch.tx_pl_tone}Hz"
            elif ch.voice_type == "ASTRO P25":
                tone_info = f" NAC:{ch.rx_nac} TG:{ch.talkgroup_id}"
            print(f"  Ch {ch.channel_number:2d}: {ch.name:<14} | Rx: {ch.rx_frequency:9.5f} | Tx: {ch.tx_frequency:9.5f} | {ch.voice_type}{tone_info}")

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
    p_new.add_argument("--model", default="Motorola XTS 2500 / PRC-153", help="Radio model name")
    p_new.add_argument("--bandsplit", default="UHF 380-470 MHz", help="Radio frequency bandsplit")
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
    p_from_csv.add_argument("--model", default="Motorola XTS 2500 / PRC-153")
    p_from_csv.add_argument("--bandsplit", default="UHF 380-470 MHz")
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
