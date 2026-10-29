#!/usr/bin/env python3
"""
Flash all supported Astro 25 radios to the full‑feature "kitchen‑sink" configuration,
capturing RCMP traffic (JSONL + PCAP) via the virtual radio server.

The virtual radio is started with ``--capture-jsonl`` and ``--capture-pcap`` so
that the live capture files are written automatically during the flash.
After each flash we rename those files to model‑specific names.

Dependencies:
- Python 3.12+
- ``tools/virtual_radio.py`` must be import‑able (same repo root).
"""

import pathlib, subprocess, shutil, time, os, signal, sys

BASE = pathlib.Path(r"C:\\Users\\v-mariorivas\\open-astro-cps")
CAP_DIR = BASE / "captures"
CAP_DIR.mkdir(exist_ok=True)

def start_virtual_radio():
    """Start the virtual radio daemon with capture enabled."""
    cmd = [
        sys.executable,
        str(BASE / "tools" / "virtual_radio.py"),
        "--host", "127.0.0.1",
        "--port", "8002",
        "--lock-security",
        "--challenge-security",
        "--capture-jsonl",
        "--capture-pcap",
    ]
    print("Launching virtual radio with capture ...")
    # creationflags to start a new process group (Windows only)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    # Give it a moment to bind the socket.
    time.sleep(1)
    return proc

def stop_virtual_radio(proc):
    """Terminate the virtual radio daemon cleanly."""
    print("Stopping virtual radio ...")
    try:
        os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
    except Exception as e:
        print(f"Failed to send CTRL_BREAK: {e}")
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

def run_cmd(cmd: list[str], prefix: str):
    """Run a flash script, then rename the live capture files to <prefix>.*"""
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    for ext in (".jsonl", ".pcap"):
        src = CAP_DIR / f"live_virtual_radio{ext}"
        dst = CAP_DIR / f"{prefix}{ext}"
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f" → saved {dst}")
        else:
            print(f"Warning: {src} not found – no capture for {prefix}")

# ----- Main workflow -----
vr_proc = start_virtual_radio()
try:
    # XTS 2500 (H46UCF9PW6AN)
    run_cmd([
        sys.executable,
        str(BASE / "tools" / "flash_radio_adp.py"),
        "--serial", "205CFR2930",
        "--write",
        "--host", "127.0.0.1",
        "--port", "8002",
    ], "xts2500_kitchen_sink")

    # XTS 5000 (H18UCF9PW6AN)
    run_cmd([
        sys.executable,
        str(BASE / "tools" / "flash_radio4_adp.py"),
        "--write",
        "--host", "127.0.0.1",
        "--port", "8002",
    ], "xts5000_kitchen_sink")
finally:
    stop_virtual_radio(vr_proc)

print("\nAll flashes completed. Capture files are in the 'captures' directory:")
for p in CAP_DIR.glob("xts*_kitchen_sink.*"):
    print(" •", p.name)
