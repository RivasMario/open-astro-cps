<#
Hang up the PPP link brought up by ppp_up.ps1.

Usage:
    powershell -ExecutionPolicy Bypass -File tools\ppp_down.ps1
#>
$entry = 'OpenAstroRadio'
$out = (rasdial $entry /DISCONNECT) 2>&1 | Out-String
Write-Host $out
Write-Host "Disconnected '$entry' (if it was up). COM7 is free for CPS again."
