"""
Export an OpenAstro RadioCodeplug to third-party SDR monitoring tools:

  * DSD-FME  -- channel-map CSV (`-C`) + group-list CSV (`-G`)
  * SDRTrunk -- playlist XML (channels + talkgroup alias list)

Schema provenance (confirmed 2026-10-26):
  * DSD-FME CSV is POSITIONAL (no header parsing). `src/dsd_import.c`:
      - csvChanImport : col0 = channel number (long), col1 = frequency (long, Hz).
                        Row 0 is skipped as labels. Columns >1 ignored.
      - csvGroupImport: col0 = talkgroup id (long), col1 = mode (<=2 chars:
                        A/B/D/DE), col2 = group name (<=98 chars). No priority.
    We still emit a human label row (DSD-FME skips it) and frequencies in Hz.
    Ref: https://github.com/lwvmobile/dsd-fme/blob/audio_work/src/dsd_import.c
  * SDRTrunk playlist element/attribute names from the sdrtrunk XML model:
      <playlist version>, <channel name system enabled site order> with children
      <alias_list_name>/<source_configuration>/<decode_configuration>/..., and
      <alias name list group> with <id type protocol value priority>.
    Ref: https://pkg.go.dev/dynatron.me/x/stillbox/pkg/talkgroups/xport/sdrtrunk
    The decode_configuration/source_configuration `type` enum strings
    (P25_PHASE1 / NBFM / sourceConfigTuner) are best-effort for the current
    sdrtrunk; verify by saving one channel from the GUI into playlists/default.xml.
"""
import os
import xml.etree.ElementTree as ET
from typing import Dict, List


def _hz(mhz: float) -> int:
    """MHz (float) -> integer Hz, the unit both tools expect."""
    return int(round(mhz * 1_000_000))


def _is_digital(ch) -> bool:
    return (ch.voice_type or "").upper().startswith(("ASTRO", "P25", "MIXED"))


def _iter_channels(codeplug):
    """Yield (global_index, zone, channel) across every zone, 1-based index."""
    i = 0
    for z in codeplug.zones:
        for ch in z.channels:
            i += 1
            yield i, z, ch


def _slug(text: str) -> str:
    keep = "".join(c if (c.isalnum() or c in "-_") else "_" for c in (text or ""))
    return keep.strip("_") or "codeplug"


def _csv_safe(text: str) -> str:
    """DSD-FME splits on commas and reads to newline -- strip both."""
    return (text or "").replace(",", " ").replace("\n", " ").replace("\r", " ").strip()


def export_dsdfme(codeplug, out_dir: str) -> Dict[str, str]:
    """Write `<base>_dsdfme_channel_map.csv` and `<base>_dsdfme_group.csv`.

    Channel map = every channel's RX frequency in Hz (conventional scan list;
    channel numbers are arbitrary per DSD-FME). Group list = one row per unique
    P25 talkgroup, mode DE (encrypted) or A (clear), name from the channel.
    Returns {"channel_map": path, "group": path}.
    """
    os.makedirs(out_dir, exist_ok=True)
    base = _slug(codeplug.serial_number or codeplug.radio_model)

    chan_path = os.path.join(out_dir, f"{base}_dsdfme_channel_map.csv")
    with open(chan_path, "w", newline="", encoding="utf-8") as f:
        f.write("Channel,Frequency\n")  # label row (DSD-FME skips row 0)
        for idx, _zone, ch in _iter_channels(codeplug):
            f.write(f"{idx},{_hz(ch.rx_frequency)}\n")

    grp_path = os.path.join(out_dir, f"{base}_dsdfme_group.csv")
    seen = set()
    with open(grp_path, "w", newline="", encoding="utf-8") as f:
        f.write("Talkgroup,Mode,Name\n")  # label row (skipped)
        for _idx, _zone, ch in _iter_channels(codeplug):
            if not _is_digital(ch):
                continue
            tg = ch.talkgroup_id
            if tg is None or tg in seen:
                continue
            seen.add(tg)
            mode = "DE" if (ch.secure_strapping or "").lower() == "secure" else "A"
            f.write(f"{tg},{mode},{_csv_safe(ch.name)[:98]}\n")

    return {"channel_map": chan_path, "group": grp_path}


def _validate_key(key: str) -> str:
    """Normalize and validate an ADP/RC4-40 key: hex digits, even length.

    DSD-FME takes the key as a hex string on the `-K` command line (NOT in the
    CSV). ADP is RC4-40 so the key is 5 bytes / 10 hex chars, but we only
    enforce 'hex and even-length' to stay build-agnostic. Raises ValueError
    otherwise. Returns the upper-cased hex string.
    """
    cleaned = (key or "").strip().replace(" ", "")
    if cleaned[:2].lower() == "0x":
        cleaned = cleaned[2:]
    if not cleaned:
        raise ValueError("key is empty")
    if len(cleaned) % 2 != 0:
        raise ValueError(f"key must be even-length hex (got {len(cleaned)} chars): {key!r}")
    try:
        int(cleaned, 16)
    except ValueError:
        raise ValueError(f"key must be hexadecimal: {key!r}")
    return cleaned.upper()


# SDRTrunk keeps its decryption keys in the GUI encryption-key manager, not in
# the playlist XML, so there is nothing key-related to emit for it.
SDRTRUNK_KEY_NOTE = (
    "SDRTrunk: ADP/RC4 keys are NOT stored in the playlist XML. Add them in the "
    "SDRTrunk GUI under the encryption-key manager (Playlist Editor -> Aliases -> "
    "Encryption Keys), then attach the key to the matching talkgroup alias. "
    "The playlist this tool emits only carries channels and talkgroup aliases."
)


def export_dsdfme_launch(codeplug, out_dir: str, key: str = None) -> str:
    """Write `<base>_dsdfme_run.sh`: a best-effort DSD-FME launch command.

    References the channel-map CSV (`-C`) and group CSV (`-G`) that
    `export_dsdfme` writes, selects P25 Phase 1 decoding, and -- when `key` is
    supplied -- passes the ADP/RC4 key via `-K <HEX>`. The exact DSD-FME flags
    vary by build, so the invocation is emitted as a commented, editable script
    rather than something guaranteed to run verbatim. If `key` is given it must
    be hexadecimal and even-length, else ValueError is raised.

    Returns the launch-script path.
    """
    hex_key = _validate_key(key) if key is not None else None

    os.makedirs(out_dir, exist_ok=True)
    base = _slug(codeplug.serial_number or codeplug.radio_model)
    chan_csv = f"{base}_dsdfme_channel_map.csv"
    grp_csv = f"{base}_dsdfme_group.csv"

    key_flag = f" -K {hex_key}" if hex_key else ""
    cmd = (
        f"dsd-fme -fp -C {chan_csv} -G {grp_csv}{key_flag} "
        f"-i rtl:0 -o pulse -N 2> dsdfme_event.log"
    )

    lines = [
        "#!/usr/bin/env bash",
        "# DSD-FME launch command generated by OpenAstro export-sdr.",
        "#",
        "# BEST-EFFORT / EDIT BEFORE USE: exact DSD-FME flags vary by build.",
        "# Run from the directory that holds the generated CSV files, or edit the",
        "# paths below. Verify flags against your `dsd-fme -h` output.",
        "#",
        "#   -fp        P25 Phase 1 (C4FM) decoding",
        f"#   -C {chan_csv}   channel-map CSV (col0=chan, col1=freq Hz)",
        f"#   -G {grp_csv}   group-list CSV (col0=TG, col1=mode, col2=name)",
    ]
    if hex_key:
        lines.append(f"#   -K {hex_key}   ADP/RC4 key (hex) -- supplied via CLI, NOT the CSV")
    else:
        lines.append("#   (no key supplied: encrypted talkgroups will stay muted)")
    lines += [
        "#   -i rtl:0   input source (adjust for your SDR)",
        "#   -o pulse   audio output (adjust for your platform)",
        "#",
        f"# {SDRTRUNK_KEY_NOTE}",
        "",
        cmd,
        "",
    ]

    out_path = os.path.join(out_dir, f"{base}_dsdfme_run.sh")
    with open(out_path, "w", newline="\n", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def export_sdrtrunk(codeplug, out_dir: str) -> str:
    """Write `<base>_sdrtrunk_playlist.xml` (channels + talkgroup aliases).

    Each codeplug channel -> a <channel> with its RX frequency and a P25_PHASE1
    (digital) or NBFM (analog) decode_configuration. Each unique P25 talkgroup ->
    an <alias> with a TALKGROUP <id>. Returns the playlist path.
    """
    os.makedirs(out_dir, exist_ok=True)
    base = _slug(codeplug.serial_number or codeplug.radio_model)
    alias_list = base

    root = ET.Element("playlist", {"version": "4"})
    root.append(ET.Comment(
        " Generated by OpenAstro export-sdr. decode_configuration/source_configuration "
        "'type' enum values are best-effort for the current sdrtrunk; if import is "
        "rejected, save one channel from the GUI and match playlists/default.xml. "))

    # Talkgroup aliases (unique P25 TGs across the codeplug).
    seen = set()
    for _idx, _zone, ch in _iter_channels(codeplug):
        if not _is_digital(ch):
            continue
        tg = ch.talkgroup_id
        if tg is None or tg in seen:
            continue
        seen.add(tg)
        alias = ET.SubElement(root, "alias", {
            "name": ch.name or f"TG {tg}",
            "list": alias_list,
            "group": _zone.name if _zone else "",
        })
        ET.SubElement(alias, "id", {
            "type": "TALKGROUP", "protocol": "APCO25", "value": str(tg),
        })

    # Channels.
    for idx, zone, ch in _iter_channels(codeplug):
        chan = ET.SubElement(root, "channel", {
            "name": f"{zone.name}/{ch.name}" if zone else ch.name,
            "system": codeplug.radio_model or "OpenAstro",
            "enabled": "true",
            "site": zone.name if zone else "",
            "order": str(idx),
        })
        ET.SubElement(chan, "alias_list_name").text = alias_list
        src = ET.SubElement(chan, "source_configuration", {"type": "sourceConfigTuner"})
        ET.SubElement(src, "frequency").text = str(_hz(ch.rx_frequency))
        if _is_digital(ch):
            dec = ET.SubElement(chan, "decode_configuration", {"type": "P25_PHASE1"})
            ET.SubElement(dec, "modulation").text = "C4FM"
        else:
            dec = ET.SubElement(chan, "decode_configuration", {"type": "NBFM"})
            ET.SubElement(dec, "bandwidth").text = (
                "BW_12_5" if ch.channel_spacing_khz == 12.5 else "BW_25_0")

    try:
        ET.indent(root, space="  ")  # py3.9+
    except AttributeError:
        pass
    out_path = os.path.join(out_dir, f"{base}_sdrtrunk_playlist.xml")
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path
