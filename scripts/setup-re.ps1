# =============================================================================
# setup-re.ps1 — Reverse Engineering toolchain for open-astro-cps (Windows)
# Installs Temurin JDK 21, Ghidra 12.1+, and REA (rea-agents), and registers
# REA's MCP server at Claude Code LOCAL scope for open-astro-cps only (no
# global context bloat, no tokens/paths committed to the public repo).
# =============================================================================

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$userHome = $env:USERPROFILE

Write-Host ""
Write-Host "==> Setting up Reverse Engineering toolchain for open-astro-cps" -ForegroundColor Cyan
Write-Host "    Project dir: $repoRoot"
Write-Host ""

# 1. Install Eclipse Temurin JDK 25 via winget (required by Ghidra 12.2+)
$jdkId = "EclipseAdoptium.Temurin.25.JDK"
$jdkInstalled = winget list --id $jdkId --accept-source-agreements 2>$null | Select-String $jdkId
if ($jdkInstalled) {
    Write-Host "  [skip] Temurin JDK 25 already installed"
} else {
    Write-Host "  [install] Temurin JDK 25..."
    winget install --id $jdkId -e --silent --accept-package-agreements --accept-source-agreements *>$null
    Write-Host "  [ok] Temurin JDK 25"
}

$javaHome = Get-ChildItem "C:\Program Files\Eclipse Adoptium\jdk-25*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
if ($javaHome) {
    [Environment]::SetEnvironmentVariable("JAVA_HOME", $javaHome, "User")
    $env:JAVA_HOME = $javaHome
    Write-Host "  [ok] JAVA_HOME = $javaHome"
}

# 2. Download & Extract Ghidra 12.1.4 to ~/tools/ghidra
$toolsDir = "$userHome\tools"
New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
$existingGhidra = Get-ChildItem "$toolsDir\ghidra_*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName

if (!$existingGhidra) {
    Write-Host "  [install] Fetching latest Ghidra release from GitHub..."
    try {
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest"
        $asset = $rel.assets | Where-Object { $_.name -like "*.zip" } | Select-Object -First 1
        if ($asset) {
            $zipPath = "$env:TEMP\$($asset.name)"
            Write-Host "  [download] $($asset.name)..."
            curl.exe -fSL $asset.browser_download_url -o $zipPath
            Write-Host "  [extract] Extracting Ghidra to $toolsDir..."
            Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
            $existingGhidra = Get-ChildItem "$toolsDir\ghidra_*" -Directory | Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
        }
    } catch {
        Write-Warning "  [!] Could not auto-download Ghidra: $_"
    }
} else {
    Write-Host "  [skip] Ghidra already installed at $existingGhidra"
}

if ($existingGhidra) {
    [Environment]::SetEnvironmentVariable("GHIDRA_INSTALL_DIR", $existingGhidra, "User")
    $env:GHIDRA_INSTALL_DIR = $existingGhidra
    Write-Host "  [ok] GHIDRA_INSTALL_DIR = $existingGhidra"
}

# 3. Install rea-agents globally via npm
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
if (Get-Command rea -ErrorAction SilentlyContinue) {
    Write-Host "  [skip] rea-agents already installed"
} else {
    Write-Host "  [install] rea-agents npm package..."
    & npm install -g rea-agents@latest *>$null
    Write-Host "  [ok] rea-agents installed"
}

# 4. Register REA MCP server at Claude Code LOCAL scope for open-astro-cps only
Push-Location $repoRoot
try {
    Remove-Item Env:CLAUDE_CONFIG_DIR -ErrorAction SilentlyContinue
    & claude mcp remove --scope local rea *>$null
    $envArgs = @()
    if ($env:GHIDRA_INSTALL_DIR) { $envArgs += @("-e", "GHIDRA_INSTALL_DIR=$($env:GHIDRA_INSTALL_DIR)") }
    if ($env:JAVA_HOME)          { $envArgs += @("-e", "JAVA_HOME=$($env:JAVA_HOME)") }
    & claude mcp add --scope local rea @envArgs -- cmd.exe /d /c npx -y rea-agents@latest mcp *>$null
    Write-Host "  [ok] Registered REA MCP at local project scope ($repoRoot)"
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "==> Reverse Engineering setup complete for open-astro-cps!" -ForegroundColor Green
