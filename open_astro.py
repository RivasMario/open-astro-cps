#!/usr/bin/env python3
"""
Unified Open‑Astro CLI

Usage:
    python open_astro.py flash   # Flash both XTS 2500 and XTS 5000 (captures saved)
    python open_astro.py read    # Read full code‑plug (partition 0x80) from virtual radio
    python open_astro.py diff <capture1.jsonl> <capture2.jsonl>

Options can be extended: e.g. --host, --port, --model to target real hardware.
The script simply wraps the existing helper scripts:
* flash_all_radios.py
* sim_codeplug.py
* diff_captures.py
"""
import argparse, subprocess, sys, pathlib, os

BASE = pathlib.Path(__file__).resolve().parent

# Force UTF-8 in child scripts so emoji/arrow output never hits a cp1252
# console and raises UnicodeEncodeError.
_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

def run_flash(args):
    script = BASE / "tools" / "flash_all_radios.py"
    subprocess.run([sys.executable, str(script)], check=True, env=_ENV)

def run_read(args):
    script = BASE / "tools" / "sim_codeplug.py"
    subprocess.run([sys.executable, str(script)], check=True, env=_ENV)

def run_diff(args):
    script = BASE / "tools" / "diff_captures.py"
    subprocess.run([sys.executable, str(script), args.file1, args.file2], check=True, env=_ENV)

def main():
    parser = argparse.ArgumentParser(prog="open_astro", description="Unified Open‑Astro CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    flash_parser = subparsers.add_parser("flash", help="Flash both XTS 2500 and XTS 5000 to kitchen‑sink flashcode.")
    flash_parser.set_defaults(func=run_flash)

    read_parser = subparsers.add_parser("read", help="Read the full code‑plug (partition 0x80) from the virtual radio.")
    read_parser.set_defaults(func=run_read)

    diff_parser = subparsers.add_parser("diff", help="Diff two RCMP JSONL capture files.")
    diff_parser.add_argument("file1", help="First capture file (JSONL)")
    diff_parser.add_argument("file2", help="Second capture file (JSONL)")
    diff_parser.set_defaults(func=run_diff)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
