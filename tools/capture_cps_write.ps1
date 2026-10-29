<#
Capture the live Motorola CPS <-> radio USB session for protocol ground truth.

Passively records the USB traffic to the radio (device [27] on \\.\USBPcap1,
VID_0CAD PID_1001) while real Motorola CPS reads or writes the codeplug. CPS
holds COM7 exclusively, so we capture at the USB bus level, not the COM port.
This script only records; it never writes to the radio.

Usage (run from an elevated PowerShell -- USBPcap needs admin):
    powershell -ExecutionPolicy Bypass -File tools\capture_cps_write.ps1

It writes captures\cps_<timestamp>.pcap and keeps running until you press a
key, so the sequence is:
    1. Start this script.
    2. In CPS: open backups\407CHT0214.cpg and Write it to the radio.
    3. When CPS reports the write finished, come back here and press a key.
#>
$ErrorActionPreference = 'Stop'
$usbpcap = 'C:\Program Files\USBPcap\USBPcapCMD.exe'
$iface   = '\\.\USBPcap1'
$device  = 27          # [27] Motorola 1500 and 2500 Series Radio (re-check with --extcap-config)
$repo    = Split-Path $PSScriptRoot -Parent
$outdir  = Join-Path $repo 'captures'
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
$stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'
$pcap    = Join-Path $outdir "cps_$stamp.pcap"

if (-not (Test-Path $usbpcap)) { throw "USBPcapCMD not found at $usbpcap" }

Write-Host "Capturing radio USB traffic -> $pcap"
Write-Host "Now perform the CPS write, then press a key here to stop."

# Capture the WHOLE bus. The radio re-enumerates to a new USB address when it
# switches modes (e.g. tuner vs CPS), so a --devices filter can miss it; the
# decoder filters to the radio by VID 0x0CAD afterward. --capture-from-all-devices
# is on by default on USBPcap, so no per-device argument is passed.
$args = @('-d', $iface, '-o', $pcap, '--capture-from-all-devices', '--capture-from-new-devices')
$proc = Start-Process -FilePath $usbpcap -ArgumentList $args -PassThru -NoNewWindow

try {
    [void][System.Console]::ReadKey($true)
} finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Start-Sleep -Milliseconds 300
}
$size = (Get-Item $pcap).Length
Write-Host "Stopped. Wrote $pcap ($size bytes)."
Write-Host "Decode with: python tools\decode_usb_ppp.py `"$pcap`""
