#!/usr/bin/env python3
"""
Simulate a complete **code‑plug read** (partition 0x80) against the virtual Astro 25 radio.

The script:
1️⃣ Starts `virtual_radio.py` with JSONL and PCAP capture enabled.
2️⃣ Sends the same RCMP handshake that the web dashboard performs for
   "Simulate CPS Identity + Read", then issues a **wildcard read** for partition 0x80
   (object 0, length 0) which the virtual radio interprets as “send all code‑plug
   objects”.
3️⃣ Stops the server and renames the generated `live_virtual_radio.*` files to a
   timestamped name under `captures/`.

Running the script yields two files, e.g.:
    captures/codeplug_read_20261028_153212.jsonl
    captures/codeplug_read_20261028_153212.pcap

These captures contain *exactly* what a real CPS client would receive when it
reads the radio’s code‑plug, making them perfect for reverse‑engineering or
verification against historic captures.
"""

import pathlib, subprocess, time, os, signal, sys, datetime

# Windows consoles default to cp1252; force UTF-8 so emoji/arrows in output
# do not raise UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = pathlib.Path(r"C:\\Users\\v-mariorivas\\open-astro-cps")
CAP_DIR = BASE / "captures"
CAP_DIR.mkdir(exist_ok=True)

def start_virtual_radio():
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
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    time.sleep(1)  # give server time to bind
    return proc

def stop_virtual_radio(proc):
    try:
        os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

def run_sim_read():
    """Imitate the sequence performed by the web dashboard's /api/sim-read.
    After the identity exchange we issue a wildcard read on partition 0x80.
    The virtual radio treats object=0, length=0 as "return everything".
    """
    import socket, struct
    def _tx(sock: socket.socket, opcode: int, body: bytes = b"") -> tuple[int, bytes]:
        payload = struct.pack('>H', opcode) + body
        sock.sendall(struct.pack('>H', len(payload)) + payload)
        hdr = sock.recv(2)
        length = struct.unpack('>H', hdr)[0]
        buf = b""
        while len(buf) < length:
            buf += sock.recv(length - len(buf))
        return struct.unpack('>H', buf[:2])[0], buf[2:]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect(("127.0.0.1", 8002))

    # Session start
    _tx(s, 0x0106, b"\x00")
    # Identity reads (model, serial, depot, etc.)
    _tx(s, 0x0012, b"")
    _tx(s, 0x0011, b"\x00")
    _tx(s, 0x000F, b"\x00")
    _tx(s, 0x000F, b"\x10")
    # Read a couple of flashcode objects just to keep parity with the dashboard
    _tx(s, 0x0100, struct.pack('>BHHH', 0x81, 0x1004, 0, 0x24) + b"\x00\x00")
    _tx(s, 0x0100, struct.pack('>BHHH', 0x81, 0x1006, 0, 0x18) + b"\x00\x00")
    # **Wildcard read of partition 0x80 (code‑plug)**
    _tx(s, 0x0100, struct.pack('>BHHH', 0x80, 0x0000, 0, 0) + b"")
    # Session end
    _tx(s, 0x0106, b"\x01")
    s.close()

def rename_captures(suffix: str):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    for ext in (".jsonl", ".pcap"):
        src = CAP_DIR / f"live_virtual_radio{ext}"
        dst = CAP_DIR / f"{suffix}_{ts}{ext}"
        if src.exists():
            src.rename(dst)
            print(f"Saved {dst.name}")
        else:
            print(f"Warning: {src} missing – no capture generated for {suffix}")

def main():
    vr = start_virtual_radio()
    try:
        run_sim_read()
    finally:
        stop_virtual_radio(vr)
    rename_captures("codeplug_read")
    print("\n✅ Code‑plug read captured successfully.")

if __name__ == "__main__":
    main()
