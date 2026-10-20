#!/bin/bash
# Live-probes the real Motorola RemSB9600 COM object (RemoteProtocols01.dll,
# extracted from the real ASTRO 25 CPS R20.01.00 installer) under Wine.
#
# WHY THIS EXISTS: see docs/CPS_BINARY_ANALYSIS.md. RemoteProtocols01.dll is a
# 32-bit in-process COM server implementing IRemoteProtocol (the real SB9600
# transport). It must be driven through 32-bit cscript.exe
# (C:\windows\syswow64\cscript.exe), not the default 64-bit one -- a 32-bit DLL
# cannot load into a 64-bit host process, and that mismatch is the actual cause
# of a bare `wine cscript ...` failing with COM error 429.
#
# This script only registers the DLL and runs scripts against it. It does not,
# on its own, open any serial port or contact a radio -- but a .vbs script it
# runs can, if it calls Open()/Send(). Read any .vbs before running it here.
set -euo pipefail
cd "$(dirname "$0")"

EXTRACTED_DLL="${OPENASTRO_REMSB9600_DLL:-}"
if [ -z "$EXTRACTED_DLL" ]; then
    echo "Set OPENASTRO_REMSB9600_DLL to the path of the extracted RemoteProtocols01.dll" >&2
    echo "(extract it from the real CPS installer with unshield; see docs/CPS_BINARY_ANALYSIS.md section 0)" >&2
    exit 1
fi
if [ ! -f "$EXTRACTED_DLL" ]; then
    echo "Not found: $EXTRACTED_DLL" >&2
    exit 1
fi

WINPATH=$(WINEDEBUG=-all winepath -w "$EXTRACTED_DLL" 2>/dev/null)
WINPATH_ESC=$(printf '%s' "$WINPATH" | sed 's/\\/\\\\/g')
REG=$(mktemp --suffix=.reg)
sed "s#__WINPATH_TO_RemoteProtocols01.dll__#${WINPATH_ESC}#" remsb9600_register.reg.template > "$REG"

echo "[*] Registering RemSB9600 COM class (CLSID {BB885C92-9093-11D3-A0A4-00108302D33D})..."
WINEDEBUG=-all wine regedit /s "$REG" 2>/dev/null
rm -f "$REG"

SCRIPT="${1:-test_com.vbs}"
echo "[*] Running $SCRIPT via 32-bit cscript..."
WINSCRIPT=$(WINEDEBUG=-all winepath -w "$(pwd)/$SCRIPT" 2>/dev/null)
WINEDEBUG=-all wine "C:\\windows\\syswow64\\cscript.exe" //Nologo "$WINSCRIPT"
