"""
OpenAstro Command Line Interface (CLI)
"""
import argparse
import os
import sys
from .models import RadioCodeplug, Zone, Channel, EncryptionKey
from .parsers import JsonParser, CsvParser, CpgParser, CpgDecoder, CpgWriter
from .parsers.button_edit import (
    ButtonPatcher,
    BUTTON_POSITIONS,
    BUTTON_ALIASES,
    FUNCTION_TOKENS,
    resolve_function,
    resolve_position,
    function_label,
    ButtonPatchError,
)
from .exporters.sdr_export import (
    export_dsdfme,
    export_sdrtrunk,
    export_dsdfme_launch,
    SDRTRUNK_KEY_NOTE,
)
from .protocol import RadioSerialLink, AstroFlasher

def cmd_new(args):
    codeplug = RadioCodeplug(
        radio_model=args.model,
        bandsplit=args.bandsplit,
        serial_number="OPENASTRO_SURPLUS",
        flashcode="500008-000488-2",
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
                host_ver = at_interface.get_host_version(link.connection)
                dsp_ver = at_interface.get_dsp_version(link.connection)
                print(f"[+] Radio Identity (AT&V):")
                if banner:
                    print(f"    Firmware: {banner}")
                if host_ver:
                    print(f"    {host_ver}")
                if dsp_ver:
                    print(f"    {dsp_ver}")
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
    directory = data.get("directory") or {}
    streams = data.get("streams", [])
    enc_streams = [s for s in streams if "crc_ok" in s]
    crc_ok = sum(1 for s in enc_streams if s.get("crc_ok"))
    print(f"[+] .cpg is an OLE compound file ({len(streams)} total streams). RC4 key {data['rc4_key']}")
    if hdr:
        print(f"[+] Header stream '{hdr.get('stream')}' ({hdr.get('size')} B, cleartext):")
        if hdr.get("model"):
            print(f"      Model : {hdr['model']}")
        if hdr.get("serial"):
            print(f"      Serial: {hdr['serial']}")
        if hdr.get("uuid"):
            print(f"      UUID  : {hdr['uuid']}")
    if not args.raw:
        print(f"[+] Encrypted stream CRC-16 check: {crc_ok}/{len(enc_streams)} passed"
              f"{'  (0 passing => stream crypto needs calibration, see docs/CPG_FILE_FORMAT.md)' if crc_ok == 0 else ''}")
        if directory:
            print(f"[+] Directory index ({directory.get('stream')}): "
                  f"{directory.get('matched_streams')}/{directory.get('record_count')} records matched")
    if args.output:
        print(f"[+] Wrote structural dump: {args.output}")
    else:
        print("    (pass -o <file.json> to save the full structural dump)")


def cmd_decode_cpg(args):
    try:
        decoder = CpgDecoder(args.input)
    except (RuntimeError, ValueError) as e:
        print(f"[-] {e}")
        sys.exit(1)
    try:
        codeplug = decoder.decode()
        personalities = decoder.personality_records()
    finally:
        decoder.close()

    JsonParser.save_file(codeplug, args.output)
    print(f"[+] Decoded {len(codeplug.zones)} zones / {codeplug.total_channels()} channels "
          f"from {codeplug.radio_model} (Serial: {codeplug.serial_number})")
    print(f"[+] Talkgroups: {len(codeplug.talkgroups)}  "
          f"Sites: {len(codeplug.sites)}  Scan lists: {len(codeplug.scan_lists)}")
    print(f"[+] Conventional personalities (unique 0x0FFB across all 0x0FFD instances): "
          f"{len(personalities)}")
    print(f"[+] Wrote typed codeplug JSON: {args.output}")
    if args.csv:
        CsvParser.export_csv(codeplug, args.csv)
        print(f"[+] Wrote channel CSV: {args.csv}")


def cmd_write_cpg(args):
    try:
        if args.input.lower().endswith(".csv"):
            codeplug = CsvParser.import_csv(args.input)
        else:
            codeplug = JsonParser.load_file(args.input)
        CpgWriter.write_codeplug(codeplug, args.output, template_path=args.template)
    except Exception as e:
        print(f"[-] {e}")
        sys.exit(1)
    print(f"[+] Patched {len(codeplug.zones)} zones / {codeplug.total_channels()} channels "
          f"into .cpg: {args.output} (template: {args.template})")


def cmd_rcmp_read(args):
    """Live READ-ONLY probe over the verified RCMP codec.

    Two transports: --serial COMx brings up PPP ourselves over the port (no
    Windows RAS entry, no re-dialing); otherwise connect to an already-up PPP
    link via TCP socket."""
    from .protocol.rcmp_transport import RcmpReadClient, RcmpError
    from .protocol import rcmp
    try:
        if args.serial:
            from .protocol.ppp_link import PppTcpConn, PppError
            try:
                conn = PppTcpConn(args.serial, dport=args.port, timeout=args.timeout)
            except PppError as e:
                print(f"[-] PPP bring-up failed on {args.serial}: {e}")
                sys.exit(1)
            client = RcmpReadClient(conn, timeout=args.timeout)
        else:
            client = RcmpReadClient.connect(host=args.host, port=args.port,
                                            timeout=args.timeout)
    except RcmpError as e:
        print(f"[-] {e}")
        sys.exit(1)
    try:
        ack = client.open_session()
        print(f"[+] session open ({ack['op']}) to {args.host}:{args.port}")
        part = int(args.partition, 0)
        # Read every object in ONE session; the radio drops PPP when the session
        # closes, so batching avoids a re-dial between objects.
        for obj_str in str(args.object).split(","):
            obj = int(obj_str.strip(), 0)
            data = client.read_object(part, obj, args.length)
            ascii_peek = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            print(f"[+] READ part=0x{part:02x} obj=0x{obj:04x} len={args.length} "
                  f"-> {len(data)} bytes")
            print(f"    hex: {data.hex()}")
            print(f"    txt: {ascii_peek}")
    except RcmpError as e:
        print(f"[-] {e}")
        sys.exit(1)
    finally:
        client.close()


def cmd_rcmp_dump(args):
    """Live READ-ONLY full codeplug read -> typed RadioCodeplug JSON."""
    from .protocol.rcmp_transport import RcmpReadClient, RcmpError
    from .parsers.cpg_decode import CpgDecoder
    try:
        if args.serial:
            from .protocol.ppp_link import PppTcpConn, PppError
            try:
                conn = PppTcpConn(args.serial, dport=args.port, timeout=args.timeout)
            except PppError as e:
                print(f"[-] PPP bring-up failed on {args.serial}: {e}")
                sys.exit(1)
            client = RcmpReadClient(conn, timeout=args.timeout)
        else:
            client = RcmpReadClient.connect(host=args.host, port=args.port,
                                            timeout=args.timeout)
    except RcmpError as e:
        print(f"[-] {e}")
        sys.exit(1)
    try:
        client.open_session()
        streams = client.read_streams(verbose=True)
    except RcmpError as e:
        print(f"[-] live read failed: {e}")
        sys.exit(1)
    finally:
        client.close()

    if not streams:
        print("[-] no objects read -- PPP link likely dropped; reset the radio and retry")
        sys.exit(1)
    print(f"[+] read {len(streams)} objects from the radio")
    codeplug = CpgDecoder.build_from_streams(streams, model=args.model,
                                             serial=args.serial_number)
    JsonParser.save_file(codeplug, args.output)
    print(f"[+] decoded {len(codeplug.zones)} zones / {codeplug.total_channels()} "
          f"channels, bandsplit {codeplug.bandsplit}")
    print(f"[+] wrote typed codeplug JSON: {args.output}")


def cmd_channel_edit(args):
    """Offline channel patcher: load .cpg or structural JSON objects, patch channel,
    and output modified objects or --edit CLI flags for rcmp_replay_write.py."""
    import json
    from .parsers.cpg_parser import CpgParser
    from .parsers.channel_patch import ChannelPatcher, ChannelPatchError

    if args.input.lower().endswith('.cpg'):
        parser = CpgParser(args.input)
        try:
            objs = parser.objects()
        finally:
            parser.close()
    else:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
        objs = data.get('objects', data)
        for o in objs:
            if isinstance(o.get('payload'), str):
                o['payload'] = bytes.fromhex(o['payload'])

    patcher = ChannelPatcher(objs)
    try:
        patcher.patch_channel(
            zone_num=args.zone,
            chan_num=args.channel,
            name=args.name,
            rx_frequency=args.rx_freq,
            tx_frequency=args.tx_freq,
            rx_pl_tone=args.rx_pl,
            tx_pl_tone=args.tx_pl,
            rx_dpl_code=args.rx_dpl,
            tx_dpl_code=args.tx_dpl,
            rx_nac=args.rx_nac,
            tx_nac=args.tx_nac,
            simplex=args.simplex,
        )
    except ChannelPatchError as e:
        print(f'[-] Edit failed: {e}')
        sys.exit(1)

    edits = patcher.generate_edits(objs)
    print(f'[+] Channel modified: Zone {args.zone}, Channel {args.channel}')
    if args.name:
        print(f'    Name: {args.name}')
    if args.rx_freq or args.tx_freq:
        print(f'    Freq: Rx={args.rx_freq} MHz, Tx={args.tx_freq} MHz')
    if args.rx_pl or args.tx_pl:
        print(f'    PL: Rx={args.rx_pl} Hz, Tx={args.tx_pl} Hz')
    if args.rx_dpl or args.tx_dpl:
        print(f'    DPL: Rx={args.rx_dpl}, Tx={args.tx_dpl}')
    print(f'[+] Generated {len(edits)} object edit(s) for live replay write:')
    for e in edits:
        print(f'    --edit {e}')

    if args.output:
        serializable = []
        for o in patcher.objects:
            entry = dict(o)
            entry['payload'] = o['payload'].hex()
            serializable.append(entry)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({'objects': serializable}, f, indent=2)
        print(f'[+] Saved patched objects to {args.output}')


def _parse_nibble_bit(spec):
    """Parse a 'NIBBLE:BIT' feature spec (e.g. '8:4') into (int, int)."""
    try:
        n_str, b_str = spec.split(":")
        nibble, bit = int(n_str, 0), int(b_str, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"feature spec must be NIBBLE:BIT (e.g. 8:4), got '{spec}'")
    if not (0 <= nibble <= 11) or bit not in (1, 2, 4, 8):
        raise argparse.ArgumentTypeError(f"nibble must be 0..11 and bit one of 1/2/4/8, got '{spec}'")
    return (nibble, bit)


def cmd_flashcode_upgrade(args):
    """Offline FLASHcode editor: flip feature bits, recompute the (verified Luhn)
    check digit, and emit a `--edit 81:1006:0:<HEX>` flag for rcmp_replay_write.py.
    Does NOT transmit -- partition 0x81 is ReadWriteLocked and needs UnlockSecurity
    (0x0107) first; see docs/FLASHCODE_AND_EEPROM_MAP.md."""
    from .models.flashcode import (
        FlashcodeDecoder, FLASHCODE_MATRIX, HARDWARE_GATED, ADP_Q667,
        FEATURE_FLAGS, PROFILES, format_flashcode, verify_flashcode,
        set_feature, feature_bits,
    )
    import json

    def _feat_label(key):
        feat = FLASHCODE_MATRIX.get(key)
        return f"{feat.code} {feat.name}" if feat else f"Nibble {key[0]} bit {key[1]} (proprietary)"

    # --list-features: print the friendly feature slugs and exit.
    if args.list_features:
        print("Feature switches (--enable / --disable <name>):\n")
        for slug, nb in FEATURE_FLAGS.items():
            gate = "  [UCM/dongle]" if nb in HARDWARE_GATED else ""
            print(f"  {slug:<20} {_feat_label(nb)}{gate}")
        print("\nProfiles (--profile): recommended | max-nonucm | max-ucm")
        print("  recommended : sane no-UCM P25 conventional load")
        print("  max-nonucm  : every software feature (no UCM) -- the no-UCM 'kitchen sink'")
        print("  max-ucm     : all 48 bits incl. hardware crypto (implies --ucm)")
        print("\n[UCM/dongle] features do nothing without the physical module; blocked unless --ucm.")
        return

    # Gate: hardware features need a UCM/dongle. Without --ucm, refuse to enable them.
    def _enable_bit(payload, nibble, bit, source):
        if (nibble, bit) in HARDWARE_GATED and not args.ucm:
            print(f"[-] '{source}' ({_feat_label((nibble, bit))}) needs a UCM/dongle you said")
            print(f"    this fleet does not have. Pass --ucm to force it anyway.")
            sys.exit(1)
        return set_feature(payload, nibble, bit, True)

    # 1. Resolve the starting 12-nibble payload.
    if args.set:
        payload = args.set.strip().upper()
        if len(payload) != 12 or any(c not in "0123456789ABCDEF" for c in payload):
            print(f"[-] --set must be 12 hex nibbles, got '{args.set}'")
            sys.exit(1)
    else:
        src = args.flashcode
        if args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    src = json.load(f).get("flashcode") or src
            except (OSError, ValueError) as e:
                print(f"[-] Could not read flashcode from {args.input}: {e}")
                sys.exit(1)
        payload = FlashcodeDecoder.clean_flashcode(src)
        if len(payload) != 12:
            print(f"[-] Could not parse a 12-nibble payload from '{src}'")
            sys.exit(1)

    if any(c not in "0123456789ABCDEF" for c in payload):
        print(f"[-] '{payload}' uses the extended-alphabet flashcode format (letters beyond")
        print("    hex A-F, e.g. G/L/Q/R/S/Y -- newer H98/H51/M22/M25-SS/M37 families).")
        print("    Only the classic numeric/hex format is supported (verified Luhn). Aborting.")
        sys.exit(1)

    before = set(feature_bits(payload))
    old_fc = format_flashcode(payload)

    # 2. Apply operations: profile -> kitchen-sink -> enable -> add -> adp -> disable -> remove.
    def _apply_all_bits(payload, allow_ucm):
        # All software features ON; hardware-gated bits ON only with --ucm, else
        # CLEARED (strip dead UCM bits from a no-UCM load, incl. pre-existing ones).
        for n in range(12):
            for b in (8, 4, 2, 1):
                if (n, b) in HARDWARE_GATED:
                    payload = set_feature(payload, n, b, allow_ucm)
                else:
                    payload = set_feature(payload, n, b, True)
        return payload

    if args.profile == "recommended":
        for slug in PROFILES["recommended"]:
            n, b = FEATURE_FLAGS[slug]
            payload = _enable_bit(payload, n, b, slug)
    elif args.profile == "max-nonucm":
        payload = _apply_all_bits(payload, allow_ucm=False)
    elif args.profile == "max-ucm":
        payload = _apply_all_bits(payload, allow_ucm=True)   # implies UCM installed

    if args.kitchen_sink:
        payload = _apply_all_bits(payload, allow_ucm=args.ucm)

    for slug in (args.enable or []):
        if slug not in FEATURE_FLAGS:
            print(f"[-] Unknown feature '{slug}'. Use --list-features for valid names.")
            sys.exit(1)
        n, b = FEATURE_FLAGS[slug]
        payload = _enable_bit(payload, n, b, slug)

    if args.add_adp:
        payload = _enable_bit(payload, ADP_Q667[0], ADP_Q667[1], "adp")

    for n, b in (args.add or []):
        payload = _enable_bit(payload, n, b, f"{n}:{b}")

    for slug in (args.disable or []):
        if slug not in FEATURE_FLAGS:
            print(f"[-] Unknown feature '{slug}'. Use --list-features for valid names.")
            sys.exit(1)
        n, b = FEATURE_FLAGS[slug]
        payload = set_feature(payload, n, b, False)

    for n, b in (args.remove or []):
        payload = set_feature(payload, n, b, False)

    after = set(feature_bits(payload))
    new_fc = format_flashcode(payload)

    def _label(key):
        feat = FLASHCODE_MATRIX.get(key)
        return f"{feat.code} {feat.name}" if feat else f"Nibble {key[0]} bit {key[1]} (proprietary)"

    # 3. Report.
    print(f"\n[+] FLASHcode upgrade")
    print(f"    From: {old_fc}")
    print(f"    To  : {new_fc}")
    print(f"    (check digit {new_fc[-1]} = verified Luhn mod-10; self-check {'OK' if verify_flashcode(new_fc) else 'FAIL'})")

    added = sorted(after - before)
    removed = sorted(before - after)
    if added:
        print(f"\n[+] Features ENABLED ({len(added)}):")
        for k in added:
            gate = HARDWARE_GATED.get(k)
            print(f"    + {_label(k)}" + (f"   [!] HARDWARE-GATED: {gate}" if gate else ""))
    if removed:
        print(f"\n[-] Features DISABLED ({len(removed)}):")
        for k in removed:
            print(f"    - {_label(k)}")
    if not added and not removed:
        print("\n[*] No feature change (payload identical).")

    gated_on = sorted(k for k in after if k in HARDWARE_GATED)
    if gated_on:
        print(f"\n[!] {len(gated_on)} feature(s) in the final flashcode need physical hardware")
        print("    and will NOT activate from the bit alone (UCM / dongle):")
        for k in gated_on:
            print(f"      - {_label(k)}: {HARDWARE_GATED[k]}")
    if args.kitchen_sink:
        print("\n[!] --kitchen-sink sets ALL 48 bits. Some combinations (band/channel-spacing")
        print("    straps) are mutually exclusive and UNTESTED on hardware -- the radio's")
        print("    acceptance of an arbitrary all-features code is not yet confirmed. Prefer")
        print("    targeted flags (e.g. --add-adp) for a known-good single-bit change.")

    # 4. Emit the write record (ASCII of the dashed string + NUL pad to 16 bytes).
    ascii_bytes = new_fc.encode("ascii") + b"\x00"   # 15 chars + NUL = 16-byte object
    edit_hex = ascii_bytes.hex()
    print(f"\n[+] Replay-write flag for 81:1006:0 (ASCII '{new_fc}' + NUL pad, 16 B):")
    print(f"    --edit 81:1006:0:{edit_hex}")
    print(f"    (undashed-ascii variant: {(payload + new_fc[-1]).encode('ascii').hex()})")

    print("\n[!] This writes partition 0x81 (RW-LOCKED). It will NOT persist over plain RCMP:")
    print("    the radio must be unlocked first (CRcmpBundler::UnlockSecurity / 0x0107), and")
    print("    the exact 16-byte on-wire framing of 0x1006 is UNCONFIRMED -- verify with")
    print("    `open-astro rcmp-read --partition 0x81 --object 0x1006 --length 0x10` on the")
    print("    radio before transmitting. See docs/FLASHCODE_AND_EEPROM_MAP.md.")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({
                "old_flashcode": old_fc, "new_flashcode": new_fc,
                "payload": payload, "check_digit": new_fc[-1],
                "edit_flag": f"81:1006:0:{edit_hex}",
                "features_enabled": [{"nibble": k[0], "bit": k[1], "label": _label(k),
                                      "hardware_gated": k in HARDWARE_GATED} for k in added],
                "features_disabled": [{"nibble": k[0], "bit": k[1], "label": _label(k)} for k in removed],
            }, f, indent=2)
        print(f"\n[+] Wrote upgrade summary: {args.output}")


def cmd_export_sdr(args):
    """Export codeplug channels and talkgroups to DSD-FME and/or SDRTrunk."""
    codeplug = JsonParser.load_file(args.input)
    fmt = args.format
    if fmt in ("dsdfme", "both"):
        paths = export_dsdfme(codeplug, args.output_dir)
        print("[+] Exported DSD-FME files:")
        print(f"    Channel map: {paths['channel_map']}")
        print(f"    Group list : {paths['group']}")
    if fmt in ("sdrtrunk", "both"):
        path = export_sdrtrunk(codeplug, args.output_dir)
        print(f"[+] Exported SDRTrunk playlist: {path}")

    if getattr(args, "emit_launch", False):
        try:
            launch_path = export_dsdfme_launch(codeplug, args.output_dir, key=args.key)
        except ValueError as e:
            print(f"[-] Could not emit DSD-FME launch command: {e}")
            sys.exit(1)
        print(f"[+] Emitted DSD-FME launch command: {launch_path}")
        if args.key:
            print(f"    (ADP key passed to DSD-FME via -K; keep the .sh out of public repos)")
        print(f"[!] {SDRTRUNK_KEY_NOTE}")


def cmd_buttons(args):
    """Offline button-assignment editor: patch conventional button functions
    and generate --edit CLI flags for rcmp_replay_write.py."""
    if args.list_buttons:
        print("Supported Physical Buttons:")
        for slug, (idx, desc) in BUTTON_POSITIONS.items():
            print(f"  {slug:<15} (index {idx}): {desc}")
        print("\nAliases:")
        for alias, target in BUTTON_ALIASES.items():
            print(f"  {alias:<15} -> {target}")
        if not args.list_functions:
            return

    if args.list_functions:
        print("Known Function Tokens:")
        for name, token in FUNCTION_TOKENS.items():
            print(f"  {name:<22} : 0x{token:02x}")
        return

    if not args.input:
        print("[-] Error: input codeplug or structural JSON dump is required.")
        sys.exit(1)

    try:
        patcher = ButtonPatcher.from_file(args.input)
    except Exception as e:
        print(f"[-] Edit failed: {e}")
        sys.exit(1)

    if not args.set:
        print(f"[+] Button configuration for {args.input}:")
        short_tokens = patcher.current_tokens("short")
        long_tokens = patcher.current_tokens("long")
        print("\n  Short Press (0x0016):")
        for slug, (idx, desc) in BUTTON_POSITIONS.items():
            if idx < len(short_tokens):
                print(f"    {slug:<14} ({desc}): {function_label(short_tokens[idx])}")
        print("\n  Long Press (0x0017):")
        for slug, (idx, desc) in BUTTON_POSITIONS.items():
            if idx < len(long_tokens):
                print(f"    {slug:<14} ({desc}): {function_label(long_tokens[idx])}")
        return

    orig_short = list(patcher.current_tokens("short"))
    orig_long = list(patcher.current_tokens("long"))

    all_notes = []
    for item in args.set:
        if "=" not in item:
            print(f"[-] Invalid format for --set: '{item}'. Expected <button>=<function> (e.g. orange=monitor)")
            sys.exit(1)
        btn, func = item.split("=", 1)
        btn = btn.strip()
        func = func.strip()
        try:
            notes = patcher.set_button(btn, func, long_press=args.long)
            if notes:
                all_notes.extend(notes)
        except ButtonPatchError as e:
            print(f"[-] Edit failed: {e}")
            sys.exit(1)

    new_short = patcher.current_tokens("short")
    new_long = patcher.current_tokens("long")

    press_label = "Long Press (0x0017)" if args.long else "Short Press (0x0016)"
    print(f"[+] Modified button assignments ({press_label}):")
    changed = False
    for slug, (idx, desc) in BUTTON_POSITIONS.items():
        if idx < len(orig_short) and idx < len(new_short) and orig_short[idx] != new_short[idx]:
            print(f"    [Short] {slug} ({desc}): {function_label(orig_short[idx])} -> {function_label(new_short[idx])}")
            changed = True
        if idx < len(orig_long) and idx < len(new_long) and orig_long[idx] != new_long[idx]:
            print(f"    [Long]  {slug} ({desc}): {function_label(orig_long[idx])} -> {function_label(new_long[idx])}")
            changed = True
    if not changed:
        print("    (no changes detected; values already matched)")

    for note in all_notes:
        print(f"[!] Note: {note}")

    edits = patcher.generate_edits()
    print(f"[+] Generated {len(edits)} object edit(s) for live replay write:")
    for e in edits:
        print(f"    --edit {e}")

    if args.output:
        patcher.save_json(args.output)
        print(f"[+] Saved patched objects to {args.output}")


def cmd_trunking_dump(args):
    """Dump P25/Type II trunking systems, control channels, and talkgroups."""
    import json
    from .parsers.cpg_parser import CpgParser
    from .parsers.trunking_decode import TrunkingDecoder, TAG_TALKGROUPS

    if args.input.lower().endswith(".cpg"):
        cpg = CpgParser.load_file(args.input)
        objects = cpg.objects
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        objects = {}
        for k, v in data.items():
            if isinstance(k, str) and ":" in k:
                parts = [int(p, 0) for p in k.split(":")]
                objects[(parts[0], parts[1], parts[2])] = bytes.fromhex(v) if isinstance(v, str) else bytes(v)

    systems = TrunkingDecoder.decode_all_systems(objects)
    master_tg_data = objects.get((128, TAG_TALKGROUPS, 0)) or objects.get((0x80, TAG_TALKGROUPS, 0))
    talkgroups = TrunkingDecoder.decode_talkgroups(master_tg_data) if master_tg_data else []

    if args.json:
        out = {
            "systems": [
                {
                    "system_index": s.system_index,
                    "name": s.name,
                    "system_id": s.system_id,
                    "control_channels": [
                        {
                            "flags": cc.flags,
                            "rx_channel_id": cc.rx_channel_id,
                            "tx_channel_id": cc.tx_channel_id,
                            "rx_freq_mhz": cc.rx_freq_mhz,
                            "tx_freq_mhz": cc.tx_freq_mhz,
                        }
                        for cc in s.control_channels
                    ],
                }
                for s in systems
            ],
            "master_talkgroups": [
                {"tgid": tg.tgid, "flags": tg.flags, "priority_flags": tg.priority_flags}
                for tg in talkgroups
            ],
        }
        json_str = json.dumps(out, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"[+] Wrote trunking dump JSON to {args.output}")
        else:
            print(json_str)
        return

    print(f"\n[+] P25 / Type II Trunking Systems ({len(systems)} found in {args.input}):")
    print("=" * 70)
    for s in systems:
        print(f"System #{s.system_index + 1:<2} | Name: {s.name:<12} | System ID: {s.system_id} (0x{s.system_id:04X})")
        if s.control_channels:
            print(f"  Candidate Control Channels ({len(s.control_channels)}):")
            for idx, cc in enumerate(s.control_channels):
                flag_str = " (revert/alt)" if cc.flags & 0x80 else ""
                print(f"    [{idx+1:2d}] {cc.rx_freq_mhz:.4f} MHz (Ch {cc.rx_channel_id}){flag_str}")
        else:
            print("  (no control channels configured)")
        print("-" * 70)

    if talkgroups:
        print(f"\n[+] Master Fleet Talkgroup List ({len(talkgroups)} entries):")
        tg_strings = [f"{tg.tgid}" for tg in talkgroups]
        for i in range(0, len(tg_strings), 7):
            print("  " + "  ".join(f"{tg:<6}" for tg in tg_strings[i:i+7]))
        print("=" * 70)


def cmd_make_nas(args):
    """Build a safe Non-Affiliation Scan (NAS) codeplug or objects bundle."""
    import json
    from .builders.nas_builder import (
        NasBuilder,
        NasSafetyViolation,
    )

    # Parse control channels (accept comma-separated or multiple flags)
    ccs = []
    if args.control_channels:
        for item in args.control_channels:
            for part in str(item).split(","):
                part = part.strip()
                if part:
                    ccs.append(float(part))
    else:
        ccs = [856.1625, 860.4375, 860.5875]

    try:
        builder = NasBuilder.create_default(
            system_id=args.system_id,
            system_name=args.system_name,
            control_channels=ccs,
            target_tgid=args.tgid,
            target_name=args.tg_name,
            park_name=args.dummy_name,
            park_rx_freq=args.dummy_freq,
            zone_num=args.zone,
            chan_num=args.channel,
        )
    except NasSafetyViolation as e:
        print(f"[-] Safety violation: {e}")
        sys.exit(1)

    summary = builder.export_summary()

    # If base codeplug is provided, load and patch it
    if args.input:
        if args.input.lower().endswith(".json"):
            codeplug = JsonParser.load_file(args.input)
        elif args.input.lower().endswith(".cpg"):
            decoder = CpgDecoder(args.input)
            try:
                codeplug = decoder.decode()
            finally:
                decoder.close()
        else:
            print(f"[-] Unsupported input format: {args.input}")
            sys.exit(1)

        builder.apply_to_codeplug(codeplug)
        if args.output:
            JsonParser.save_file(codeplug, args.output)
            if not args.json:
                print(f"[+] Successfully patched NAS into codeplug: {args.output}")
    else:
        # Build standalone codeplug template with NAS zone
        codeplug = RadioCodeplug(
            radio_model="Motorola XTS 5000 Model III",
            bandsplit="700/800 MHz (764-870 MHz)",
            serial_number="NAS_STAGING",
            flashcode="FBFFFF-B7F3FF-1",
            zones=[]
        )
        builder.apply_to_codeplug(codeplug)
        if args.output:
            JsonParser.save_file(codeplug, args.output)
            if not args.json:
                print(f"[+] Successfully wrote NAS codeplug to {args.output}")

    if args.emit_objects:
        objs = builder.generate_codeplug_objects()
        serializable_objs = {
            f"{p}:{t}:{i}": pl.hex()
            for (p, t, i), pl in objs.items()
        }
        with open(args.emit_objects, "w", encoding="utf-8") as f:
            json.dump(serializable_objs, f, indent=2)
        if not args.json:
            print(f"[+] Wrote {len(objs)} codeplug objects to {args.emit_objects}")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("\n=======================================================")
        print(" Non-Affiliation Scan (NAS) Configuration")
        print("=======================================================")
        print(f" Trunking System : {summary['trunking_system']['system_name']} (ID: {summary['trunking_system']['system_id']})")
        print(f" Control Channels: {', '.join(f'{f:.4f} MHz' for f in summary['trunking_system']['control_channels'])}")
        print(f" Target TGID     : {summary['talkgroups'][0]['tgid']} ({summary['talkgroups'][0]['name']})")
        print(f" Parked Channel  : Zone {summary['park_channel']['zone']} Ch {summary['park_channel']['channel']} - {summary['park_channel']['name']}")
        print(f" Parked RX Freq  : {summary['park_channel']['rx_frequency_mhz']:.4f} MHz")
        print(f" Parked TX Freq  : {summary['park_channel']['tx_frequency_mhz']:.4f} MHz (STRICT 0.0)")
        print(f" RX Only / Inhibit: {summary['park_channel']['rx_only']} / {summary['park_channel']['tx_inhibit']}")
        print(f" Zero RF Emission: ENFORCED (Passive DSP monitoring)")
        print(f" Inhibit Immunity: ACTIVE (No ISW affiliation emitted)")
        print("=======================================================\n")


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

    # decode-cpg
    p_decode_cpg = subparsers.add_parser("decode-cpg",
        help="Decode a .cpg into a typed RadioCodeplug JSON (zones, conventional/trunked channels, talkgroups)")
    p_decode_cpg.add_argument("input", help="Path to the .cpg file")
    p_decode_cpg.add_argument("-o", "--output", default="codeplug.json",
                              help="Output typed JSON codeplug (default: codeplug.json)")
    p_decode_cpg.add_argument("--csv", help="Also export channels to this CSV file")
    p_decode_cpg.set_defaults(func=cmd_decode_cpg)

    # write-cpg
    p_write_cpg = subparsers.add_parser("write-cpg",
        help="Apply a JSON or CSV codeplug onto a template .cpg file with CRC-16 and RC4")
    p_write_cpg.add_argument("input", help="Input JSON or CSV codeplug file")
    p_write_cpg.add_argument("output", help="Output .cpg file path")
    p_write_cpg.add_argument("-t", "--template", default="backups/205CFR2930.cpg",
                             help="Donor/template .cpg file (default: backups/205CFR2930.cpg)")
    p_write_cpg.set_defaults(func=cmd_write_cpg)

    # rcmp-read (live, read-only)
    p_rcmp = subparsers.add_parser("rcmp-read",
        help="Live READ-ONLY object read over the verified RCMP codec (needs PPP link up)")
    p_rcmp.add_argument("--serial", help="Bring up PPP ourselves over this COM/tty port (e.g. COM7); no RAS entry needed")
    p_rcmp.add_argument("--host", default="192.168.128.1", help="Radio PPP IP (default 192.168.128.1)")
    p_rcmp.add_argument("--port", type=int, default=8002, help="RCMP TCP port (default 8002)")
    p_rcmp.add_argument("--partition", default="0x80", help="Partition selector (0x80 codeplug, 0x82 tuning)")
    p_rcmp.add_argument("--object", default="0x0047", help="Object id, e.g. 0x0047")
    p_rcmp.add_argument("--length", type=lambda s: int(s, 0), default=0x10, help="Bytes to read")
    p_rcmp.add_argument("--timeout", type=float, default=5.0, help="Socket timeout seconds")
    p_rcmp.set_defaults(func=cmd_rcmp_read)

    # rcmp-dump (live, read-only full codeplug read)
    p_dump = subparsers.add_parser("rcmp-dump",
        help="Live READ-ONLY full codeplug read into a typed RadioCodeplug JSON")
    p_dump.add_argument("--serial", help="Bring up PPP over this COM/tty port (e.g. COM7)")
    p_dump.add_argument("--host", default="192.168.128.1", help="Radio PPP IP")
    p_dump.add_argument("--port", type=int, default=8002, help="RCMP TCP port")
    p_dump.add_argument("--timeout", type=float, default=5.0, help="Timeout seconds")
    p_dump.add_argument("-o", "--output", default="live_codeplug.json", help="Output JSON path")
    p_dump.add_argument("--model", default="Motorola XTS 2500", help="Model string for the output")
    p_dump.add_argument("--serial-number", default="UNKNOWN", help="Serial for the output")
    p_dump.set_defaults(func=cmd_rcmp_dump)

    # channel-edit (offline channel patcher)
    p_edit = subparsers.add_parser("channel-edit",
        help="Modify a channel (name, freq, PL/DPL) and generate --edit replay flags")
    p_edit.add_argument("input", help="Path to source .cpg or structural JSON dump")
    p_edit.add_argument("--zone", type=int, required=True, help="Zone number (1-based)")
    p_edit.add_argument("--channel", type=int, required=True, help="Channel number (1-based)")
    p_edit.add_argument("--name", help="New channel name (up to 14 chars)")
    p_edit.add_argument("--rx-freq", type=float, help="RX frequency in MHz")
    p_edit.add_argument("--tx-freq", type=float, help="TX frequency in MHz")
    p_edit.add_argument("--rx-pl", type=float, help="RX CTCSS PL tone in Hz (e.g. 156.7)")
    p_edit.add_argument("--tx-pl", type=float, help="TX CTCSS PL tone in Hz (e.g. 156.7)")
    p_edit.add_argument("--rx-dpl", type=int, help="RX DPL octal code (e.g. 23)")
    p_edit.add_argument("--tx-dpl", type=int, help="TX DPL octal code (e.g. 23)")
    p_edit.add_argument("--rx-nac", help="RX NAC hex string (e.g. $293)")
    p_edit.add_argument("--tx-nac", help="TX NAC hex string (e.g. $293)")
    p_edit.add_argument("--simplex", action="store_true", help="Set simplex/direct mode")
    p_edit.add_argument("-o", "--output", help="Optional output JSON for patched objects")
    p_edit.set_defaults(func=cmd_channel_edit)

    # flashcode-upgrade (offline: flip feature bits + compute check digit)
    p_fc = subparsers.add_parser("flashcode-upgrade",
        help="Edit FLASHcode feature bits, recompute the check digit, emit a 81:1006:0 write flag")
    p_fc.add_argument("--flashcode", default="000008-002410-2",
                      help="Starting flashcode (default: fleet 000008-002410-2)")
    p_fc.add_argument("--input", help="Read starting flashcode from a JSON file's 'flashcode' field")
    p_fc.add_argument("--set", help="Override: raw 12-nibble payload (hex), skips --flashcode")
    p_fc.add_argument("--add-adp", action="store_true",
                      help="Enable Q667 Motorola ADP software encryption (nibble 8 bit 4)")
    p_fc.add_argument("--add", type=_parse_nibble_bit, action="append", metavar="N:B",
                      help="Enable feature at NIBBLE:BIT (e.g. 8:4); repeatable")
    p_fc.add_argument("--remove", type=_parse_nibble_bit, action="append", metavar="N:B",
                      help="Disable feature at NIBBLE:BIT; repeatable")
    p_fc.add_argument("--profile", choices=["recommended", "max-nonucm", "max-ucm"],
                      help="Preset: recommended (sane no-UCM P25 conventional), max-nonucm "
                           "(all software features), max-ucm (all 48 bits, implies UCM present)")
    p_fc.add_argument("--enable", action="append", metavar="FEATURE",
                      help="Enable a named feature (see --list-features); repeatable")
    p_fc.add_argument("--disable", action="append", metavar="FEATURE",
                      help="Disable a named feature; repeatable")
    p_fc.add_argument("--ucm", action="store_true",
                      help="Allow hardware-gated features (AES/DES/HW-multikey/ASK). Default: "
                           "refuse them -- this fleet has no UCM, so the bits are dead weight.")
    p_fc.add_argument("--kitchen-sink", action="store_true",
                      help="Set all feature bits. Without --ucm = software-only (no-UCM max); "
                           "with --ucm = all 48. Experimental; see warnings.")
    p_fc.add_argument("--list-features", action="store_true",
                      help="List all feature switch names + profiles and exit")
    p_fc.add_argument("-o", "--output", help="Write upgrade summary to this JSON file")
    p_fc.set_defaults(func=cmd_flashcode_upgrade)

    # export-sdr
    p_sdr = subparsers.add_parser("export-sdr", help="Export codeplug to DSD-FME CSVs and SDRTrunk playlist XML")
    p_sdr.add_argument("input", help="Path to codeplug JSON file")
    p_sdr.add_argument("--format", choices=["dsdfme", "sdrtrunk", "both"], default="both",
                       help="Export format (default: both)")
    p_sdr.add_argument("-o", "--output-dir", default=".", help="Output directory for generated files (default: .)")
    p_sdr.add_argument("--key", metavar="HEX",
                       help="ADP/RC4 key (hex, e.g. A1B2C3D4E5) passed to the emitted DSD-FME "
                            "launch command via -K. Only used with --emit-launch.")
    p_sdr.add_argument("--emit-launch", action="store_true",
                       help="Also emit a best-effort DSD-FME launch script (<base>_dsdfme_run.sh) "
                            "referencing the generated CSVs, P25 Phase 1 flags, and --key if given.")
    p_sdr.set_defaults(func=cmd_export_sdr)

    # buttons
    p_btn = subparsers.add_parser("buttons",
        help="Modify button assignments (short/long press) and generate --edit replay flags")
    p_btn.add_argument("input", nargs="?", help="Path to source .cpg or structural JSON dump")
    p_btn.add_argument("--list-buttons", action="store_true", help="List supported physical buttons and exit")
    p_btn.add_argument("--list-functions", action="store_true", help="List known function tokens and exit")
    p_btn.add_argument("--set", action="append", metavar="BUTTON=FUNCTION",
                       help="Set button function (e.g. orange=monitor, side2=scan); repeatable")
    p_btn.add_argument("--long", action="store_true",
                       help="Target long-press (0x0017) instead of short-press (0x0016)")
    p_btn.add_argument("-o", "--output", help="Path to write patched JSON dump")
    p_btn.set_defaults(func=cmd_buttons)

    # trunking-dump
    p_tdump = subparsers.add_parser("trunking-dump",
        help="Inspect P25/Type II trunking systems, control channels, and talkgroups")
    p_tdump.add_argument("input", help="Path to .cpg codeplug or structural JSON file")
    p_tdump.add_argument("--json", action="store_true", help="Output raw structured JSON")
    p_tdump.add_argument("-o", "--output", help="Write output to file instead of stdout")
    p_tdump.set_defaults(func=cmd_trunking_dump)

    # make-nas
    p_nas = subparsers.add_parser("make-nas",
        help="Generate safe Non-Affiliation Scan (NAS) codeplug (zero transmit, inhibit protected)")
    p_nas.add_argument("--input", help="Optional source .cpg or .json codeplug to patch NAS into")
    p_nas.add_argument("--system-name", default="PUGET SOUND", help="Trunking system display name (default: PUGET SOUND)")
    p_nas.add_argument("--system-id", type=int, default=1, help="Trunking system ID (default: 1)")
    p_nas.add_argument("--control-channels", action="append", metavar="MHZ",
                       help="Candidate control channel frequency (MHz). Can specify multiple times or comma-separated")
    p_nas.add_argument("--tgid", type=int, default=1188, help="Target talkgroup ID (default: 1188)")
    p_nas.add_argument("--tg-name", default="SEATTLE DISP", help="Target talkgroup name (default: SEATTLE DISP)")
    p_nas.add_argument("--dummy-name", default="NAS PARK", help="Rotary knob parked dummy channel name (default: NAS PARK)")
    p_nas.add_argument("--dummy-freq", type=float, default=851.0125, help="Dummy channel RX frequency MHz (default: 851.0125)")
    p_nas.add_argument("--zone", type=int, default=1, help="Zone number for dummy channel (default: 1)")
    p_nas.add_argument("--channel", type=int, default=1, help="Channel position for dummy channel (default: 1)")
    p_nas.add_argument("-o", "--output", default="nas_codeplug.json", help="Output codeplug JSON path (default: nas_codeplug.json)")
    p_nas.add_argument("--emit-objects", metavar="JSON_PATH", help="Optional path to output raw RCMP write objects JSON")
    p_nas.add_argument("--json", action="store_true", help="Output JSON summary to stdout")
    p_nas.set_defaults(func=cmd_make_nas)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
