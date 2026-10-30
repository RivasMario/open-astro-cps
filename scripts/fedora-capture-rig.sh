#!/usr/bin/env bash
# =============================================================================
# fedora-capture-rig.sh -- turnkey real-CPS flashcode-write capture (x86 Linux)
#
# Brings up the Wine CPS container (docker/Dockerfile.wine-cps) with
# tools/virtual_radio.py impersonating a radio, lets you drive a Write in real
# Motorola CPS through noVNC, then validates the captured handshake + codeplug
# with tools/verify_handshake.py and tools/verify_codeplug.py.
#
# MUST run on an x86_64 Linux host (the CPS binaries are 32-bit x86). On the
# ARM64 Windows workstation this is impossible -- see
# docs/FEDORA_CAPTURE_HANDOFF.md.
#
# Prereqs: docker + docker compose v2; the extracted ASTRO25 CPS tree.
#
# Usage:
#   export CPS_HOST_DIR=~/re/ASTRO25SOFTWARE/astro25portablecpsr20.01.00   # dir holding PatPort.exe + DLLs
#   export RADIO_CODEPLUG=/workspace/backups/721CLZ0655.cpg   # optional (container path)
#   export RADIO_SERIAL=721CLZ0655                            # optional
#   export RADIO_FLASHCODE=400008-002000-0                    # optional
#   scripts/fedora-capture-rig.sh
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$REPO/docker/docker-compose.yml"
CAPDIR="$REPO/captures"

# --- preflight ---------------------------------------------------------------
arch="$(uname -m)"
if [ "$arch" != "x86_64" ]; then
    echo "ERROR: host arch is '$arch'; the CPS binaries are 32-bit x86 and this"
    echo "       rig needs an x86_64 Linux host. Aborting." >&2
    exit 2
fi
command -v docker >/dev/null || { echo "ERROR: docker not found." >&2; exit 2; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: 'docker compose' v2 not found." >&2; exit 2; }

if [ -z "${CPS_HOST_DIR:-}" ]; then
    echo "ERROR: set CPS_HOST_DIR to the extracted CPS tree (the dir under which" >&2
    echo "       PatPort.exe and NextGen10.dll live). See re_sources.json." >&2
    exit 2
fi
if ! find "$CPS_HOST_DIR" -iname PatPort.exe -print -quit | grep -q .; then
    echo "ERROR: no PatPort.exe found under CPS_HOST_DIR=$CPS_HOST_DIR" >&2
    exit 2
fi
export CPS_HOST_DIR

echo "==> Host x86_64 OK, docker OK, PatPort.exe found under CPS_HOST_DIR."
before="$(ls -1 "$CAPDIR"/rcmp_trace_*.jsonl 2>/dev/null | wc -l)"

# --- bring up the wine rig ---------------------------------------------------
echo "==> Building + starting the Wine CPS capture rig (profile: wine)..."
docker compose -f "$COMPOSE" --profile wine up --build -d

cat <<EOF

======================================================================
  RIG RUNNING
  1. Open:  http://127.0.0.1:6080/vnc.html
  2. In ASTRO 25 CPS (PatPort), connect to the (virtual) radio and run
     Write Device / Flashport -> Upgrade, then Read Device.
     The virtual radio answers identity + the 0x0107 handshake, so CPS
     believes a real radio is attached.
  3. When CPS reports done, come back here and press ENTER to verify.
======================================================================
EOF
read -r _

# --- locate the capture this run produced ------------------------------------
cap="$(ls -1t "$CAPDIR"/rcmp_trace_*.jsonl 2>/dev/null | head -1 || true)"
after="$(ls -1 "$CAPDIR"/rcmp_trace_*.jsonl 2>/dev/null | wc -l)"
if [ -z "$cap" ] || [ "$after" -le "$before" ]; then
    echo "WARNING: no new rcmp_trace_*.jsonl appeared in $CAPDIR." >&2
    echo "         Did CPS actually talk to the virtual radio? Check the container logs:" >&2
    echo "         docker compose -f $COMPOSE --profile wine logs" >&2
    exit 1
fi
echo "==> Capture: $cap"

# --- validate ----------------------------------------------------------------
echo "==> Verifying 0x0107 handshake..."
python3 "$REPO/tools/verify_handshake.py" "$cap" || true
echo "==> Verifying Partition 0x80 codeplug read vs reference .cpg..."
ref="${RADIO_CODEPLUG_HOST:-$REPO/backups/721CLZ0655.cpg}"
python3 "$REPO/tools/verify_codeplug.py" "$cap" --cpg "$ref" || true

echo
echo "==> Done. To stop the rig:  docker compose -f $COMPOSE --profile wine down"
