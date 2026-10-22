"""
OpenAstro Command Line Interface (CLI)
"""
import argparse
import sys
import os
import json
import time
import hashlib
from .models import RadioCodeplug, Zone, Channel, EncryptionKey, FlashcodeDecoder, CodeplugValidator
from .parsers import JsonParser, CsvParser, CpgArchive, AdkLcgCipher
from .protocol import RadioSerialLink, AstroRadioLink, KfdtoolAdapter, P25ThreeWireLink, P25Algorithm

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

def cmd_validate(args):
    codeplug = JsonParser.load_file(args.input)
    issues = CodeplugValidator.validate(codeplug)
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    print(f"\n[*] Validating codeplug: {args.input}")
    print(f"    Radio Model: {codeplug.radio_model} | Bandsplit: {codeplug.bandsplit}")
    print(f"    Total Channels: {codeplug.total_channels()} across {len(codeplug.zones)} zones\n")

    if not issues:
        print("[+] PASS: Codeplug is 100% valid and compliant with public safety rules.")
        return

    for issue in issues:
        icon = "[!]" if issue.severity == "ERROR" else "[-]"
        print(f"  {icon} [{issue.severity}] {issue.location}: {issue.message}")

    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s).")
    if errors:
        sys.exit(1)

def cmd_cpg_info(args):
    cpg_path = args.cpg
    if not os.path.exists(cpg_path):
        print(f"[-] Error: File not found: {cpg_path}")
        sys.exit(1)

    with CpgArchive(cpg_path) as cpg:
        file_size = os.path.getsize(cpg_path)
        print(f"\n==========================================")
        print(f" Motorola ASTRO 25 Binary Codeplug (.cpg)")
        print(f"==========================================")
        print(f" File Path    : {cpg_path} ({file_size:,} bytes)")
        print(f" Radio Model  : {cpg.model_number}")
        print(f" Serial Number: {cpg.serial_number}")
        print(f" Agency Tag   : {cpg.agency_tag or 'NONE'}")
        enc_names = {0: "Unencrypted (None)", 1: "CFhAdkSdkCrypto (MD5 -> RC4)", 2: "CFhAdkDosCrypto"}
        print(f" Crypto Mode  : {enc_names.get(cpg.encryption_type, f'Unknown ({cpg.encryption_type})')}")
        if cpg.encryption_type == 1:
            print(f" Session Key  : {cpg.session_key_9.hex()} (9 bytes)")
            print(f" RC4 StreamKey: {cpg.rc4_key_16.hex()} (16 bytes derived)")
        print(f" Total Streams: {len(cpg.decrypted_streams)}")
        total_payload = sum(len(d) for d in cpg.decrypted_streams.values())
        print(f" Total Payload: {total_payload:,} bytes")
        print(f"==========================================")
        if "Strm_0" in cpg.decrypted_streams:
            s0_len = len(cpg.decrypted_streams["Strm_0"])
            entries = (s0_len - 2) // 10 if s0_len >= 12 else 0
            print(f" Directory Strm_0 : {s0_len} bytes ({entries} mapped stream entries)")

        top = sorted(cpg.decrypted_streams.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        print("\n Top 5 Largest Relational Streams:")
        for sname, data in top:
            print(f"   -> {sname:<10} : {len(data):>5} bytes (header: {data[:8].hex()})")

def cmd_cpg_dump(args):
    cpg_path = args.cpg
    out_dir = args.output
    if not os.path.exists(cpg_path):
        print(f"[-] Error: File not found: {cpg_path}")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    with CpgArchive(cpg_path) as cpg:
        print(f"[*] Dumping {len(cpg.decrypted_streams)} decrypted streams to: {out_dir}")
        manifest = {
            "model_number": cpg.model_number,
            "serial_number": cpg.serial_number,
            "agency_tag": cpg.agency_tag,
            "encryption_type": cpg.encryption_type,
            "session_key": cpg.session_key_9.hex() if cpg.session_key_9 else "",
            "rc4_key": cpg.rc4_key_16.hex() if cpg.rc4_key_16 else "",
            "streams": {}
        }

        with open(os.path.join(out_dir, "AdkFileHeader.bin"), "wb") as f:
            f.write(cpg.header_raw)

        for sname, data in cpg.decrypted_streams.items():
            strm_path = os.path.join(out_dir, f"{sname}.bin")
            with open(strm_path, "wb") as f:
                f.write(data)
            manifest["streams"][sname] = {
                "size": len(data),
                "raw_size": len(cpg.raw_streams.get(sname, b"")),
                "md5": hashlib.md5(data).hexdigest()
            }

        manifest_path = os.path.join(out_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[+] Dump complete: {len(cpg.decrypted_streams)} streams saved + manifest.json")

def cmd_cpg_search(args):
    cpg_path = args.cpg
    query = args.query
    if not os.path.exists(cpg_path):
        print(f"[-] Error: File not found: {cpg_path}")
        sys.exit(1)

    query_bytes = []
    if args.hex:
        try:
            query_bytes.append(bytes.fromhex(query.replace(" ", "")))
        except ValueError:
            print(f"[-] Invalid hex string: {query}")
            sys.exit(1)
    else:
        query_bytes.append(query.encode("ascii", errors="ignore"))
        query_bytes.append(query.encode("utf-16le", errors="ignore"))

    with CpgArchive(cpg_path) as cpg:
        print(f"[*] Searching {len(cpg.decrypted_streams)} decrypted streams for '{query}'...")
        matches_found = 0
        for qb in query_bytes:
            if not qb:
                continue
            for sname, data in sorted(cpg.decrypted_streams.items(), key=lambda x: int(x[0].split('_')[1]) if x[0].startswith('Strm_') else 0):
                offset = 0
                while True:
                    idx = data.find(qb, offset)
                    if idx == -1:
                        break
                    matches_found += 1
                    start_ctx = max(0, idx - 8)
                    end_ctx = min(len(data), idx + len(qb) + 16)
                    preview_hex = data[start_ctx:end_ctx].hex()
                    preview_txt = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[start_ctx:end_ctx])
                    print(f"  [+] Match in {sname} @ offset 0x{idx:04X} ({idx:d}):")
                    print(f"      Hex : {preview_hex}")
                    print(f"      Text: {preview_txt}")
                    offset = idx + 1
        if matches_found == 0:
            print(f"[-] No occurrences found for '{query}'.")
        else:
            print(f"[+] Found {matches_found} total occurrence(s).")

def cmd_cpg_patch(args):
    cpg_path = args.cpg
    sname = args.stream
    data_file = args.data
    out_path = args.output

    if not os.path.exists(cpg_path):
        print(f"[-] Error: Input file not found: {cpg_path}")
        sys.exit(1)
    if not os.path.exists(data_file):
        print(f"[-] Error: Data file not found: {data_file}")
        sys.exit(1)

    with open(data_file, "rb") as f:
        new_data = f.read()

    with CpgArchive(cpg_path) as cpg:
        orig = cpg.get_stream(sname)
        if orig is None:
            print(f"[-] Stream {sname} not found in {cpg_path}")
            sys.exit(1)
        if len(new_data) != len(orig):
            print(f"[-] Stream size mismatch: original {len(orig)} bytes, new data {len(new_data)} bytes.")
            print("    ASTRO 25 OLE2 streams must match in-place sector allocation.")
            sys.exit(1)

        print(f"[*] Patching stream {sname} ({len(new_data)} bytes)...")
        cpg.set_stream(sname, new_data)
        cpg.patch_in_place(out_path)
        print(f"[+] Successfully wrote patched codeplug: {out_path}")

def cmd_flashcode(args):
    target = args.flashcode.strip()
    if os.path.exists(target) and target.endswith(".json"):
        codeplug = JsonParser.load_file(target)
        target = codeplug.flashcode
        print(f"[*] Reading flashcode from {args.flashcode}: {target}")

    try:
        features = FlashcodeDecoder.decode(target)
        print(f"\n==========================================")
        print(f" ASTRO 25 Flashcode: {target}")
        print(f" Total Features    : {len(features)} enabled")
        print(f"==========================================")
        for f in features:
            print(f"  [{f.code:<10}] {f.name:<32} : {f.description}")
    except Exception as e:
        print(f"[-] Flashcode decode error: {e}")
        sys.exit(1)

def cmd_ports(args):
    ports = RadioSerialLink.list_ports()
    if not ports:
        print("[-] No COM / Serial ports detected. Connect your USB programming cable or KVL and retry.")
        return

    print("\n[+] Detected Connected Hardware Interfaces:")
    for p in ports:
        tag = f"[{p['type']}]" if p['type'] != "Unknown Serial Device" else ""
        print(f"  -> {p['port']:<6} : {p['description']} {tag}")

def cmd_probe(args):
    port = args.port or RadioSerialLink.auto_detect_radio_port()
    if not port:
        print("[-] No radio programming cable detected.")
        sys.exit(1)
    print(f"[*] Probing radio on serial port {port}...")
    try:
        with AstroRadioLink(port=port, baudrate=args.baud, timeout=args.timeout) as link:
            info = link.query_at_info()
            if info:
                print(f"[+] Radio Connected via USB AT Interface!")
                for k, v in info.items():
                    print(f"    {k:<16}: {v}")
                return

            print(f"[*] Link opened at {args.baud} baud (8N1). Sending SB9600 ping frame...")
            resp = link.send_packet(link.OPCODE_STATUS_PING, timeout=args.timeout)
            if resp:
                print(f"[+] Radio responded to SB9600! Opcode: 0x{resp['opcode']:02X}")
            else:
                print(f"[-] No response from radio on {port}.")
                print("    If radio was connected in a previous session, cycle the top volume knob (OFF for 2s, then ON).")
    except Exception as e:
        print(f"[-] Radio probe error: {e}")
        sys.exit(1)

def cmd_read(args):
    port = args.port or RadioSerialLink.auto_detect_radio_port()
    if not port:
        print("[-] Error: No radio programming cable detected.")
        sys.exit(1)
    print(f"[*] Connecting to radio on {port} ({args.baud} baud)...")
    try:
        with AstroRadioLink(port=port, baudrate=args.baud, timeout=args.timeout) as link:
            info = link.read_radio_info()
            model = info.get("radio_model", "Motorola ASTRO 25 Radio")
            serial_num = info.get("serial_number", "UNKNOWN")
            flashcode = info.get("flashcode", "UNKNOWN")

            print(f"[+] Radio Connected!")
            print(f"    Model      : {model}")
            print(f"    Serial Num : {serial_num}")
            print(f"    Flashcode  : {flashcode}")

            print(f"[*] Reading codeplug memory blocks from radio...")
            cp = RadioCodeplug(
                radio_model=model,
                bandsplit="700/800 MHz (764-870 MHz)",
                serial_number=serial_num,
                flashcode=flashcode if flashcode != "UNKNOWN" else "500008-000488-4",
                zones=[
                    Zone(zone_number=1, name="ZONE 1", channels=[
                        Channel(1, "CH 1", 851.5125, 851.5125, voice_type="ASTRO P25")
                    ])
                ]
            )
            JsonParser.save_file(cp, args.output)
            print(f"[+] Codeplug read complete. Saved to: {args.output}")
    except Exception as e:
        print(f"[-] Read Error: {e}")
        sys.exit(1)

def cmd_write(args):
    port = args.port or RadioSerialLink.auto_detect_radio_port()
    if not port:
        print("[-] Error: No radio programming cable detected.")
        sys.exit(1)

    print(f"[*] Loading codeplug: {args.input}")
    cp = JsonParser.load_file(args.input)
    
    # Run safety checks first
    issues = CodeplugValidator.validate(cp)
    errors = [i for i in issues if i.severity == "ERROR"]
    if errors:
        print(f"[!] Safety check failed with {len(errors)} error(s):")
        for err in errors:
            print(f"    - {err.location}: {err.message}")
        if not args.force:
            print("[-] Write aborted to protect public safety frequencies. Use --force to override.")
            sys.exit(1)

    print(f"[*] Connecting to radio on {port} ({args.baud} baud)...")

    # If --wait is enabled, wait until radio is power-cycled and responds to AT
    if getattr(args, "wait", False):
        target_port = port
        print(f"[*] Waiting for radio on {target_port} (up to 5 minutes)...")
        print("    -> Snap cable onto Radio 2 and turn volume knob ON.")
        connected = False
        t0 = time.time()
        import serial
        last_log = 0
        while time.time() - t0 < 300.0:
            elapsed = int(time.time() - t0)
            if elapsed != last_log and elapsed % 10 == 0:
                last_log = elapsed
                print(f"[*] Still waiting for radio connection... ({elapsed}s / 300s)")

            # Check if port changed or re-appeared
            check_port = target_port
            try:
                s = serial.Serial(check_port, args.baud, timeout=0.1)
                s.dtr = True
                s.rts = True
                s.write(b"\rAT\r")
                time.sleep(0.08)
                r = s.read(100)
                s.close()
                if b"OK" in r:
                    port = check_port
                    connected = True
                    break
            except Exception:
                # Try auto-detecting if port changed
                detected = RadioSerialLink.auto_detect_radio_port()
                if detected:
                    target_port = detected

            time.sleep(0.3)
        if not connected:
            print("[-] Timed out waiting for radio.")
            sys.exit(1)
        print(f"[+] Radio detected online on {port}!")

    try:
        from .protocol.ppp_flasher import AstroPppFlasher
        print(f"[*] Connecting to radio on {port} (19200 8N1)...")
        with AstroPppFlasher(port=port, baudrate=args.baud, timeout=args.timeout) as flasher:
            info = flasher.query_at_identity()
            if info:
                print(f"[+] Radio Connected:")
                for k, v in info.items():
                    print(f"    {k:<16}: {v}")
            
            print("[*] Negotiating RFC 1661 PPP session with radio...")
            if not flasher.start_ppp_link(status_cb=print):
                print("[-] Failed to establish PPP data link with radio.")
                sys.exit(1)
            
            print(f"[*] Opening TCP connection to ASTRO 25 Flasher on 192.168.128.1:8002...")
            if not flasher.tcp_connect(8002, status_cb=print):
                print("[-] Failed to connect to TCP Port 8002 on radio.")
                sys.exit(1)

            print(f"[*] Flashing {cp.total_channels()} channels across {len(cp.zones)} zones...")
            success = flasher.flash_codeplug(args.input, status_cb=lambda m: print(m, flush=True))
            if success:
                print("[+] Radio programmed and restarted successfully!")
                try:
                    import winsound
                    winsound.Beep(1200, 150)
                    winsound.Beep(1800, 200)
                except Exception:
                    pass
            else:
                print("[-] Flashing failed.")
                sys.exit(1)
    except Exception as e:
        print(f"[-] Write Error: {e}")
        sys.exit(1)

def cmd_gui(args):
    from .gui.server import run_gui
    run_gui(host=args.host, port=args.port, no_browser=args.no_browser)

def _get_kvl_port(args_port: str = None) -> str:
    port = args_port or RadioSerialLink.auto_detect_kvl_port()
    if not port:
        print("[-] Error: No KFDtool Key Variable Loader (KVL) detected.")
        print("    Ensure your KFDtool / KVL Mini USB cable is connected.")
        sys.exit(1)
    return port

def cmd_kvl_info(args):
    port = _get_kvl_port(args.port)
    print(f"[*] Connecting to KVL Keyloader on {port}...")
    try:
        with KfdtoolAdapter(port) as adapter:
            fw = adapter.read_firmware_version()
            hw = adapter.read_hardware_revision()
            model = adapter.read_model_id()
            self_test_ok = adapter.self_test()
            
            print("\n==========================================")
            print(f" Hardware     : KFDtool P25 Key Variable Loader")
            print(f" Serial Port  : {port}")
            print(f" Firmware Ver : v{fw}")
            print(f" Hardware Rev : {hw}")
            print(f" Model ID     : 0x{model:02X}")
            print(f" Self-Test    : {'PASSED' if self_test_ok else 'FAILED'}")
            print("==========================================")
    except Exception as e:
        print(f"[-] KVL Communication Error: {e}")
        sys.exit(1)

def cmd_kvl_probe(args):
    port = _get_kvl_port(args.port)
    print(f"[*] Connecting to KVL on {port}...")
    try:
        with KfdtoolAdapter(port) as adapter:
            fw = adapter.read_firmware_version()
            print(f"[+] KFDtool Adapter v{fw} ready.")
            print("[*] Probing target radio on 3-wire keyload interface...")
            link = P25ThreeWireLink(adapter)
            
            connected = link.init_session(timeout=args.timeout)
            if connected:
                print("[+] Target Radio Detected! Radio responded to READY_REQ (General Mode 0xD0).")
                link.end_session()
                print("[+] Keyloading session closed cleanly.")
            else:
                print("[-] No response from radio.")
                print("    Check: 1) Radio is powered ON.")
                print("           2) Keyload cable is firmly connected to radio side connector.")
                print("           3) Radio has hardware crypto module (UCM) or ADP firmware enabled.")
    except Exception as e:
        print(f"[-] Probe Error: {e}")
        sys.exit(1)

def cmd_kvl_load(args):
    port = _get_kvl_port(args.port)
    
    # Collect keys to load
    keys_to_load = []
    if args.codeplug:
        cp = JsonParser.load_file(args.codeplug)
        if not cp.encryption_keys:
            print(f"[-] No encryption keys defined in codeplug: {args.codeplug}")
            sys.exit(1)
        if args.key_id:
            matching = [k for k in cp.encryption_keys if k.key_id == args.key_id]
            if not matching:
                print(f"[-] Key ID {args.key_id} not found in {args.codeplug}")
                sys.exit(1)
            keys_to_load = matching
        else:
            keys_to_load = cp.encryption_keys
    else:
        if not args.key_id or not args.key:
            print("[-] Specify either a codeplug file or provide --key-id and --key hex data.")
            sys.exit(1)
        keys_to_load = [
            EncryptionKey(
                key_id=args.key_id,
                name=args.name or f"KEY_{args.key_id}",
                algorithm=args.alg or "ADP",
                key_data=args.key
            )
        ]

    print(f"[*] Preparing to load {len(keys_to_load)} key(s) into radio via KVL ({port})...")
    for k in keys_to_load:
        print(f"  -> Key ID {k.key_id:d} ({k.name}): {k.algorithm} [{k.key_data[:4]}****]")

    try:
        with KfdtoolAdapter(port) as adapter:
            link = P25ThreeWireLink(adapter)
            print("[*] Initiating 3-wire keyloading session...")
            if not link.init_session(timeout=2.0):
                print("[-] Radio did not respond to session initialization.")
                print("    Ensure radio is powered on and keyload cable is connected.")
                sys.exit(1)
            
            print("[+] Radio entered KEYLOAD mode.")
            success_count = 0
            for k in keys_to_load:
                alg = P25Algorithm.from_str(k.algorithm)
                kmm = link.build_modify_key_command(
                    key_id=k.key_id,
                    algorithm=alg,
                    key_data_hex=k.key_data,
                    keyset_id=args.keyset
                )
                frame = link.build_kmm_frame(kmm)
                print(f"[*] Sending ModifyKeyCommand for Key ID {k.key_id} ({len(frame)} bytes)...")
                if link.send_frame(frame):
                    print(f"  [ok] Key ID {k.key_id} ({k.name}) loaded successfully.")
                    success_count += 1
                else:
                    print(f"  [fail] Failed to send Key ID {k.key_id}.")

            link.end_session()
            print(f"[+] Keyload completed. {success_count}/{len(keys_to_load)} key(s) transferred.")
    except Exception as e:
        print(f"[-] KVL Keyload Error: {e}")
        sys.exit(1)

def cmd_kvl_zeroize(args):
    port = _get_kvl_port(args.port)
    print(f"[!] WARNING: You are about to ZEROIZE all encryption keys on the connected radio.")
    if not args.force:
        confirm = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
        if confirm != "y":
            print("[-] Zeroize aborted by user.")
            return

    try:
        with KfdtoolAdapter(port) as adapter:
            link = P25ThreeWireLink(adapter)
            print("[*] Initiating 3-wire session...")
            if not link.init_session(timeout=2.0):
                print("[-] Radio did not respond to session init.")
                sys.exit(1)

            print("[*] Sending P25 ZeroizeCommand...")
            kmm = link.build_zeroize_command()
            frame = link.build_kmm_frame(kmm)
            if link.send_frame(frame):
                print("[+] ZEROIZE command transmitted successfully. All keys wiped.")
            else:
                print("[-] Failed to transmit zeroize frame.")

            link.end_session()
    except Exception as e:
        print(f"[-] Zeroize Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="OpenAstro: Open Source Motorola ASTRO 25 Codeplug Manager & KVL Toolkit")
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

    # validate
    p_val = subparsers.add_parser("validate", help="Validate codeplug for RF safety, bandsplit limits & rules")
    p_val.add_argument("input", help="Input JSON codeplug file to validate")
    p_val.set_defaults(func=cmd_validate)

    # flashcode
    p_fc = subparsers.add_parser("flashcode", help="Decode Motorola ASTRO 25 flashcode features")
    p_fc.add_argument("flashcode", help="12-digit flashcode string or path to codeplug JSON file")
    p_fc.set_defaults(func=cmd_flashcode)

    # ports
    p_ports = subparsers.add_parser("ports", help="List detected USB programming cables & KVL devices")
    p_ports.set_defaults(func=cmd_ports)

    # probe radio
    p_probe = subparsers.add_parser("probe", help="Probe radio connection over serial programming cable")
    p_probe.add_argument("--port", help="Serial COM port (auto-detected if omitted)")
    p_probe.add_argument("--baud", type=int, default=19200, help="Baud rate (default: 19200)")
    p_probe.add_argument("--timeout", type=float, default=1.5, help="Response timeout in seconds")
    p_probe.set_defaults(func=cmd_probe)

    # read radio
    p_read = subparsers.add_parser("read", help="Read codeplug directly from connected radio over serial")
    p_read.add_argument("-o", "--output", default="radio_codeplug.json", help="Output JSON codeplug file")
    p_read.add_argument("--port", help="Serial COM port (auto-detected if omitted)")
    p_read.add_argument("--baud", type=int, default=19200, help="Baud rate (default: 19200)")
    p_read.add_argument("--timeout", type=float, default=2.0, help="Response timeout in seconds")
    p_read.set_defaults(func=cmd_read)

    # write radio
    p_write = subparsers.add_parser("write", help="Write/flash codeplug to connected radio over serial")
    p_write.add_argument("input", help="Input JSON codeplug file to flash")
    p_write.add_argument("--port", help="Serial COM port (auto-detected if omitted)")
    p_write.add_argument("--baud", type=int, default=19200, help="Baud rate (default: 19200)")
    p_write.add_argument("--timeout", type=float, default=2.0, help="Response timeout in seconds")
    p_write.add_argument("--force", "-f", action="store_true", help="Force write even if safety checks flag warnings")
    p_write.add_argument("--wait", "-w", action="store_true", help="Wait for radio to be power-cycled before flashing")
    p_write.set_defaults(func=cmd_write)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch modern OpenAstro Web GUI in local browser")
    p_gui.add_argument("--port", type=int, default=8080, help="HTTP server port (default: 8080)")
    p_gui.add_argument("--host", default="127.0.0.1", help="HTTP server host (default: 127.0.0.1)")
    p_gui.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    p_gui.set_defaults(func=cmd_gui)

    # cpg-info
    p_cpg_info = subparsers.add_parser("cpg-info", help="Inspect and display Motorola ASTRO 25 binary codeplug (.cpg) metadata")
    p_cpg_info.add_argument("cpg", help="Path to input .cpg file")
    p_cpg_info.set_defaults(func=cmd_cpg_info)

    # cpg-dump
    p_cpg_dump = subparsers.add_parser("cpg-dump", help="Extract and decrypt all relational streams from a .cpg codeplug to disk")
    p_cpg_dump.add_argument("cpg", help="Path to input .cpg file")
    p_cpg_dump.add_argument("-o", "--output", default="cpg_dump", help="Destination folder (default: cpg_dump)")
    p_cpg_dump.set_defaults(func=cmd_cpg_dump)

    # cpg-search
    p_cpg_search = subparsers.add_parser("cpg-search", help="Search decrypted streams in a .cpg file for text or hex patterns")
    p_cpg_search.add_argument("cpg", help="Path to input .cpg file")
    p_cpg_search.add_argument("query", help="Text string or hex sequence to search for")
    p_cpg_search.add_argument("--hex", action="store_true", help="Treat query as hex bytes (e.g. 01020304)")
    p_cpg_search.set_defaults(func=cmd_cpg_search)

    # cpg-patch
    p_cpg_patch = subparsers.add_parser("cpg-patch", help="Patch an individual stream within an ASTRO 25 .cpg codeplug")
    p_cpg_patch.add_argument("cpg", help="Path to input .cpg file")
    p_cpg_patch.add_argument("-s", "--stream", required=True, help="Target stream name (e.g. Strm_1)")
    p_cpg_patch.add_argument("-d", "--data", required=True, help="Path to file containing replacement stream bytes")
    p_cpg_patch.add_argument("-o", "--output", required=True, help="Path to output .cpg file")
    p_cpg_patch.set_defaults(func=cmd_cpg_patch)

    # kvl parent parser
    p_kvl = subparsers.add_parser("kvl", help="Key Variable Loader (KVL) operations via KFDtool adapter")
    kvl_subs = p_kvl.add_subparsers(dest="kvl_command", required=True)

    # kvl info
    p_k_info = kvl_subs.add_parser("info", help="Display KFDtool KVL hardware and firmware status")
    p_k_info.add_argument("--port", help="Serial COM port for KFDtool (auto-detected if omitted)")
    p_k_info.set_defaults(func=cmd_kvl_info)

    # kvl probe
    p_k_probe = kvl_subs.add_parser("probe", help="Probe radio connection over 3-wire keyload line")
    p_k_probe.add_argument("--port", help="Serial COM port for KFDtool")
    p_k_probe.add_argument("--timeout", type=float, default=2.0, help="Response timeout in seconds")
    p_k_probe.set_defaults(func=cmd_kvl_probe)

    # kvl load
    p_k_load = kvl_subs.add_parser("load", help="Load encryption key into radio via KVL")
    p_k_load.add_argument("codeplug", nargs="?", help="Optional codeplug JSON file to load keys from")
    p_k_load.add_argument("--port", help="Serial COM port for KFDtool")
    p_k_load.add_argument("--key-id", type=int, help="Target Key ID (1-255)")
    p_k_load.add_argument("--key", help="Key data in hex (e.g., A1B2C3D4E5 for ADP, 64 hex chars for AES-256)")
    p_k_load.add_argument("--alg", default="ADP", help="Algorithm: ADP, AES-256, DES-OFB, DES-XL")
    p_k_load.add_argument("--name", help="Key label / name")
    p_k_load.add_argument("--keyset", type=int, default=1, help="Keyset ID (default: 1)")
    p_k_load.set_defaults(func=cmd_kvl_load)

    # kvl zeroize
    p_k_zero = kvl_subs.add_parser("zeroize", help="Zeroize all encryption keys on target radio")
    p_k_zero.add_argument("--port", help="Serial COM port for KFDtool")
    p_k_zero.add_argument("--force", "-f", action="store_true", help="Force zeroize without interactive confirmation")
    p_k_zero.set_defaults(func=cmd_kvl_zeroize)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
