"""
Read-only AT-exchange capture logger.

Opens the radio's USB CDC-ACM serial port, sends ONLY the verified read-only
AT query commands (AT, ATI1..ATI4, AT&V -- the same set in
src/open_astro/protocol/at_interface.py), and logs every byte sent and received
to captures/ for later analysis.

Nothing here writes radio configuration, resets, or changes state. It is the
read side only. Usage:

    python tools/at_capture.py --port COM7

Writes two files to captures/:
  * at_<serial-or-port>_<timestamp>.log    human-readable transcript
  * at_<serial-or-port>_<timestamp>.jsonl  one JSON record per command
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time

# Only read-only query commands. Do not add state-changing commands here.
READ_ONLY_COMMANDS = ["AT", "ATI1", "ATI2", "ATI3", "ATI4", "AT&V"]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURES_DIR = os.path.join(REPO_ROOT, "captures")


def _hexdump(b: bytes) -> str:
    return b.hex(" ") if b else ""


def _ascii(b: bytes) -> str:
    return "".join(chr(x) if 0x20 <= x < 0x7F else "." for x in b)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only AT exchange capture")
    ap.add_argument("-p", "--port", required=True, help="Serial port (e.g. COM7 or /dev/ttyACM0)")
    ap.add_argument("-b", "--baud", type=int, default=19200, help="Baud rate (default 19200)")
    ap.add_argument("--settle", type=float, default=0.6, help="Per-command read window seconds")
    args = ap.parse_args()

    try:
        import serial  # pyserial
    except ImportError:
        print("[-] pyserial not installed: pip install pyserial", file=sys.stderr)
        return 1

    os.makedirs(CAPTURES_DIR, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    conn = serial.Serial(args.port, args.baud, timeout=1.5)
    serial_id = args.port.replace("/", "_").replace("\\", "_")

    records = []
    try:
        for cmd in READ_ONLY_COMMANDS:
            conn.reset_input_buffer()
            tx = cmd.encode("ascii") + b"\r\n"
            t0 = time.time()
            conn.write(tx)
            conn.flush()
            time.sleep(args.settle)
            rx = conn.read(conn.in_waiting or 1024)
            rec = {
                "ts": _dt.datetime.now().isoformat(timespec="milliseconds"),
                "elapsed_ms": round((time.time() - t0) * 1000, 1),
                "command": cmd,
                "tx_hex": _hexdump(tx),
                "rx_hex": _hexdump(rx),
                "rx_ascii": _ascii(rx),
            }
            records.append(rec)
            # Pull SERIAL out of AT&V so we can name the files after the radio.
            if cmd == "AT&V":
                for line in rx.decode("latin1", "replace").splitlines():
                    if line.strip().upper().startswith("SERIAL"):
                        sid = line.split(":", 1)[1].strip()
                        if sid:
                            serial_id = sid
    finally:
        conn.close()

    base = os.path.join(CAPTURES_DIR, f"at_{serial_id}_{ts}")
    with open(base + ".jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    with open(base + ".log", "w", encoding="utf-8") as f:
        f.write(f"# Read-only AT capture  port={args.port} baud={args.baud}  {ts}\n")
        for r in records:
            f.write(f"\n[{r['ts']}] >>> {r['command']}  ({r['elapsed_ms']} ms)\n")
            f.write(f"    TX {r['tx_hex']}\n")
            f.write(f"    RX {r['rx_hex']}\n")
            f.write(f"    -- {r['rx_ascii']}\n")

    print(f"[+] Captured {len(records)} read-only AT exchanges")
    print(f"[+] {base}.log")
    print(f"[+] {base}.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
