# Desktop Shortcut Setup for Open Astro CLI

This document provides a concise, step‑by‑step guide for **installing the Rust toolchain**, **building the `open_astro_cli` binary**, and **creating a Windows Desktop shortcut** that launches the app with a single click.

---

## 1️⃣ Install Rust (rustup)
```powershell
# Download rustup‑init (the official installer)
$installer = "$env:TEMP\rustup-init.exe"
Invoke-WebRequest -Uri "https://static.rust-lang.org/rustup/archive/1.29.1/aarch64-pc-windows-msvc/rustup-init.exe" -OutFile $installer -UseBasicParsing

# Run the installer (UAC prompt will appear). The `-y` flag accepts defaults.
Start-Process -FilePath $installer -ArgumentList "-y" -Verb RunAs -Wait

# Verify installation
rustc --version
cargo  --version
```
The installer adds `%USERPROFILE%\.cargo\bin` to your `PATH`. Open a **new PowerShell window** after installation so the updated PATH is recognized.

---

## 2️⃣ Build the Open Astro CLI (Rust)
```powershell
# Navigate to the crate directory
Set-Location "C:\Users\v-mariorivas\open-astro-cps\rust\open_astro_cli"

# Build the release binary (optimised, no debug symbols)
cargo build --release

# Verify the binary exists
if (Test-Path "target\release\open_astro_cli.exe") {
    Write-Host "✅ Build succeeded – binary is at $(Resolve-Path target\release\open_astro_cli.exe)"
} else {
    Write-Error "❌ Build failed – check the Cargo output above."
}
```
The executable will be located at:
```
C:\Users\v-mariorivas\open-astro-cps\rust\open_astro_cli\target\release\open_astro_cli.exe
```

---

## 3️⃣ Create a Desktop shortcut
A helper PowerShell script (`scripts/create_shortcut.ps1`) creates a Windows shortcut (`Open Astro CLI.lnk`) on your Desktop.

```powershell
# From the repository root (or any folder that can resolve the script path)
powershell -ExecutionPolicy Bypass -File ".\scripts\create_shortcut.ps1" -Argument "flash"
```
- **`-Argument`** specifies which sub‑command the shortcut runs. Defaults to `flash`.
- You can create additional shortcuts for other commands (`read`, `diff …`) by changing the argument.

The script produces a shortcut like:
```
C:\Users\<YourUser>\Desktop\Open Astro CLI.lnk
```
Double‑click the shortcut to run the Rust CLI with the chosen argument.

---

## 4️⃣ Optional: Multiple shortcuts
```powershell
# Shortcut that reads the code‑plug
powershell -File ".\scripts\create_shortcut.ps1" -Argument "read"

# Shortcut that runs a diff between two capture files
powershell -File ".\scripts\create_shortcut.ps1" -Argument "diff captures/xts2500_kitchen_sink.jsonl captures/cps_20261023_083952_decoded.json"
```
Each command creates a separate `.lnk` file on the Desktop.

---

## 📂 Files involved
- `rust/open_astro_cli/Cargo.toml` – Cargo manifest.
- `rust/open_astro_cli/src/main.rs` – Source code for the standalone CLI.
- `scripts/create_shortcut.ps1` – PowerShell script that creates the desktop shortcut.
- This `README` (`docs/DESKTOP_SHORTCUT.md`).

---

## ✅ Ready for the next AI
All steps are documented, the Rust binary can be built on any platform, and the shortcut provides a **single‑click launch** experience.

Feel free to copy‑paste the commands into a PowerShell prompt to reproduce the whole workflow.
