$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$pidFile = Join-Path $repo 'scratch/capture_pid.txt'
$pcap = Join-Path $repo 'captures/live_depot_capture.pcap'

if (Test-Path $pidFile) {
    $procId = Get-Content $pidFile
    Get-Process -Id $procId -ErrorAction SilentlyContinue | Stop-Process -Force
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}

# Also ensure any USBPcapCMD is stopped
Get-Process -Name 'USBPcapCMD' -ErrorAction SilentlyContinue | Stop-Process -Force

Start-Sleep -Milliseconds 500

if (Test-Path $pcap) {
    $bytes = (Get-Item $pcap).Length
    Write-Host "[+] USB capture stopped. Saved $pcap ($bytes bytes)."
} else {
    Write-Host "[-] Capture file not found."
}
