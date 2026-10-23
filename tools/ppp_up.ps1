<#
Bring up the PPP link to the radio on Windows, so the read-only RCMP client
(python -m open_astro.cli rcmp-read) can reach it at 192.168.128.1:8002.

This dials a dial-up (RAS) entry bound to the radio's own modem
("Motorola 1500 and 2500 Series Radio" on COM7) -- the same mechanism CPS uses
(the radio answers a PPP CLIENT -> CLIENTSERVER handshake). No credentials: the
captured sessions used no PAP/CHAP.

CPS must NOT be running (it holds COM7). Hang up afterward with ppp_down.ps1.

Future (Fedora): the transport layer is OS-agnostic; bring PPP up there with
pppd instead (see docs/RCMP_WIRE_PROTOCOL.md / tools/ppp_probe.py), then the
same rcmp-read command works.

Usage:
    powershell -ExecutionPolicy Bypass -File tools\ppp_up.ps1
#>
$ErrorActionPreference = 'Stop'
$entry  = 'OpenAstroRadio'
$modem  = 'Motorola 1500 and 2500 Series Radio'

# The dial-up entry must exist in the SYSTEM phonebook (rasdial /PHONEBOOK with a
# hand-written .pbk returns 623 on Win11). Create it once via the GUI:
#   Control Panel > Network and Sharing Center > "Set up a new connection or
#   network" > "Connect to the Internet" > "Dial-up" > choose the
#   "Motorola 1500 and 2500 Series Radio" modem > phone number: 0 >
#   connection name: OpenAstroRadio > user/password blank > Create.
# Then this script just dials that entry by name.
$pbkUser = "$env:APPDATA\Microsoft\Network\Connections\Pbk\rasphone.pbk"
$pbkAll  = "$env:PROGRAMDATA\Microsoft\Network\Connections\Pbk\rasphone.pbk"
$haveEntry = $false
foreach ($pb in @($pbkUser, $pbkAll)) {
    if ((Test-Path $pb) -and (Select-String -Path $pb -SimpleMatch "[$entry]" -Quiet)) {
        $haveEntry = $true; break
    }
}
if (-not $haveEntry) {
    Write-Host "Dial-up entry '$entry' not found in the system phonebook."
    Write-Host "Create it once (GUI), then re-run:"
    Write-Host "  Control Panel > Network and Sharing Center > Set up a new connection"
    Write-Host "  > Connect to the Internet > Dial-up > modem '$modem'"
    Write-Host "  > phone number 0 > name '$entry' > user/pass blank."
    Write-Host "Opening the connection wizard now..."
    Start-Process control.exe -ArgumentList 'netconnections'
    exit 1
}

Write-Host "Dialing system entry '$entry' over '$modem' (COM7)..."
$out = (rasdial $entry) 2>&1 | Out-String
Write-Host $out
if ($out -notmatch 'Successfully connected|Connected|already connected') {
    Write-Host "First attempt did not confirm. Retrying with dummy credentials..."
    $out = (rasdial $entry guest "") 2>&1 | Out-String
    Write-Host $out
}

Start-Sleep -Milliseconds 800
Write-Host "`n=== PPP interface(s) ==="
Get-NetIPAddress -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '192.168.128.*' } |
    Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize

Write-Host "=== reachability test: 192.168.128.1 ==="
if (Test-Connection -ComputerName 192.168.128.1 -Count 2 -Quiet -ErrorAction SilentlyContinue) {
    Write-Host "radio reachable. Now run:  python -m open_astro.cli rcmp-read --object 0x0047 --length 16"
} else {
    Write-Host "radio NOT reachable yet. Check that CPS is closed and the cable is on COM7, then re-run."
}
