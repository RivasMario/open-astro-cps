"""
OpenAstro Command Line Interface (CLI)
"""
import argparse
import os
import sys
from .models import RadioCodeplug, Zone, Channel, EncryptionKey
from .parsers import JsonParser, CsvParser, CpgParser
from .protocol import RadioSerialLink, AstroFlasher

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
        print("[-] No serial ports detected. Connect the radio and retry.")
        return

    print("[+] Detected serial ports:")
    for p in ports:
        print(f"  -> {p}")

    auto = RadioSerialLink.auto_detect_port()
    if auto:
        info = RadioSerialLink.describe_port(auto) or {}
        print(f"\n[+] Auto-detect would use: {auto}")
        if info.get("native_usb_radio"):
            print(f"    Native USB radio: {info.get('model_hint')} "
                  f"(VID:PID {info['vid']:04X}:{info['pid']:04X}, CDC-ACM)")
        if not os.access(auto, os.R_OK | os.W_OK):
            print(f"    [!] No read/write access to {auto}. Install the udev rule:")
            print("        sudo cp scripts/99-openastro.rules /etc/udev/rules.d/")
            print("        sudo udevadm control --reload-rules && sudo udevadm trigger")
            print("        (or: sudo usermod -aG dialout $USER, then log out and back in)")
    else:
        print("\n[-] No Motorola radio or known programming cable found among those ports.")

def cmd_probe(args):
    port = args.port or RadioSerialLink.auto_detect_port()
    if not port:
        print("[-] Error: No serial port found. Specify --port (e.g. COM3 or /dev/ttyUSB0).")
        sys.exit(1)

    print(f"[*] Probing radio on port {port}...")
    link = RadioSerialLink(port=port, baudrate=19200, timeout=1.5)
    try:
        link.connect()

        # 1. Real, verified path: the AT command interface this radio's own
        #    USB descriptor advertises (native-USB radios only -- see
        #    docs/AT_INTERFACE_DISCOVERY.md). Not gated: AT&V is a standard,
        #    read-only command, measured safe against real hardware.
        port_info = RadioSerialLink.describe_port(port)
        if port_info and port_info.get("native_usb_radio"):
            from .protocol import at_interface
            if at_interface.ping(link.connection):
                print("[+] Radio responded OK to AT -- link established.")
                info = at_interface.get_radio_identity(link.connection)
                banner = at_interface.get_firmware_banner(link.connection)
                print(f"[+] Radio Identity (AT&V):")
                if banner:
                    print(f"    Firmware: {banner}")
                for k, v in info.items():
                    print(f"    {k}: {v}")
                return
            else:
                print("[!] Radio is a native USB Motorola device but didn't answer AT. "
                      "Falling back to the unverified placeholder protocol below.")

        # 2. Fallback: the unverified placeholder SB9600 path. Gated.
        if not args.accept_unverified_protocol:
            print("[-] Refusing to try the placeholder protocol: unverified wire encoding")
            print("    (see docs/CPS_BINARY_ANALYSIS.md). Pass --accept-unverified-protocol")
            print("    to try it anyway -- expect silence, not a crash.")
            sys.exit(1)

        if not link.ping(allow_unverified_protocol=True):
            print("[-] Radio did not respond to the placeholder PING either.")
            sys.exit(1)
        print("[+] Radio PING OK: Link Established!")

        from .protocol.commands import UNKNOWN_GET_RADIO_INFO
        resp = link.send_command(UNKNOWN_GET_RADIO_INFO, b"", allow_unverified_protocol=True)
        if not resp:
            print("[!] Link responded, but failed to retrieve hardware identity string.")
            sys.exit(1)

        payload = resp.get("payload", b"")
        print(f"[+] Radio Hardware Identity Response Received ({len(payload)} bytes):")
        strings = [s.decode("latin1", errors="replace") for s in payload.split(b"\x00") if s]
        for s in strings:
            print(f"    -> {s}")

    except Exception as e:
        print(f"[-] Hardware probe error: {e}")
        sys.exit(1)
    finally:
        link.disconnect()

def cmd_reboot(args):
    port = args.port or RadioSerialLink.auto_detect_port()
    if not port:
        print("[-] Error: No serial port found. Specify --port.")
        sys.exit(1)
    
    if not args.accept_unverified_protocol:
        print("[-] Refusing to send reboot: unverified placeholder wire encoding (see")
        print("    docs/CPS_BINARY_ANALYSIS.md). Pass --accept-unverified-protocol to try anyway.")
        sys.exit(1)

    print(f"[*] Sending placeholder reboot command to radio on {port}...")
    link = RadioSerialLink(port=port, baudrate=19200, timeout=1.5)
    try:
        link.connect()
        if link.reboot_radio(allow_unverified_protocol=True):
            print("[+] Radio software reboot command acknowledged! Radio will reboot in ~1 second.")
        else:
            print("[-] Reboot command sent, but no ACK returned (radio may have already reset).")
    except Exception as e:
        print(f"[-] Reboot error: {e}")
    finally:
        link.disconnect()

def cmd_read(args):
    port = args.port or RadioSerialLink.auto_detect_port()
    if not port:
        print("[-] Error: No serial port found. Connect programming cable or specify --port.")
        sys.exit(1)

    if not args.accept_unverified_protocol:
        print("[-] Refusing to read: the wire encoding is an unverified placeholder")
        print("    (see docs/CPS_BINARY_ANALYSIS.md). Pass --accept-unverified-protocol to try anyway.")
        sys.exit(1)

    print(f"[*] Connecting to radio on {port} (placeholder wire encoding)...")
    link = RadioSerialLink(port=port, baudrate=19200, timeout=1.5)
    flasher = AstroFlasher(link)

    try:
        link.connect()
        info = flasher.get_radio_identity(allow_unverified_protocol=args.accept_unverified_protocol)
        print(f"[+] Radio Detected: {info.get('model')} (Serial: {info.get('serial')}, Flash: {info.get('flashcode')})")

        def progress(bytes_read, total_bytes, elapsed):
            pct = (bytes_read / total_bytes) * 100
            rate = (bytes_read / elapsed / 1024) if elapsed > 0 else 0
            eta = ((total_bytes - bytes_read) / (bytes_read / elapsed)) if (elapsed > 0 and bytes_read > 0) else 0
            sys.stdout.write(f"\r[*] Reading Radio: {pct:5.1f}% | {bytes_read//1024:3d}/{total_bytes//1024:3d} KB | {rate:4.1f} KB/s | ETA: {eta:3.0f}s")
            sys.stdout.flush()

        print("[*] Initiating codeplug dump (placeholder protocol)...")
        raw_data = flasher.read_codeplug(progress_callback=progress, allow_unverified_protocol=True)
        print(f"\n[+] Read complete: {len(raw_data)} bytes retrieved.")

        with open(args.output, "wb") as f:
            f.write(raw_data)
        print(f"[+] Saved raw codeplug image to: {args.output}")

    except Exception as e:
        print(f"\n[-] Read failure: {e}")
        sys.exit(1)
    finally:
        link.disconnect()

def cmd_write(args):
    port = args.port or RadioSerialLink.auto_detect_port()
    if not port:
        print("[-] Error: No serial port found. Connect programming cable or specify --port.")
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"[-] Input file not found: {args.input}")
        sys.exit(1)

    with open(args.input, "rb") as f:
        codeplug_bytes = f.read()

    print(f"[*] Loaded codeplug image: {len(codeplug_bytes)} bytes from {args.input}")
    print(f"[*] Connecting to radio on {port} at 19,200 baud...")
    link = RadioSerialLink(port=port, baudrate=19200, timeout=1.5)
    flasher = AstroFlasher(link)

    try:
        link.connect()
        info = flasher.get_radio_identity(allow_unverified_protocol=args.accept_unverified_protocol)
        print(f"[+] Target Radio: {info.get('model')} (Serial: {info.get('serial')})")

        def progress(bytes_written, total_bytes, elapsed):
            pct = (bytes_written / total_bytes) * 100
            rate = (bytes_written / elapsed / 1024) if elapsed > 0 else 0
            eta = ((total_bytes - bytes_written) / (bytes_written / elapsed)) if (elapsed > 0 and bytes_written > 0) else 0
            sys.stdout.write(f"\r[*] Flashing Radio: {pct:5.1f}% | {bytes_written//1024:3d}/{total_bytes//1024:3d} KB | {rate:4.1f} KB/s | ETA: {eta:3.0f}s")
            sys.stdout.flush()

        print("[*] Starting flash into Staging Bank B...")
        success = flasher.write_codeplug(
            codeplug_bytes,
            progress_callback=progress,
            allow_unverified_protocol=args.accept_unverified_protocol,
        )
        if success:
            print(f"\n[+] Flashing & CRC32 verification complete!")
            print("[+] Radio software watchdog reboot triggered. Ready for mission use!")

    except Exception as e:
        print(f"\n[-] Write failure: {e}")
        sys.exit(1)
    finally:
        link.disconnect()

def cmd_gui(args):
    import webbrowser
    import http.server
    import socketserver
    import threading
    from pathlib import Path

    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    html_path = docs_dir / "gui_mockup.html"

    if not html_path.exists():
        print(f"[-] GUI mockup file not found at {html_path}")
        sys.exit(1)

    port = args.port or 8080
    print(f"[+] Launching OpenAstro Web GUI...")
    print(f"[+] Serving interface at: http://127.0.0.1:{port}/gui_mockup.html")
    
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(docs_dir), **k)
        def log_message(self, format, *a):
            pass

    server = socketserver.TCPServer(("127.0.0.1", port), QuietHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    webbrowser.open(f"http://127.0.0.1:{port}/gui_mockup.html")
    print("[*] Press Ctrl+C in this terminal to stop the GUI server.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping GUI server.")
        server.shutdown()

def cmd_read_cpg(args):
    try:
        reader = CpgParser(args.input)
    except (RuntimeError, ValueError) as e:
        print(f"[-] {e}")
        sys.exit(1)
    try:
        data = reader.to_json(args.output, decrypt=not args.raw) if args.output else reader.parse(decrypt=not args.raw)
    finally:
        reader.close()

    hdr = data.get("header") or {}
    streams = data.get("streams", [])
    crc_ok = sum(1 for s in streams if s.get("crc_ok"))
    print(f"[+] .cpg is an OLE compound file ({len(streams)} streams). RC4 key {data['rc4_key']}")
    if hdr:
        print(f"[+] Header stream '{hdr.get('stream')}' ({hdr.get('size')} B, cleartext):")
        if hdr.get("model"):
            print(f"      Model : {hdr['model']}")
        if hdr.get("serial"):
            print(f"      Serial: {hdr['serial']}")
        if hdr.get("uuid"):
            print(f"      UUID  : {hdr['uuid']}")
    if not args.raw:
        print(f"[+] Stream CRC-16 check: {crc_ok}/{len(streams)} passed"
              f"{'  (0 passing => stream crypto needs calibration, see docs/CPG_FILE_FORMAT.md)' if crc_ok == 0 else ''}")
    if args.output:
        print(f"[+] Wrote structural dump: {args.output}")
    else:
        print("    (pass -o <file.json> to save the full structural dump)")


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

    # probe
    p_probe = subparsers.add_parser("probe", help="Probe radio hardware and display model, serial, and flashcode")
    p_probe.add_argument("-p", "--port", help="Serial port (default: auto-detect)")
    p_probe.add_argument("--accept-unverified-protocol", action="store_true",
                         help="Required to probe. The wire encoding is an unverified placeholder "
                              "known not to match the real protocol -- see docs/CPS_BINARY_ANALYSIS.md.")
    p_probe.set_defaults(func=cmd_probe)

    # read
    p_read = subparsers.add_parser("read", help="Read raw codeplug from radio with pre-flight tuning backup")
    p_read.add_argument("-p", "--port", help="Serial port (default: auto-detect)")
    p_read.add_argument("-o", "--output", default="radio_codeplug.bin", help="Output binary file path")
    p_read.add_argument("--accept-unverified-protocol", action="store_true",
                        help="Required to read. See docs/CPS_BINARY_ANALYSIS.md.")
    p_read.set_defaults(func=cmd_read)

    # write
    p_write = subparsers.add_parser("write", help="Write codeplug binary to radio Staging Bank with CRC verification")
    p_write.add_argument("input", help="Input binary codeplug file path")
    p_write.add_argument("-p", "--port", help="Serial port (default: auto-detect)")
    p_write.add_argument("--accept-unverified-protocol", action="store_true",
                         help="Required to write. The SB9600 opcodes and address map are "
                              "unverified guesses; a wrong map can destroy factory RF "
                              "calibration. Only use on a radio you can afford to lose.")
    p_write.set_defaults(func=cmd_write)

    # reboot
    p_reboot = subparsers.add_parser("reboot", help="Send placeholder reboot command to reset radio (unverified)")
    p_reboot.add_argument("-p", "--port", help="Serial port (default: auto-detect)")
    p_reboot.add_argument("--accept-unverified-protocol", action="store_true",
                          help="Required to send. See docs/CPS_BINARY_ANALYSIS.md.")
    p_reboot.set_defaults(func=cmd_reboot)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch modern interactive GUI in web browser")
    p_gui.add_argument("--port", type=int, default=8080, help="HTTP server port (default: 8080)")
    p_gui.set_defaults(func=cmd_gui)

    p_read_cpg = subparsers.add_parser("read-cpg", help="Read a .cpg codeplug file offline (OLE/RC4/CRC structural dump)")
    p_read_cpg.add_argument("input", help="Path to the .cpg file")
    p_read_cpg.add_argument("-o", "--output", help="Write full structural dump to this JSON file")
    p_read_cpg.add_argument("--raw", action="store_true", help="Do not attempt decryption; dump raw stream sizes only")
    p_read_cpg.set_defaults(func=cmd_read_cpg)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
