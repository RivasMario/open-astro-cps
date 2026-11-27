"""Mock ASTRO 25 RCMP radio server for capturing CPS/Depot wire sequences.

Listens on TCP port 8002 (the radio's RCMP port), serves codeplug objects
from an optional ``.cpg`` backup, logs every inbound RCMP record (including
``0x0107`` UnlockSecurity / ``0x0103`` / ``0x0101`` / ``0x0106``) to a JSONL
file, and returns valid ``0x81xx`` ACKs so CPS/Depot completes its full flow
with zero risk to real hardware.
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from open_astro.protocol import rcmp


def _crc16_ccitt(data: bytes) -> int:
    crc = 0x0000
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc


def _frame_with_crc(payload_no_crc: bytes) -> bytes:
    crc = _crc16_ccitt(payload_no_crc)
    body = payload_no_crc + struct.pack(">H", crc)
    return struct.pack(">H", len(body)) + body


def _load_cpg_objects(cpg_path: Optional[Path]) -> Dict[Tuple[int, int, int], bytes]:
    objects: Dict[Tuple[int, int, int], bytes] = {}
    if not cpg_path:
        return objects
    try:
        from open_astro.parsers.cpg_decode import CpgParser
        parser = CpgParser(cpg_path)
        for obj in parser.objects():
            part = obj.get("partition") or 0x80
            objects[(part, obj["tag"], obj["instance"])] = obj["payload"]
    except Exception as exc:
        print(f"[warn] Could not load {cpg_path}: {exc}", file=sys.stderr)
    return objects


class MockRadioServer:
    def __init__(self, host: str, port: int, objects: Dict[Tuple[int, int, int], bytes],
                 log_path: Optional[Path] = None) -> None:
        self.host = host
        self.port = port
        self.flash: Dict[Tuple[int, int, int], bytes] = dict(objects)
        self.staging: Dict[Tuple[int, int, int], bytes] = dict(objects)
        self.objects = self.flash
        self.log_path = log_path
        self._unlock_stage = 0
        self.unlocked_81 = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(4)
        self.bound_port = self._sock.getsockname()[1]

    def _log(self, direction: str, opcode: int, payload: bytes) -> None:
        rec = {
            "ts": round(time.time(), 4),
            "dir": direction,
            "opcode": f"0x{opcode:04x}",
            "len": len(payload),
            "hex": payload.hex(),
        }
        print(f"[{direction}] op=0x{opcode:04x} len={len(payload)} hex={payload[:32].hex()}"
              + ("..." if len(payload) > 32 else ""))
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(rec) + "\n")

    def _handle_record(self, payload: bytes) -> bytes:
        if len(payload) < 2:
            return _frame_with_crc(bytes([0x80, 0x00, 0x01]))
        opcode = struct.unpack(">H", payload[:2])[0]
        self._log("IN", opcode, payload)

        resp_op = opcode | rcmp.RESP_FLAG
        if opcode == rcmp.OP_SESSION and len(payload) >= 3:
            sub = payload[2]
            if sub == 0x00:
                self.staging = dict(self.flash)
                self.unlocked_81 = False
            elif sub == 0x01:
                # Commit staged writes to persistent flash/EEPROM and reset session
                self.flash = dict(self.staging)
                self.objects = self.flash
                self.unlocked_81 = False
            resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))
        elif opcode == rcmp.OP_READ and len(payload) >= 9:
            part = payload[2]
            obj_id, inst, req_len = struct.unpack(">HHH", payload[3:9])
            data = self.flash.get((part, obj_id, inst), b"\x00" * req_len)[:req_len]
            if len(data) < req_len:
                data = data.ljust(req_len, b"\x00")
            echo = struct.pack(">HBHHH", resp_op, part, obj_id, inst, len(data)) + b"\x00\x00\x00"
            resp = _frame_with_crc(echo + data)
        elif opcode == rcmp.OP_PREPARE and len(payload) >= 7:
            part = payload[2]
            start_id, end_id = struct.unpack(">HH", payload[3:7])
            if part == 0x80:
                for k in [k for k in self.staging if k[0] == 0x80 and start_id <= k[1] <= end_id]:
                    del self.staging[k]
            resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))
        elif opcode == rcmp.OP_WRITE and len(payload) >= 11:
            part = payload[2]
            obj_id, inst, data_len = struct.unpack(">HHH", payload[3:9])
            # Support both standard 13-byte RCMP write header (with 0000 + len2) and compact 9-byte header
            if len(payload) >= 13 + data_len + 2 and payload[9:11] == b"\x00\x00":
                data = payload[13:13 + data_len]
            else:
                data = payload[9:9 + data_len]
            if part == 0x82:
                # Tuning partition is ReadOnly — reject
                resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x01))
            elif part == 0x81 and not self.unlocked_81:
                # Real hardware behavior: ACK transport, silently drop EEPROM write
                resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))
            else:
                self.staging[(part, obj_id, inst)] = data
                resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))
        elif opcode == rcmp.OP_CHECKSUM:
            # First 0x0107 returns a 32-byte deterministic seed; second unlocks 0x81
            if self._unlock_stage == 0:
                self._unlock_stage = 1
                seed = bytes(range(32))
                resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00) + seed)
            else:
                self._unlock_stage = 0
                self.unlocked_81 = True
                resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))
        else:
            resp = _frame_with_crc(struct.pack(">HB", resp_op, 0x00))

        self._log("OUT", resp_op, resp[2:])
        return resp

    def serve_once(self) -> None:
        conn, addr = self._sock.accept()
        print(f"[connect] {addr}")
        buf = bytearray()
        with conn:
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                while len(buf) >= 2:
                    rec_len = struct.unpack(">H", buf[:2])[0]
                    if len(buf) < 2 + rec_len:
                        break
                    payload = bytes(buf[2:2 + rec_len])
                    del buf[:2 + rec_len]
                    conn.sendall(self._handle_record(payload))

    def close(self) -> None:
        self._sock.close()


def _run_self_test() -> None:
    srv = MockRadioServer("127.0.0.1", 0, {(0x81, 0x1004, 0): b"205CFR2930"}, None)
    t = threading.Thread(target=srv.serve_once, daemon=True)
    t.start()
    frames = [
        _frame_with_crc(bytes.fromhex("010600")),
        _frame_with_crc(bytes.fromhex("01008110040000000a0000")),
        _frame_with_crc(bytes.fromhex("0102")),
        _frame_with_crc(bytes.fromhex("010380000201f4")),
        _frame_with_crc(bytes.fromhex("010781201100")),
        _frame_with_crc(bytes.fromhex("010781") + bytes(32)),
        _frame_with_crc(bytes.fromhex("0101800fff00000004") + b"TEST"),
        _frame_with_crc(bytes.fromhex("010601")),
    ]
    with socket.create_connection(("127.0.0.1", srv.bound_port), timeout=5) as cli:
        for f in frames:
            cli.sendall(f)
            hdr = cli.recv(2)
            rlen = struct.unpack(">H", hdr)[0]
            body = cli.recv(rlen)
            assert body[0] & 0x80, f"Expected 0x80 response bit, got {body[:2].hex()}"
    srv.close()
    print("[self-test] PASS: all 8 RCMP write/unlock/commit frames acked cleanly.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mock ASTRO 25 RCMP radio for CPS/Depot capture")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--cpg", type=Path, default=None, help="Optional .cpg backup to serve on 0x0100 reads")
    ap.add_argument("--out", type=Path, default=None, help="Optional JSONL capture log")
    ap.add_argument("--self-test", action="store_true", help="Run offline loopback self-test and exit")
    args = ap.parse_args()

    if args.self_test:
        _run_self_test()
        return

    objs = _load_cpg_objects(args.cpg)
    srv = MockRadioServer(args.host, args.port, objs, args.out)
    print(f"Listening on {args.host}:{srv.bound_port} (loaded {len(objs)} objects)...")
    try:
        while True:
            srv.serve_once()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
