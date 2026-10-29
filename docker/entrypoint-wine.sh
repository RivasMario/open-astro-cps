#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export WINEARCH=win32
export WINEPREFIX="${WINEPREFIX:-/wine}"
export WINEDEBUG="${WINEDEBUG:--all}"

CODEPLUG="${RADIO_CODEPLUG:-/workspace/backups/721CLZ0655.cpg}"
SERIAL="${RADIO_SERIAL:-721CLZ0655}"
FLASHCODE="${RADIO_FLASHCODE:-400008-002000-0}"
CAPTURE_DIR="${CAPTURE_DIR:-/workspace/captures}"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$CAPTURE_DIR"

echo "[*] Configuring virtual radio IP 192.168.128.1 & 192.168.128.2 on loopback..."
ip addr add 192.168.128.1/24 dev lo 2>/dev/null || true
ip addr add 192.168.128.2/24 dev lo 2>/dev/null || true
grep -q "192.168.128.1" /etc/hosts || echo "192.168.128.1 radio" >> /etc/hosts

echo "[*] Starting virtual COM1 <-> PTY bridge (socat) for serial PPP fallback..."
mkdir -p "$WINEPREFIX/dosdevices"
socat -d -d pty,raw,echo=0,link=/tmp/ttyVRadio0 pty,raw,echo=0,link="$WINEPREFIX/dosdevices/com1" &
SOCAT_PID=$!
sleep 1

echo "[*] Starting tcpdump on port 8002 -> $CAPTURE_DIR/docker_tcp_${STAMP}.pcap ..."
tcpdump -i any -U -w "$CAPTURE_DIR/docker_tcp_${STAMP}.pcap" "tcp port 8002" >/dev/null 2>&1 &
TCPDUMP_PID=$!

echo "[*] Starting Virtual ASTRO 25 Radio Server ($CODEPLUG, serial=$SERIAL, fc=$FLASHCODE)..."
python3 /workspace/tools/virtual_radio.py "$CODEPLUG" \
    --host 0.0.0.0 \
    --port 8002 \
    --serial "$SERIAL" \
    --flashcode "$FLASHCODE" \
    --ppp-serial /tmp/ttyVRadio0 \
    --challenge-security \
    --capture-jsonl "$CAPTURE_DIR/rcmp_trace_${STAMP}.jsonl" \
    --capture-pcap "$CAPTURE_DIR/rcmp_synth_${STAMP}.pcap" \
    --verbose &
VRADIO_PID=$!

echo "[*] Starting Xvfb ($DISPLAY), Fluxbox, x11vnc (:5900), and noVNC (:6080)..."
Xvfb "$DISPLAY" -screen 0 1280x800x24 >/dev/null 2>&1 &
sleep 1
fluxbox >/dev/null 2>&1 &
x11vnc -display "$DISPLAY" -forever -nopw -shared -rfbport 5900 >/dev/null 2>&1 &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/dev/null 2>&1 &

# Auto-register all Motorola ASTRO 25 CPS / Depot 32-bit COM DLLs if mounted at /cps
if [ -d "/cps" ]; then
    echo "[*] Scanning /cps for Motorola CPS DLLs to register in 32-bit Wine..."
    find /cps -iname "*.dll" | while read -r dll; do
        wine regsvr32 /s "$dll" 2>/dev/null || true
    done
    PATPORT="$(find /cps -iname "PatPort.exe" | head -n 1 || true)"
    if [ -n "$PATPORT" ]; then
        echo "[+] Found PatPort.exe: $PATPORT"
        echo "[+] Launching ASTRO 25 CPS inside noVNC (http://localhost:6080/vnc.html)..."
        wine "$PATPORT" &
    else
        echo "[!] No PatPort.exe found under /cps; open xterm at http://localhost:6080/vnc.html"
        xterm &
    fi
else
    echo "[!] Mount your ASTRO 25 CPS directory to /cps (set CPS_HOST_DIR)"
    xterm &
fi

echo "======================================================================"
echo "  OPEN-ASTRO DOCKER CAPTURE RIG READY"
echo "  - Web GUI (noVNC): http://localhost:6080/vnc.html"
echo "  - Virtual Radio:   192.168.128.1:8002 & COM1 (/tmp/ttyVRadio0)"
echo "  - JSONL Trace:     $CAPTURE_DIR/rcmp_trace_${STAMP}.jsonl"
echo "  - PCAP Capture:    $CAPTURE_DIR/docker_tcp_${STAMP}.pcap"
echo "======================================================================"

wait "$VRADIO_PID"
