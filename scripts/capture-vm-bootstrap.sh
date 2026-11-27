#!/usr/bin/env bash
# =============================================================================
# capture-vm-bootstrap.sh -- run INSIDE a fresh Debian guest (PVE VM or LXC) to
# install Docker and launch the real-CPS capture rig.
#
# Expects, bind-mounted / copied into the guest:
#   $OA_REPO  : the open-astro-cps checkout            (default /opt/open-astro-cps)
#   $CPS_HOST_DIR : the extracted ASTRO25 CPS tree root (contains PatPort.exe)
#
# Must be x86_64 (the CPS binaries are 32-bit x86). Run as root.
# =============================================================================
set -euo pipefail

OA_REPO="${OA_REPO:-/opt/open-astro-cps}"

[ "$(uname -m)" = "x86_64" ] || { echo "ERROR: guest is $(uname -m); need x86_64." >&2; exit 2; }
[ -n "${CPS_HOST_DIR:-}" ] || { echo "ERROR: set CPS_HOST_DIR (dir holding PatPort.exe)." >&2; exit 2; }
[ -d "$OA_REPO" ] || { echo "ERROR: OA_REPO=$OA_REPO not found." >&2; exit 2; }
export CPS_HOST_DIR

if ! command -v docker >/dev/null; then
    echo "==> Installing Docker (docker.io + compose plugin)..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y docker.io docker-compose-v2 python3 python3-pip
    pip3 install --break-system-packages olefile 2>/dev/null || pip3 install olefile
    systemctl enable --now docker 2>/dev/null || dockerd >/tmp/dockerd.log 2>&1 &
    sleep 3
fi
docker info >/dev/null 2>&1 || { echo "ERROR: docker daemon not running. In an LXC, create it with features nesting=1,keyctl=1." >&2; exit 2; }

echo "==> Launching capture rig from $OA_REPO ..."
exec "$OA_REPO/scripts/fedora-capture-rig.sh"
