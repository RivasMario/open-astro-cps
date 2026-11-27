"""Offline CLI tests for `open-astro write` (safe-by-default 0x80 writer)."""
import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("olefile")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPG = os.path.join(REPO, "backups", "205CFR2930.cpg")


def _run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(REPO, "src")
    return subprocess.run(
        [sys.executable, "-m", "open_astro.cli", *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_write_dry_run_json_verifies_framing_and_0x82_firewall():
    res = _run_cli("rcmp-write", CPG, "--json")
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["dry_run"] is True
    assert data["partition"] == "0x80"
    assert data["control_framing_ok"] is True
    assert data["tuning_0x82_blocked"] is True
    assert data["write_objects"] > 100
    assert data["opcodes"].get("0106") == 2  # open + commit
    assert data["opcodes"].get("0103") == 2  # prepare x2


def test_write_confirm_refuses_without_socket():
    res = _run_cli("rcmp-write", CPG, "--confirm", "--expect-serial", "205CFR2930")
    assert res.returncode == 2
    assert "--socket" in res.stderr


def test_write_confirm_refuses_without_expect_serial():
    res = _run_cli("rcmp-write", CPG, "--confirm", "--socket")
    assert res.returncode == 2
    assert "--expect-serial" in res.stderr


def test_write_missing_cpg_exits_nonzero():
    res = _run_cli("rcmp-write", "backups/does_not_exist_999.cpg")
    assert res.returncode == 2
    assert "not found" in res.stderr.lower()
