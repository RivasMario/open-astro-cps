#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Creates a Desktop shortcut that launches the Open Astro Rust CLI.
.DESCRIPTION
    This script locates the compiled `open_astro_cli` binary (Release build) under
    `rust/open_astro_cli/target/release/` and creates a Windows shortcut (`.lnk`)
    on the current user's Desktop. The shortcut runs the binary with optional
    arguments (default "flash").
.EXAMPLE
    .\scripts\create_shortcut.ps1 -Argument "flash"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Argument = "flash"
)

# Resolve the path to the binary (assumes this script lives in the repo root).
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$binaryPath = Join-Path $repoRoot "rust\open_astro_cli\target\release\open_astro_cli.exe"

if (-not (Test-Path $binaryPath)) {
    Write-Error "Compiled binary not found at $binaryPath. Please run 'cargo build --release' first."
    exit 1
}

# Get the current user's Desktop folder.
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Open Astro CLI.lnk"

# Create the COM object for a shortcut.
$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $binaryPath
$shortcut.Arguments = $Argument
$shortcut.WorkingDirectory = Split-Path $binaryPath
$shortcut.WindowStyle = 1   # Normal window
$shortcut.Description = "Open Astro CLI – Flash XTS radios or read code‑plug"
# Optional: set an icon (use the binary itself as the icon).
$shortcut.IconLocation = "$binaryPath,0"
$shortcut.Save()
Write-Host "Shortcut created at $shortcutPath"
