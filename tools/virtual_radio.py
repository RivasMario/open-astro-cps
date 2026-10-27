#!/usr/bin/env python3
"""Standalone Virtual ASTRO 25 Radio RCMP Server.

Loads an ASTRO 25 codeplug (.cpg or structural JSON) and serves Partition 0x80
(codeplug objects) and Partition 0x81 (identity / security objects) over TCP
port 8002 (and standard TCP loopback 127.0.0.1:8002).

Supports standard length-prefixed RCMP frame format:
  <2-byte length BE> <2-byte opcode BE> <payload>

Opcodes supported:
  - 0x000C: Unlock / Start Session -> 0x800C (status 0 = success)
  - 0x000D: Lock / End Session -> 0x800D (status 0 = success)
  - 0x0001: ReadObject -> 0x8001 (returns loaded object data)
  - 0x0002: WriteObject -> 0x8002 (refuses partition 0x82!)
  - 0x0100: OP_READ (rcmp.py / RcmpReadClient verified wire format)
  - 0x0101: OP_WRITE (rcmp.py / RcmpWriteClient format, refuses 0x82)
  - 0x0103: OP_PREPARE (erase/prepare acknowledge)
  - 0x0106: OP_SESSION (session open/close)
  - 0x0011: Query Serial Number
  - 0x0012: Query Authorization UUID
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from open_astro.parsers.cpg_parser import CpgData, CpgParser, crc16_ccitt
from open_astro.protocol import rcmp

DEFAULT_CPG = os.path.join(REPO_ROOT, "backups", "205CFR2930.cpg")
PART_CODEPLUG = 0x80
PART_SECURITY = 0x81
PART_TUNING = 0x82


def load_codeplug(path: str,
                  serial_override: Optional[str] = None,
                  flashcode_override: Optional[str] = None) -> CpgData:
    """Load a .cpg or structural .json codeplug and apply overrides."""
    if not os.path.isabs(path) and not os.path.exists(path):
        candidate = os.path.join(REPO_ROOT, path)
        if os.path.exists(candidate):
            path = candidate

    if not os.path.exists(path):
        raise FileNotFoundError(f"Codeplug file not found: {path}")

    if path.lower().endswith(".cpg"):
        data = CpgParser.load_file(path)
    elif path.lower().endswith(".json"):
        data = _load_json_codeplug(path)
    else:
        # Default try CpgParser, fallback to JSON
        try:
            data = CpgParser.load_file(path)
        except Exception:
            data = _load_json_codeplug(path)

    # Apply serial override
    if serial_override:
        data.serial = serial_override
        ser_ascii = serial_override.encode("ascii", errors="replace") + b"\x00"
        if (PART_SECURITY, 0x1004, 0) in data:
            old_p = bytearray(data[(PART_SECURITY, 0x1004, 0)])
            # Serial is typically at offset 2 in 0x1004
            parts = old_p.split(b"\x00", 2)
            if len(parts) >= 2 and len(parts[0]) >= 2:
                prefix = parts[0][:2]
                remainder = b"\x00".join(parts[1:])
                data[(PART_SECURITY, 0x1004, 0)] = bytes(prefix + ser_ascii + remainder)
            else:
                data[(PART_SECURITY, 0x1004, 0)] = bytes(b"\x02\x12" + ser_ascii + (data.model or "H46UCF9PW6AN").encode("ascii") + b"\x00")
        else:
            data[(PART_SECURITY, 0x1004, 0)] = b"\x02\x12" + ser_ascii + (data.model or "H46UCF9PW6AN").encode("ascii") + b"\x00"

    # Apply flashcode override
    if flashcode_override:
        data.flashcode = flashcode_override
        fc_bytes = flashcode_override.encode("ascii", errors="replace") + b"\x00"
        if (PART_SECURITY, 0x1006, 0) in data:
            old_p = data[(PART_SECURITY, 0x1006, 0)]
            prefix = old_p[:8] if len(old_p) >= 8 else b"\x00\x00\x00\x10\x00\x01\x00\x01"
            data[(PART_SECURITY, 0x1006, 0)] = prefix + fc_bytes
        else:
            data[(PART_SECURITY, 0x1006, 0)] = b"\x00\x00\x00\x10\x00\x01\x00\x01" + fc_bytes

    return data


def _load_json_codeplug(path: str) -> CpgData:
    """Parse JSON codeplug file (structural dump or high-level dictionary)."""
    with open(path, "r", encoding="utf-8") as f:
        jd = json.load(f)

    obj_map: Dict[Tuple[int, int, int], bytes] = {}
    header = jd.get("header") or {}
    model = header.get("model") or jd.get("radio_model") or jd.get("model")
    serial = header.get("serial") or jd.get("serial_number") or jd.get("serial")
    flashcode = jd.get("flashcode")

    if "streams" in jd:
        # Structural dump from CpgParser.to_json()
        part_of = {}
        for s in jd["streams"]:
            if s.get("name") == "DataStg/Strm_0" and "decrypted_hex" in s:
                raw0 = bytes.fromhex(s["decrypted_hex"])
                for k in range(len(raw0) // 10):
                    iid, inst, part, crc, strm = (
                        int.from_bytes(raw0[10 * k + o:10 * k + o + 2], "big")
                        for o in (0, 2, 4, 6, 8)
                    )
                    part_of[strm] = part

        for s in jd["streams"]:
            name = s.get("name", "")
            if name.startswith("DataStg/Strm_") and name != "DataStg/Strm_0":
                strm_idx = int(name.split("_")[-1])
                hex_data = s.get("decrypted_hex")
                if hex_data:
                    raw = bytes.fromhex(hex_data)
                    if len(raw) >= 6:
                        tag = int.from_bytes(raw[0:2], "big")
                        inst = int.from_bytes(raw[2:4], "big")
                        length = int.from_bytes(raw[4:6], "big")
                        payload = raw[6:6 + length]
                        part = part_of.get(strm_idx, PART_CODEPLUG)
                        obj_map[(part, tag, inst)] = payload

    if not model:
        model = "H46UCF9PW6AN"
    if not serial:
        serial = "205CFR2930"
    if not flashcode:
        flashcode = "000008-002410-2"

    if (PART_SECURITY, 0x1004, 0) not in obj_map:
        obj_map[(PART_SECURITY, 0x1004, 0)] = (
            b"\x02\x12" + serial.encode("ascii") + b"\x00" + model.encode("ascii") + b"\x00"
        )
    if (PART_SECURITY, 0x1006, 0) not in obj_map:
        obj_map[(PART_SECURITY, 0x1006, 0)] = (
            b"\x00\x00\x00\x10\x00\x01\x00\x01" + flashcode.encode("ascii") + b"\x00"
        )

    return CpgData(obj_map, header=header, model=model, serial=serial, flashcode=flashcode)


class VirtualRadioServer:
    """Virtual ASTRO 25 Radio RCMP Server."""

    def __init__(self, cpg_data: CpgData, host: str = "127.0.0.1", port: int = 8002,
                 verbose: bool = False, lock_security: bool = False):
        self.cpg_data = cpg_data
        self.host = host
        self.port = port
        self.verbose = verbose
        self.lock_security = lock_security
        self.running = False
        self.server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.client_threads: list[threading.Thread] = []

    def start(self) -> None:
        """Start the server in a background thread."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        # Update port if bound to ephemeral port 0
        self.port = self.server_sock.getsockname()[1]
        self.server_sock.listen(5)
        self.running = True

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the server and close all sockets."""
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
            self.server_sock = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[VirtualRadio] {msg}", file=sys.stderr, flush=True)

    def _listen_loop(self) -> None:
        self._log(f"Listening on {self.host}:{self.port}")
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
            except OSError:
                break
            self._log(f"Connection accepted from {addr[0]}:{addr[1]}")
            ct = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
            # Prune finished client threads so the list cannot grow unbounded.
            with self._lock:
                self.client_threads = [t for t in self.client_threads if t.is_alive()]
                self.client_threads.append(ct)
            ct.start()

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        buf = bytearray()
        # Per-connection session state (e.g. UnlockSecurity grant for this client).
        session: Dict[str, Any] = {"unlocked": False}
        # Guard against idle / half-open clients blocking a thread forever.
        client_sock.settimeout(30.0)
        try:
            while self.running:
                # Need at least 2-byte length prefix
                while len(buf) < 2:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        return
                    buf.extend(chunk)

                length = (buf[0] << 8) | buf[1]
                if length == 0:
                    del buf[:2]
                    continue

                while len(buf) < 2 + length:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        return
                    buf.extend(chunk)

                record = bytes(buf[2:2 + length])
                del buf[:2 + length]

                resp_payload = self.process_record(record, session)
                if resp_payload:
                    resp_frame = struct.pack(">H", len(resp_payload)) + resp_payload
                    client_sock.sendall(resp_frame)
        except socket.timeout:
            self._log(f"Client idle timeout, closing: {addr[0]}:{addr[1]}")
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                client_sock.close()
            except OSError:
                pass
            self._log(f"Client disconnected: {addr[0]}:{addr[1]}")

    def process_record(self, record: bytes,
                       session: Optional[Dict[str, Any]] = None) -> bytes:
        """Process one incoming RCMP record and return response record payload.

        ``session`` carries per-connection state (e.g. the UnlockSecurity grant).
        A direct call without a session gets a throwaway one.
        """
        if session is None:
            session = {"unlocked": False}
        if len(record) < 2:
            return b""

        opcode = (record[0] << 8) | record[1]
        payload = record[2:]

        # Opcode 0x000C: Unlock / Start Session
        if opcode == 0x000C:
            self._log("REQ 0x000C (Unlock / Start Session)")
            # Respond with 0x800C (status 0 = success)
            resp = struct.pack(">HB", 0x800C, 0x00)
            self._log("RESP 0x800C (status 0 = success)")
            return resp

        # Opcode 0x000D: Lock / End Session
        elif opcode == 0x000D:
            self._log("REQ 0x000D (Lock / End Session)")
            # Respond with 0x800D (status 0 = success)
            resp = struct.pack(">HB", 0x800D, 0x00)
            self._log("RESP 0x800D (status 0 = success)")
            return resp

        # Opcode 0x0106: OP_SESSION (rcmp.py open/commit)
        elif opcode == 0x0106:
            sub = payload[0] if payload else 0
            self._log(f"REQ 0x0106 (OP_SESSION, sub={sub})")
            resp = struct.pack(">HB", 0x8106, 0x00)
            self._log("RESP 0x8106 (SESSION_ACK)")
            return resp

        # Opcode 0x0001: ReadObject
        elif opcode == 0x0001:
            self._log(f"REQ 0x0001 (ReadObject): {payload.hex()}")
            if len(payload) < 5:
                return struct.pack(">H", 0x8001)

            part = payload[0]
            obj = (payload[1] << 8) | payload[2]
            inst = (payload[3] << 8) | payload[4]
            offset = 0
            length = None

            if len(payload) >= 9:
                w1 = (payload[5] << 8) | payload[6]
                w2 = (payload[7] << 8) | payload[8]
                if w1 == 0 and w2 > 0:
                    offset, length = 0, w2
                elif w2 == 0 and w1 > 0:
                    offset, length = 0, w1
                else:
                    offset, length = w1, w2
            elif len(payload) >= 7:
                length = (payload[5] << 8) | payload[6]

            data = self._lookup_object(part, obj, inst)
            sliced = data[offset:offset + length] if length else data[offset:]
            self._log(f"RESP 0x8001 (ReadObject 0x{part:02X}:0x{obj:04X}:{inst}, {len(sliced)} bytes)")
            return struct.pack(">H", 0x8001) + sliced

        # Opcode 0x0100: OP_READ (rcmp.py / RcmpReadClient)
        elif opcode == 0x0100:
            if len(payload) < 7:
                return struct.pack(">H", 0x8100)
            part = payload[0]
            obj = (payload[1] << 8) | payload[2]
            inst = (payload[3] << 8) | payload[4]
            reqlen = (payload[5] << 8) | payload[6]
            offset = ((payload[7] << 8) | payload[8]) if len(payload) >= 9 else 0

            self._log(f"REQ 0x0100 (OP_READ part=0x{part:02X} obj=0x{obj:04X} inst={inst} reqlen={reqlen})")
            data = self._lookup_object(part, obj, inst)
            sliced = data[offset:offset + reqlen] if reqlen else data[offset:]

            # Read-ack layout: 12-byte header + data + CRC-16
            # 00 <part:1> <obj:2> <inst:2> <reqlen:2> 00 00 <acklen:2>
            acklen = len(sliced)
            header = struct.pack(">BBHHHHH", 0x00, part, obj, inst, reqlen, 0x0000, acklen)
            crc = crc16_ccitt(sliced)
            resp = struct.pack(">H", 0x8100) + header + sliced + struct.pack(">H", crc)
            self._log(f"RESP 0x8100 (READ_ACK, {acklen} bytes payload, crc=0x{crc:04X})")
            return resp

        # Opcode 0x0002: WriteObject
        elif opcode == 0x0002:
            part = payload[0] if payload else 0
            self._log(f"REQ 0x0002 (WriteObject part=0x{part:02X})")
            if part == PART_TUNING:
                self._log("[-] Refusing WriteObject to partition 0x82 (Tuning Firewall active)!")
                # Error status 1
                return struct.pack(">HB", 0x8002, 0x01)

            if self.lock_security and part == PART_SECURITY and not session.get("unlocked"):
                self._log("[-] Refusing WriteObject to partition 0x81 (security locked; send 0x0107 UnlockSecurity first)")
                return struct.pack(">HB", 0x8002, 0x01)

            if len(payload) >= 5:
                obj = (payload[1] << 8) | payload[2]
                inst = (payload[3] << 8) | payload[4]
                if len(payload) >= 7:
                    datalen = (payload[5] << 8) | payload[6]
                    data = payload[7:7 + datalen] if len(payload) >= 7 + datalen else payload[7:]
                else:
                    data = payload[5:]
                with self._lock:
                    self.cpg_data.objects[(part, obj, inst)] = data
                self._log(f"[+] Wrote {len(data)} bytes to 0x{part:02X}:0x{obj:04X}:{inst}")

            return struct.pack(">HB", 0x8002, 0x00)

        # Opcode 0x0101: OP_WRITE (rcmp.py / RcmpWriteClient)
        elif opcode == 0x0101:
            part = payload[0] if payload else 0
            self._log(f"REQ 0x0101 (OP_WRITE part=0x{part:02X})")
            if part == PART_TUNING:
                self._log("[-] Refusing OP_WRITE to partition 0x82 (Tuning Firewall active)!")
                return struct.pack(">HB", 0x8101, 0x01)

            if self.lock_security and part == PART_SECURITY and not session.get("unlocked"):
                self._log("[-] Refusing OP_WRITE to partition 0x81 (security locked; send 0x0107 UnlockSecurity first)")
                return struct.pack(">HB", 0x8101, 0x01)

            if len(payload) >= 13:
                obj = (payload[1] << 8) | payload[2]
                inst = (payload[3] << 8) | payload[4]
                # In rcmp.build_write:
                # part(1), obj(2), inst(2), len(2), 0000(2), len(2), data(len-2), crc(2)
                data = payload[11:-2]
                # Verify the trailing CRC-16 over the written data; accept either way
                # (this is a test double, not a strict validator).
                frame_crc = (payload[-2] << 8) | payload[-1]
                calc_crc = crc16_ccitt(data)
                if calc_crc != frame_crc:
                    self._log(f"[!] OP_WRITE CRC mismatch: frame=0x{frame_crc:04X} calc=0x{calc_crc:04X} (accepting anyway)")
                with self._lock:
                    self.cpg_data.objects[(part, obj, inst)] = data
                self._log(f"[+] Wrote {len(data)} bytes to 0x{part:02X}:0x{obj:04X}:{inst}")

            return struct.pack(">HB", 0x8101, 0x00)

        # Opcode 0x0103: OP_PREPARE
        elif opcode == 0x0103:
            self._log("REQ 0x0103 (OP_PREPARE)")
            return struct.pack(">HB", 0x8103, 0x00)

        # Opcode 0x0107: UnlockSecurity (grants partition 0x81 writes for this session)
        elif opcode == 0x0107:
            self._log("REQ 0x0107 (UnlockSecurity)")
            session["unlocked"] = True
            self._log("RESP 0x8107 (status 0 = security unlocked for this session)")
            return struct.pack(">HB", 0x8107, 0x00)

        # Opcode 0x0011: Query Serial Number
        elif opcode == 0x0011:
            self._log("REQ 0x0011 (Query Serial)")
            ser_bytes = (self.cpg_data.serial or "UNKNOWN").encode("ascii") + b"\x00"
            return struct.pack(">HB", 0x8011, 0x00) + ser_bytes

        # Opcode 0x0012: Query Authorization UUID
        elif opcode == 0x0012:
            self._log("REQ 0x0012 (Query UUID)")
            uuid_hex = self.cpg_data.header.get("uuid") or "00" * 16
            try:
                uuid_bytes = bytes.fromhex(uuid_hex)[:16]
            except ValueError:
                uuid_bytes = b"\x00" * 16
            return struct.pack(">HB", 0x8012, 0x00) + uuid_bytes

        # Unknown / default: echo with response flag
        else:
            self._log(f"REQ 0x{opcode:04X} (unknown)")
            resp_op = opcode | 0x8000
            return struct.pack(">HB", resp_op, 0x00)

    def _lookup_object(self, part: int, obj: int, inst: int) -> bytes:
        with self._lock:
            if (part, obj, inst) in self.cpg_data.objects:
                return self.cpg_data.objects[(part, obj, inst)]
            for (p, o, i), data in self.cpg_data.objects.items():
                if p == part and o == obj and (inst == 0 or i == inst):
                    return data
        return b""


def print_banner(server: VirtualRadioServer) -> None:
    """Print the startup banner with radio details and listening socket."""
    cpg = server.cpg_data
    partitions = sorted(set(hex(p) for p, o, i in cpg.objects.keys()))
    parts_str = ", ".join(partitions) if partitions else "None"

    banner = f"""
======================================================================
  VIRTUAL ASTRO 25 RADIO RCMP SERVER
======================================================================
  Radio Model:  {cpg.model}
  Serial:       {cpg.serial}
  FLASHcode:    {cpg.flashcode}
  Objects:      {len(cpg.objects)} loaded (Partitions: {parts_str})
  Status:       Active listening on {server.host}:{server.port}
======================================================================
"""
    print(banner.strip(), flush=True)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Virtual ASTRO 25 Radio RCMP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "codeplug",
        nargs="?",
        default=DEFAULT_CPG,
        help="Path to .cpg or structural .json codeplug",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Bind port",
    )
    parser.add_argument(
        "--flashcode",
        help="Override FLASHcode string (e.g. 000008-006410-3)",
    )
    parser.add_argument(
        "--serial",
        help="Override serial number string (e.g. 205CFR2930)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log all RCMP requests and responses to stderr",
    )
    parser.add_argument(
        "--lock-security",
        action="store_true",
        help="Refuse partition 0x81 writes until the client sends a 0x0107 UnlockSecurity",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        cpg_data = load_codeplug(
            args.codeplug,
            serial_override=args.serial,
            flashcode_override=args.flashcode,
        )
    except Exception as e:
        print(f"[-] Failed to load codeplug '{args.codeplug}': {e}", file=sys.stderr)
        return 1

    server = VirtualRadioServer(
        cpg_data=cpg_data,
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        lock_security=args.lock_security,
    )

    try:
        server.start()
    except Exception as e:
        print(f"[-] Failed to bind {args.host}:{args.port}: {e}", file=sys.stderr)
        return 1

    print_banner(server)
    print("\nPress Ctrl+C to terminate the virtual radio server.\n", flush=True)

    try:
        while server.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] Shutting down Virtual ASTRO 25 Radio Server...", flush=True)
    finally:
        server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
