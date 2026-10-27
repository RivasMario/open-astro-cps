"""
FastAPI backend for the OpenAstro Web GUI (Epic 4.4).

Every endpoint is a thin wrapper over existing OpenAstro library code. The app
is READ-ONLY / OFFLINE-COMPUTE ONLY: it decodes files on disk, computes a
FLASHcode upgrade in memory, and writes SDR export artifacts into the repo. It
NEVER opens a serial port or transmits to a radio -- radio writes live behind
the CLI replay harness and are out of scope for v1 on purpose.

Safety mirrored from the CLI (cli.cmd_flashcode_upgrade):
    * UCM/dongle hardware-gated feature bits are refused by default; a flipped
      bit alone does not enable e.g. AES without the physical module.
File-path safety:
    * every caller-supplied path is resolved and must stay inside the repo root
      (backups/, examples/, captures/, ...). A '..' escape or an absolute path
      outside the repo is rejected with a clean 400, never a filesystem read.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..models.flashcode import (
    FlashcodeDecoder,
    FLASHCODE_MATRIX,
    FEATURE_FLAGS,
    HARDWARE_GATED,
    format_flashcode,
    verify_flashcode,
    set_feature,
    feature_bits,
    software_feature_slugs,
)

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# src/open_astro/web/app.py -> parents[3] == repo root (same anchor cpg_decode
# uses for its schema lookup).
REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_EXPORT_DIR = REPO_ROOT / "exports" / "sdr"


class ApiError(Exception):
    """A clean, client-facing error. Carries an HTTP status and optional extra
    payload so endpoints never leak a stack trace as a 500."""

    def __init__(self, message: str, status: int = 400, **extra: Any):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def _resolve_in_repo(path_str: Optional[str], *, must_exist: bool = True) -> Path:
    """Resolve a caller-supplied path and confine it to the repository root.

    Relative paths are taken relative to the repo root; absolute paths are used
    as-is. Either way the fully resolved real path must live inside REPO_ROOT or
    the request is rejected (path-traversal / arbitrary-read guard)."""
    if path_str is None or not str(path_str).strip():
        raise ApiError("path is required")
    candidate = Path(str(path_str).strip())
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        resolved = candidate.resolve()
    except OSError as exc:  # pragma: no cover - defensive
        raise ApiError(f"invalid path: {path_str!r} ({exc})")
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        raise ApiError(
            f"path escapes the repository root and is not allowed: {path_str!r}",
            status=400,
            repo_root=str(REPO_ROOT),
        )
    if must_exist and not resolved.exists():
        raise ApiError(f"file not found inside repository: {path_str!r}", status=404)
    return resolved


def _feature_label(key) -> str:
    feat = FLASHCODE_MATRIX.get(key)
    return f"{feat.code} {feat.name}" if feat else f"Nibble {key[0]} bit {key[1]} (proprietary)"


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class DecodeRequest(BaseModel):
    path: str = Field(..., description="Path to a .cpg inside the repository (e.g. backups/205CFR2930.cpg)")


class FlashcodeRequest(BaseModel):
    flashcode: str = Field(..., description="Starting flashcode, e.g. 000008-002410-2")
    add: List[str] = Field(default_factory=list, description="Feature slugs to enable (see /api/flashcode/features)")
    allow_ucm: bool = Field(False, description="Permit UCM/dongle hardware-gated features (default: refuse)")


class ExportRequest(BaseModel):
    codeplug_json_path: str = Field(..., description="Path to a codeplug .json inside the repository")
    format: str = Field("both", description="dsdfme | sdrtrunk | both")
    output_dir: Optional[str] = Field(None, description="Output dir inside the repo (default: exports/sdr)")


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="OpenAstro Web GUI",
    version=__version__,
    description="Offline / read-only browser front end for the OpenAstro codeplug engine. No radio writes.",
)


@app.exception_handler(ApiError)
async def _api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    body: Dict[str, Any] = {"error": exc.message}
    body.update(exc.extra)
    return JSONResponse(status_code=exc.status, content=body)


@app.exception_handler(Exception)
async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    # Never surface a stack trace. Known input problems map to 400; everything
    # else is reported as a terse 500 message (no traceback body).
    if isinstance(exc, (ValueError, FileNotFoundError, KeyError)):
        return JSONResponse(status_code=400, content={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"error": f"internal error: {type(exc).__name__}: {exc}"},
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "version": __version__, "write_enabled": False}


@app.post("/api/decode-cpg")
def decode_cpg(req: DecodeRequest) -> Dict[str, Any]:
    """Decode a .cpg on disk into typed JSON via the existing CpgDecoder.

    Returns the serialized RadioCodeplug (same shape JsonParser emits) plus a
    conventional-personality count from CpgDecoder.personality_records()."""
    from ..parsers.cpg_decode import CpgDecoder
    from ..parsers.json_parser import JsonParser

    path = _resolve_in_repo(req.path)
    if path.suffix.lower() != ".cpg":
        raise ApiError(f"not a .cpg file: {req.path!r}")

    try:
        decoder = CpgDecoder(str(path))
    except Exception as exc:  # olefile missing / not an OLE file / corrupt
        raise ApiError(f"could not open .cpg: {exc}")

    try:
        codeplug = decoder.decode()
        personalities = decoder.personality_records()
    except Exception as exc:
        raise ApiError(f"failed to decode .cpg: {exc}")
    finally:
        try:
            decoder.close()
        except Exception:
            pass

    cp_dict = JsonParser.to_dict(codeplug)
    zone_count = len(codeplug.zones)
    channel_count = codeplug.total_channels()
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "radio_model": codeplug.radio_model,
        "bandsplit": codeplug.bandsplit,
        "serial_number": codeplug.serial_number,
        "zone_count": zone_count,
        "channel_count": channel_count,
        "personality_count": len(personalities),
        "talkgroup_count": len(codeplug.talkgroups),
        "scan_list_count": len(codeplug.scan_lists),
        "codeplug": cp_dict,
    }


@app.get("/api/flashcode/features")
def flashcode_features() -> Dict[str, Any]:
    """Expose the feature slug catalogue so the UI can render checkboxes.

    Each entry flags whether the feature is hardware-gated (UCM/dongle), which
    the UI greys out / warns on, matching the CLI's safety posture."""
    software = set(software_feature_slugs())
    features = []
    for slug, nb in FEATURE_FLAGS.items():
        features.append({
            "slug": slug,
            "nibble": nb[0],
            "bit": nb[1],
            "label": _feature_label(nb),
            "hardware_gated": nb in HARDWARE_GATED,
            "software": slug in software,
            "gate_note": HARDWARE_GATED.get(nb),
        })
    return {"features": features}


@app.post("/api/flashcode/upgrade")
def flashcode_upgrade(req: FlashcodeRequest) -> Dict[str, Any]:
    """Offline FLASHcode feature upgrade. NEVER transmits.

    Flips the requested feature bits, recomputes the verified Luhn check digit,
    and reports old/new/check-digit plus which bits are hardware-gated. UCM/
    dongle features are refused by default (allow_ucm=true to force+annotate),
    mirroring cli.cmd_flashcode_upgrade's safety behavior."""
    # 1. Resolve + validate the starting 12-nibble payload.
    payload = FlashcodeDecoder.clean_flashcode(req.flashcode)
    if len(payload) != 12:
        raise ApiError(f"could not parse a 12-nibble payload from {req.flashcode!r}")
    if any(c not in "0123456789ABCDEF" for c in payload):
        raise ApiError(
            f"{payload!r} uses the extended-alphabet flashcode format (letters beyond "
            "hex A-F); only the classic numeric/hex format is supported.",
        )

    # 2. Resolve the requested feature slugs.
    unknown = [s for s in req.add if s not in FEATURE_FLAGS]
    if unknown:
        raise ApiError(
            f"unknown feature slug(s): {unknown}. See /api/flashcode/features.",
            unknown=unknown,
        )

    requested = [(s, FEATURE_FLAGS[s]) for s in req.add]
    gated = [
        {"slug": s, "nibble": nb[0], "bit": nb[1],
         "label": _feature_label(nb), "gate_note": HARDWARE_GATED[nb]}
        for s, nb in requested if nb in HARDWARE_GATED
    ]

    # 3. Safety gate: refuse UCM/dongle features unless explicitly allowed.
    if gated and not req.allow_ucm:
        raise ApiError(
            "one or more requested features need a UCM/dongle this fleet may not "
            "have; a flashcode bit alone does NOT enable them. Re-send with "
            "allow_ucm=true to force (and annotate) them.",
            status=400,
            hardware_gated=gated,
            refused=True,
        )

    before = set(feature_bits(payload))
    old_fc = format_flashcode(payload)

    # 4. Apply the enables (offline, in memory).
    for _slug, (n, b) in requested:
        payload = set_feature(payload, n, b, True)

    after = set(feature_bits(payload))
    new_fc = format_flashcode(payload)
    added = sorted(after - before)

    gated_final = [
        {"nibble": k[0], "bit": k[1], "label": _feature_label(k),
         "gate_note": HARDWARE_GATED[k]}
        for k in sorted(after) if k in HARDWARE_GATED
    ]

    return {
        "old": old_fc,
        "new": new_fc,
        "check_digit": new_fc[-1],
        "payload": payload,
        "valid": verify_flashcode(new_fc),
        "features_enabled": [
            {"nibble": k[0], "bit": k[1], "label": _feature_label(k),
             "hardware_gated": k in HARDWARE_GATED}
            for k in added
        ],
        "hardware_gated": gated_final,
        "forced_ucm": bool(gated) and req.allow_ucm,
        "transmitted": False,
    }


@app.post("/api/export-sdr")
def export_sdr(req: ExportRequest) -> Dict[str, Any]:
    """Export a codeplug JSON to DSD-FME CSVs and/or an SDRTrunk playlist."""
    from ..parsers.json_parser import JsonParser
    from ..exporters.sdr_export import export_dsdfme, export_sdrtrunk

    src = _resolve_in_repo(req.codeplug_json_path)
    fmt = (req.format or "both").lower()
    if fmt not in ("dsdfme", "sdrtrunk", "both"):
        raise ApiError(f"format must be one of dsdfme|sdrtrunk|both, got {req.format!r}")

    if req.output_dir:
        out_dir = _resolve_in_repo(req.output_dir, must_exist=False)
    else:
        out_dir = DEFAULT_EXPORT_DIR

    try:
        codeplug = JsonParser.load_file(str(src))
    except Exception as exc:
        raise ApiError(f"could not load codeplug JSON: {exc}")

    out_dir.mkdir(parents=True, exist_ok=True)
    generated: Dict[str, str] = {}
    try:
        if fmt in ("dsdfme", "both"):
            paths = export_dsdfme(codeplug, str(out_dir))
            generated["dsdfme_channel_map"] = paths["channel_map"]
            generated["dsdfme_group"] = paths["group"]
        if fmt in ("sdrtrunk", "both"):
            generated["sdrtrunk_playlist"] = export_sdrtrunk(codeplug, str(out_dir))
    except Exception as exc:
        raise ApiError(f"export failed: {exc}")

    rel = {
        k: str(Path(v).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
        for k, v in generated.items()
    }
    return {
        "format": fmt,
        "output_dir": str(out_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "files": generated,
        "files_relative": rel,
    }


@app.get("/api/personalities")
def personalities(path: str) -> Dict[str, Any]:
    """List the decoded conventional personalities from a .cpg.

    Returns freqs, NAC, and flags (incl. simplex/duplex) for each 0x0FFB
    personality record."""
    from ..parsers.cpg_decode import CpgDecoder

    cpg = _resolve_in_repo(path)
    if cpg.suffix.lower() != ".cpg":
        raise ApiError(f"not a .cpg file: {path!r}")

    try:
        decoder = CpgDecoder(str(cpg))
    except Exception as exc:
        raise ApiError(f"could not open .cpg: {exc}")
    try:
        recs = decoder.personality_records()
    except Exception as exc:
        raise ApiError(f"failed to decode personalities: {exc}")
    finally:
        try:
            decoder.close()
        except Exception:
            pass

    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(recs):
        simplex = bool(rec.get("simplex", False))
        out.append({
            "index": i,
            "rx_frequency": rec.get("rx_frequency") or rec.get("freq_rx"),
            "tx_frequency": rec.get("tx_frequency") or rec.get("freq_tx"),
            "rx_nac": str(rec.get("rx_nac")) if rec.get("rx_nac") is not None else None,
            "tx_nac": str(rec.get("tx_nac")) if rec.get("tx_nac") is not None else None,
            "simplex": simplex,
            "duplex": not simplex,
            "voice_type": rec.get("voice_type"),
            "rx_pl_tone": rec.get("rx_pl_tone"),
            "tx_pl_tone": rec.get("tx_pl_tone"),
            "rx_dpl_code": rec.get("rx_dpl_code"),
            "tx_dpl_code": rec.get("tx_dpl_code"),
        })
    return {
        "path": str(cpg.relative_to(REPO_ROOT)).replace("\\", "/"),
        "personality_count": len(out),
        "personalities": out,
    }


# --------------------------------------------------------------------------- #
# Static single-page UI (mounted last so /api/* routes win).
# --------------------------------------------------------------------------- #
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
