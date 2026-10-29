"""Tests for open-astro make-nas CLI command."""
import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch

from open_astro.cli import main
from open_astro.parsers.json_parser import JsonParser

BACKUP_RADIO1 = Path(__file__).resolve().parents[1] / "backups" / "Radio1_205CMB2249_codeplug.cpg"


def test_cli_make_nas_default_stdout(capsys, tmp_path):
    """Test open-astro make-nas default human-readable output and codeplug output."""
    out_json = tmp_path / "test_nas.json"
    test_args = ["open-astro", "make-nas", "-o", str(out_json)]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr().out
    assert "Non-Affiliation Scan (NAS) Configuration" in captured
    assert "Parked TX Freq  : 0.0000 MHz (STRICT 0.0)" in captured
    assert "Inhibit Immunity: ACTIVE (No ISW affiliation emitted)" in captured
    assert "Zero RF Emission: ENFORCED (Passive DSP monitoring)" in captured
    assert out_json.exists()

    cp = JsonParser.load_file(str(out_json))
    assert len(cp.zones) == 1
    assert cp.zones[0].channels[0].name == "NAS PARK"
    assert cp.zones[0].channels[0].tx_frequency == 0.0
    assert cp.zones[0].channels[0].rx_only is True


def test_cli_make_nas_json(capsys, tmp_path):
    """Test open-astro make-nas --json output."""
    out_json = tmp_path / "test_nas.json"
    test_args = [
        "open-astro",
        "make-nas",
        "--tgid", "2501",
        "--tg-name", "TAC 1",
        "--system-name", "STATEWIDE",
        "--json",
        "-o", str(out_json),
    ]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["trunking_system"]["system_name"] == "STATEWIDE"
    assert data["talkgroups"][0]["tgid"] == 2501
    assert data["park_channel"]["tx_frequency_mhz"] == 0.0
    assert data["park_channel"]["rx_only"] is True
    assert data["safety_enforced"]["zero_rf_emission"] is True


def test_cli_make_nas_emit_objects(capsys, tmp_path):
    """Test open-astro make-nas --emit-objects raw RCMP payload generation."""
    out_json = tmp_path / "test_nas.json"
    objs_json = tmp_path / "test_nas_objs.json"
    test_args = [
        "open-astro",
        "make-nas",
        "-o", str(out_json),
        "--emit-objects", str(objs_json),
    ]
    with patch("sys.argv", test_args):
        main()

    assert objs_json.exists()
    with open(objs_json, "r", encoding="utf-8") as f:
        objs = json.load(f)

    assert len(objs) > 0
    # Strict verification: Ensure NO partition 0x82 (130) objects were emitted
    for key in objs.keys():
        part, tag, inst = [int(p, 0) for p in key.split(":")]
        assert part != 0x82, f"Partition 0x82 emitted in {key}!"


def test_cli_make_nas_patch_cpg(capsys, tmp_path):
    """Test patching NAS configuration into an existing .cpg codeplug."""
    if not BACKUP_RADIO1.exists():
        pytest.skip("backups/Radio1_205CMB2249_codeplug.cpg not present")

    out_json = tmp_path / "patched_cpg.json"
    test_args = [
        "open-astro",
        "make-nas",
        "--input", str(BACKUP_RADIO1),
        "--zone", "1",
        "--channel", "1",
        "-o", str(out_json),
    ]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr().out
    assert "Successfully patched NAS into codeplug" in captured
    assert out_json.exists()

    cp = JsonParser.load_file(str(out_json))
    z1 = cp.get_zone(1)
    assert z1 is not None
    # Channel 1 is now our safe dummy park channel
    ch1 = z1.get_channel(1)
    assert ch1.name == "NAS PARK"
    assert ch1.tx_frequency == 0.0
    assert ch1.rx_only is True
