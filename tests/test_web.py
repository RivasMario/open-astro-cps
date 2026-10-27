"""
Tests for the OpenAstro Web GUI (Epic 4.4).

The whole module is skipped if FastAPI is not installed (importorskip), so the
rest of the suite still passes on a machine without the web deps.
"""
import pytest

fastapi = pytest.importorskip("fastapi")  # skips the module if FastAPI absent
pytest.importorskip("httpx")  # fastapi.testclient needs httpx; skip if absent
from fastapi.testclient import TestClient  # noqa: E402

from open_astro.web.app import app  # noqa: E402

client = TestClient(app)

CPG = "backups/205CFR2930.cpg"


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]
    # v1 must advertise that writes are disabled.
    assert body["write_enabled"] is False


def test_decode_cpg_returns_zones_and_personalities():
    r = client.post("/api/decode-cpg", json={"path": CPG})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["zone_count"] > 0
    assert len(body["codeplug"]["zones"]) > 0
    assert body["personality_count"] > 0


def test_decode_cpg_rejects_non_cpg():
    r = client.post("/api/decode-cpg", json={"path": "README.md"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_flashcode_upgrade_adp():
    # 000008-002410-2 + ADP (software, no UCM) -> 000008-006410-3
    r = client.post("/api/flashcode/upgrade",
                    json={"flashcode": "000008-002410-2", "add": ["adp"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["old"] == "000008-002410-2"
    assert body["new"] == "000008-006410-3"
    assert body["check_digit"] == "3"
    assert body["valid"] is True
    assert body["transmitted"] is False


def test_flashcode_upgrade_refuses_hardware_gated():
    # aes-256 is UCM-gated: refused by default, with an annotation of what is gated.
    r = client.post("/api/flashcode/upgrade",
                    json={"flashcode": "000008-002410-2", "add": ["aes-256"]})
    assert r.status_code == 400
    body = r.json()
    assert body.get("refused") is True
    assert body.get("hardware_gated")
    assert any("aes" in g["slug"].lower() for g in body["hardware_gated"])


def test_flashcode_upgrade_allows_gated_when_forced():
    # With allow_ucm the gated feature is accepted but annotated in the result.
    r = client.post("/api/flashcode/upgrade",
                    json={"flashcode": "000008-002410-2", "add": ["aes-256"], "allow_ucm": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["forced_ucm"] is True
    assert body["hardware_gated"]  # the gated bit is reported in the final code


def test_flashcode_unknown_feature():
    r = client.post("/api/flashcode/upgrade",
                    json={"flashcode": "000008-002410-2", "add": ["not-a-real-feature"]})
    assert r.status_code == 400
    assert "unknown" in r.json()


def test_personalities_list():
    r = client.get("/api/personalities", params={"path": CPG})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["personality_count"] > 0
    first = body["personalities"][0]
    assert "rx_frequency" in first
    assert "simplex" in first and "duplex" in first
    assert first["simplex"] != first["duplex"]


def test_path_escape_relative_rejected():
    r = client.post("/api/decode-cpg", json={"path": "../../etc/passwd"})
    assert r.status_code in (400, 404)
    assert "error" in r.json()


def test_path_escape_absolute_rejected():
    # An absolute path outside the repo must be refused (not read).
    r = client.post("/api/decode-cpg", json={"path": "C:/Windows/System32/drivers/etc/hosts"})
    assert r.status_code in (400, 404)
    assert "error" in r.json()


def test_path_escape_on_personalities_rejected():
    r = client.get("/api/personalities", params={"path": "../../../etc/passwd"})
    assert r.status_code in (400, 404)
    assert "error" in r.json()


def test_static_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "OpenAstro" in r.text
