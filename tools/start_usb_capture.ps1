$ErrorActionPreference = 'Stop'
$usbpcap = 'C:\Program Files\USBPcap\USBPcapCMD.exe'
$iface   = '\\.\USBPcap1'
$repo    = Split-Path $PSScriptRoot -Parent
$outdir  = Join-Path $repo 'captures'
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
$pcap    = Join-Path $outdir "live_depot_capture.pcap"

if (Test-Path $pcap) { Remove-Item -Force $pcap }

# Stop any lingering USBPcapCMD
Get-Process -Name 'USBPcapCMD' -ErrorAction SilentlyContinue | Stop-Process -Force

$args = @('-d', $iface, '-o', $pcap, '--capture-from-all-devices', '--capture-from-new-devices')
$proc = Start-Process -FilePath $usbpcap -ArgumentList $args -PassThru

Set-Content -Path (Join-Path $repo 'scratch/capture_pid.txt') -Value $proc.Id
Write-Host "[+] USB capture started (PID: $($proc.Id)) -> $pcap"
