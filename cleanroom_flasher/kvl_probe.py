"""
KVL / KFD adapter probe -- "get the hardware talking first".

Identifies a P25 key-fill adapter on a USB-serial port and runs its self-test.
Works for BOTH of Mario's adapters, which are the same host-side protocol:

  * Pi cable:  USB-A -> USB-C -> Pi Pico (RP2040) -> TRRS (3-wire keyfill) ->
               Hirose -> radio side connector
  * KVL clone: USB-A -> USB-C -> clone adapter   -> TRRS (3-wire keyfill) ->
               Hirose -> radio side connector

Both speak the KFDtool adapter protocol over USB CDC serial (115200 8N1). This
tool does ONLY safe, read-only adapter operations: read AP/FW/HW/model/serial
and the adapter self-test. It never sends a key signature or any byte onto the
3-wire bus toward the radio, and it refuses to touch the XTS's own USB port
(VID:PID 0cad:1001), which also enumerates as /dev/ttyACM* and must not be fed
keyfill framing.

Run (no args = scan every candidate port):
    python kvl_probe.py
    python kvl_probe.py /dev/ttyACM0        # a specific port
    python kvl_probe.py --no-self-test      # identify only

STATUS: untested against the real adapters (written without hardware). The
framing/opcodes mirror the repo's kfdtool.py (adapter protocol). When you plug
in, the model_id / fw_version reported here tell us what each adapter emulates.
"""
from __future__ import annotations

import sys
import time
from typing import List, Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial required: pip install pyserial")
    sys.exit(1)

# --- KFDtool adapter protocol (matches src/open_astro/protocol/kfdtool.py) ---
SOM_EOM = 0x61
SOM_EOM_PLACEHOLDER = 0x62
ESC = 0x63
ESC_PLACEHOLDER = 0x64

CMD_READ = 0x11
CMD_SELF_TEST = 0x15
RSP_READ = 0x21
RSP_SELF_TEST = 0x25
RSP_ERROR = 0x20

READ_AP_VER = 0x01
READ_FW_VER = 0x02
READ_UNIQUE_ID = 0x03
READ_MODEL_ID = 0x04
READ_HW_REV = 0x05
READ_SER_NUM = 0x06

# Ports we must never probe with keyfill framing:
XTS_RADIO_VIDPID = (0x0CAD, 0x1001)  # the radio's own AT/CDC port


def frame(payload: bytes) -> bytes:
    out = bytearray([SOM_EOM])
    for b in payload:
        if b == ESC:
            out += bytes([ESC, ESC_PLACEHOLDER])
        elif b == SOM_EOM:
            out += bytes([ESC, SOM_EOM_PLACEHOLDER])
        else:
            out.append(b)
    out.append(SOM_EOM)
    return bytes(out)


def unframe(raw: bytes) -> List[bytes]:
    pkts, cur = [], bytearray()
    in_pkt = esc = False
    for b in raw:
        if not in_pkt:
            if b == SOM_EOM:
                in_pkt, esc = True, False
                cur.clear()
        elif esc:
            cur.append(ESC if b == ESC_PLACEHOLDER else
                       SOM_EOM if b == SOM_EOM_PLACEHOLDER else b)
            esc = False
        elif b == ESC:
            esc = True
        elif b == SOM_EOM:
            pkts.append(bytes(cur)); cur.clear(); in_pkt = False
        else:
            cur.append(b)
    return pkts


def xfer(ser: serial.Serial, payload: bytes, timeout: float = 1.0) -> Optional[bytes]:
    ser.reset_input_buffer()
    ser.write(frame(payload))
    ser.flush()
    raw, t0 = bytearray(), time.time()
    while time.time() - t0 < timeout:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            raw += chunk
            p = unframe(bytes(raw))
            if p:
                return p[0]
        else:
            time.sleep(0.01)
    return None


def identify(port: str, run_self_test: bool = True) -> Optional[dict]:
    """Return adapter identity dict, or None if the port isn't a KFD adapter."""
    try:
        ser = serial.Serial(port, 115200, timeout=0.3)
    except Exception as e:
        print(f"  [{port}] open failed: {e}")
        return None
    try:
        # Firmware version is the cheapest liveness/identity check.
        r = xfer(ser, bytes([CMD_READ, READ_FW_VER]))
        if not r or r[0] != RSP_READ:
            return None  # not a KFDtool-protocol adapter
        info = {"port": port}
        info["fw"] = f"{r[2]}.{r[3]}.{r[4]}" if len(r) >= 5 else "?"

        r = xfer(ser, bytes([CMD_READ, READ_AP_VER]))
        if r and r[0] == RSP_READ and len(r) >= 5:
            info["ap"] = f"{r[2]}.{r[3]}.{r[4]}"

        r = xfer(ser, bytes([CMD_READ, READ_HW_REV]))
        if r and r[0] == RSP_READ and len(r) >= 4:
            info["hw"] = f"{r[2]}.{r[3]}"

        r = xfer(ser, bytes([CMD_READ, READ_MODEL_ID]))
        if r and r[0] == RSP_READ and len(r) >= 3:
            info["model_id"] = r[2]

        r = xfer(ser, bytes([CMD_READ, READ_SER_NUM]))
        if r and r[0] == RSP_READ and len(r) > 2:
            info["serial"] = r[2:].hex()

        if run_self_test:
            r = xfer(ser, bytes([CMD_SELF_TEST]), timeout=3.0)
            info["self_test"] = ("pass" if r and r[0] == RSP_SELF_TEST
                                 else "FAIL/none")
        return info
    finally:
        ser.close()


def candidate_ports(explicit: Optional[str]) -> List[str]:
    if explicit:
        return [explicit]
    ports = []
    for p in serial.tools.list_ports.comports():
        if p.vid is not None and (p.vid, p.pid) == XTS_RADIO_VIDPID:
            print(f"  skipping {p.device} -- that's the XTS radio "
                  f"({p.vid:04x}:{p.pid:04x}), not a key-fill adapter")
            continue
        ports.append(p.device)
    return ports


def main() -> int:
    args = [a for a in sys.argv[1:]]
    run_self_test = "--no-self-test" not in args
    explicit = next((a for a in args if not a.startswith("-")), None)

    ports = candidate_ports(explicit)
    if not ports:
        print("No candidate serial ports. Plug in the adapter and re-run.")
        return 1

    found = 0
    for port in ports:
        print(f"[*] probing {port} ...")
        info = identify(port, run_self_test)
        if info:
            found += 1
            print(f"  [+] KFD adapter on {port}:")
            for k in ("ap", "fw", "hw", "model_id", "serial", "self_test"):
                if k in info:
                    print(f"        {k:10s}: {info[k]}")
    if not found:
        print("No KFD adapter answered. Check cable/port, or the firmware "
              "may use a different protocol -- tell me the model and I'll adapt.")
        return 1
    print(f"[done] {found} adapter(s) identified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
