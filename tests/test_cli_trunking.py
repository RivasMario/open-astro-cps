"""Tests for open-astro trunking CLI commands."""
import json
from pathlib import Path
import pytest
from unittest.mock import patch
import io

from open_astro.cli import main

BACKUP_RADIO1 = Path(__file__).resolve().parents[1] / "backups" / "Radio1_205CMB2249_codeplug.cpg"


def test_cli_trunking_dump_table(capsys):
    """Test open-astro trunking-dump human-readable table output."""
    if not BACKUP_RADIO1.exists():
        pytest.skip("backups/Radio1_205CMB2249_codeplug.cpg not present")

    test_args = ["open-astro", "trunking-dump", str(BACKUP_RADIO1)]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr().out
    assert "P25 / Type II Trunking Systems (15 found" in captured
    assert "SEATTLE" in captured
    assert "EPSCA" in captured
    assert "860.4375 MHz" in captured
    assert "Master Fleet Talkgroup List (28 entries)" in captured
    assert "1188" in captured


def test_cli_trunking_dump_json(capsys):
    """Test open-astro trunking-dump --json structured output."""
    if not BACKUP_RADIO1.exists():
        pytest.skip("backups/Radio1_205CMB2249_codeplug.cpg not present")

    test_args = ["open-astro", "trunking-dump", str(BACKUP_RADIO1), "--json"]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "systems" in data
    assert len(data["systems"]) == 15
    assert data["systems"][0]["name"] == "SEATTLE"
    assert "master_talkgroups" in data
    assert len(data["master_talkgroups"]) == 28
