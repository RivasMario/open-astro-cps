#!/usr/bin/env python3
"""Standalone Virtual ASTRO 25 Radio RCMP Server & Packet Capture Harness.

Loads an ASTRO 25 codeplug (.cpg or structural JSON) and optional tuning dump
(.tun) and serves Partition 0x80 (codeplug objects), Partition 0x81 (identity /
security objects), and Partition 0x82 (read-only tuning objects) over TCP port
8002 (and optional serial/PTY PPP link).

Supports standard length-prefixed RCMP frame format:
  <2-byte length BE> <2-byte opcode BE> <payload>

Opcodes supported:
  - 0x000C: Unlock / Start Session -> 0x800C (status 0 = success)
  - 0x000D: Lock / End Session -> 0x800D (status 0 = success)
  - 0x0006: Tuner / Mode Subcommand -> 0x8006 (status 0 = success)
  - 0x000F: Query Firmware / Codeplug Version (sub 0x00, 0x10, 0x20, 0x40, 0x42)
  - 0x0010: Query Model Number String -> 0x8010 / raw model string
  - 0x0011: Query Serial Number -> 0x8011
  - 0x0012: Query Authorization UUID -> 0x8012
  - 0x0001: ReadObject -> 0x8001 (returns loaded object data)
  - 0x0002: WriteObject -> 0x8002 (refuses partition 0x82!)
  - 0x0100: OP_READ (rcmp.py / RcmpReadClient verified wire format, 0x81 empty status)
  - 0x0101: OP_WRITE (rcmp.py / RcmpWriteClient format, refuses 0x82)
  - 0x0102: OP_WRITE_PRE (write pre-step -> 0x8102)
  - 0x0103: OP_PREPARE (erase/prepare acknowledge -> 0x8103)
  - 0x0106: OP_SESSION (session open/close -> 0x8106)
  - 0x0107 / 0x2011: UnlockSecurity (1-step auto-unlock or 2-step 32-byte LFSR seed->response)
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
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from open_astro.parsers.cpg_parser import CpgData, CpgParser, crc16_ccitt
from open_astro.protocol import rcmp
from open_astro.protocol.unlock import SEED_LEN, unlock_response

DEFAULT_CPG = os.path.join(REPO_ROOT, "backups", "205CFR2930.cpg")
PART_CODEPLUG = 0x80
PART_SECURITY = 0x81
PART_TUNING = 0x82
DEFAULT_CHALLENGE_SEED = bytes(range(1, SEED_LEN + 1))


class PcapLogger:
    """Writes length-prefixed RCMP TCP records as a synthetic IPv4/TCP PCAP."""

    def __init__(self, path: str, client_ip: str = "192.168.128.2",
                 radio_ip: str = "192.168.128.1", client_port: int = 8001,
                 radio_port: int = 8002):
        self.path = path
        self.client_ip = socket.inet_aton(client_ip)
        self.radio_ip = socket.inet_aton(radio_ip)
        self.client_port = client_port
        self.radio_port = radio_port
        self._lock = threading.Lock()
        self._c_seq = 0x1000
        self._r_seq = 0x2000
        self._ident = 1
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(self.path, "wb") as fh:
            # Global PCAP header: magic, v2.4, tz=0, sigfigs=0, snaplen=65535, DLT_RAW (101)
            fh.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 101))

    def log_frame(self, direction: str, raw_frame: bytes) -> None:
        """Append one TCP segment (`direction`: 'OUT' host->radio, 'IN' radio->host)."""
        with self._lock:
            now = time.time()
            sec = int(now)
            usec = int((now - sec) * 1_000_000)
            if direction == "OUT":
                src_ip, dst_ip = self.client_ip, self.radio_ip
                sport, dport = self.client_port, self.radio_port
                seq, ack = self._c_seq, self._r_seq
                self._c_seq = (self._c_seq + len(raw_frame)) & 0xFFFFFFFF
            else:
                src_ip, dst_ip = self.radio_ip, self.client_ip
                sport, dport = self.radio_port, self.client_port
                seq, ack = self._r_seq, self._c_seq
                self._r_seq = (self._r_seq + len(raw_frame)) & 0xFFFFFFFF

            tcp_hdr = struct.pack(
                ">HHIIBBHHH",
                sport, dport, seq, ack,
                0x50, 0x18, 8192, 0, 0,
            )
            ip_len = 20 + len(tcp_hdr) + len(raw_frame)
            self._ident = (self._ident + 1) & 0xFFFF
            ip_hdr = struct.pack(
                ">BBHHHBBH4s4s",
                0x45, 0x00, ip_len, self._ident, 0x4000, 64, 6, 0, src_ip, dst_ip,
            )
            pkt = ip_hdr + tcp_hdr + raw_frame
            rec_hdr = struct.pack("<IIII", sec, usec, len(pkt), len(pkt))
            with open(self.path, "ab") as fh:
                fh.write(rec_hdr + pkt)


def load_codeplug(path: str,
                  serial_override: Optional[str] = None,
                  flashcode_override: Optional[str] = None,
                  tun_path: Optional[str] = None) -> CpgData:
    """Load a .cpg or structural .json codeplug (plus optional .tun) and apply overrides."""
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

    # Auto-load matching .tun file if present so CPS/Tuner reads of Partition 0x82 succeed
    if tun_path is None:
        base_tun = os.path.splitext(path)[0] + ".tun"
        if os.path.exists(base_tun):
            tun_path = base_tun
    if tun_path and os.path.exists(tun_path):
        try:
            tun_data = CpgParser.load_file(tun_path)
            for (part, obj, inst), payload in tun_data.objects.items():
                data.objects[(PART_TUNING, obj, inst)] = payload
        except Exception:
            pass

    # Apply serial override
    if serial_override:
        data.serial = serial_override
        ser_ascii = serial_override.encode("ascii", errors="replace") + b"\x00"
        if (PART_SECURITY, 0x1004, 0) in data:
            old_p = bytearray(data[(PART_SECURITY, 0x1004, 0)])
            parts = old_p.split(b"\x00", 2)
            if len(parts) >= 2 and len(parts[0]) >= 2:
                prefix = parts[0][:2]
                remainder = b"\x00".join(parts[1:])
                data[(PART_SECURITY, 0x1004, 0)] = bytes(prefix + ser_ascii + remainder)
            else:
                data[(PART_SECURITY, 0x1004, 0)] = bytes(
                    b"\x02\x12" + ser_ascii + (data.model or "H46UCF9PW6AN").encode("ascii") + b"\x00"
                )
        else:
            data[(PART_SECURITY, 0x1004, 0)] = (
                b"\x02\x12" + ser_ascii + (data.model or "H46UCF9PW6AN").encode("ascii") + b"\x00"
            )

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
    """Virtual ASTRO 25 Radio RCMP Server & Packet Recorder."""

    def __init__(self, cpg_data: CpgData, host: str = "127.0.0.1", port: int = 8002,
                 verbose: bool = False, lock_security: bool = False,
                 challenge_security: bool = False,
                 seed: bytes = DEFAULT_CHALLENGE_SEED,
                 capture_jsonl: Optional[str] = None,
                 capture_pcap: Optional[str] = None,
                 firmware_version: str = "R20.50.07",
                 codeplug_version: str = "R19.50.01"):
        self.cpg_data = cpg_data
        self.host = host
        self.port = port
        self.verbose = verbose
        self.lock_security = lock_security
        self.challenge_security = challenge_security
        if len(seed) != SEED_LEN:
            raise ValueError(f"seed must be {SEED_LEN} bytes")
        self.seed = bytes(seed)
        self.firmware_version = firmware_version
        self.codeplug_version = codeplug_version
        self.capture_jsonl = capture_jsonl
        self.pcap_logger = PcapLogger(capture_pcap) if capture_pcap else None
        self.trace_events: List[Dict[str, Any]] = []
        self.running = False
        self.server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.client_threads: list[threading.Thread] = []

        if self.capture_jsonl:
            os.makedirs(os.path.dirname(os.path.abspath(self.capture_jsonl)) or ".", exist_ok=True)

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

    def _record_event(self, direction: str, record: bytes,
                      peer: Optional[Tuple[str, int]] = None,
                      note: Optional[str] = None) -> None:
        """Record one RCMP record to in-memory trace, optional JSONL, and optional PCAP."""
        framed = struct.pack(">H", len(record)) + record
        if self.pcap_logger:
            self.pcap_logger.log_frame(direction, framed)

        parsed = rcmp.parse_record(record)
        event: Dict[str, Any] = {
            "ts": time.time(),
            "direction": direction,
            "peer": f"{peer[0]}:{peer[1]}" if peer else "direct",
            "framed_hex": framed.hex(),
            "record_hex": record.hex(),
            "opcode": parsed.get("opcode"),
            "op": parsed.get("op"),
        }
        for k in ("partition", "object", "instance", "length", "start", "end"):
            if k in parsed:
                event[k] = parsed[k]
        if note:
            event["note"] = note

        with self._lock:
            self.trace_events.append(event)
            if self.capture_jsonl:
                with open(self.capture_jsonl, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event) + "\n")

    def _listen_loop(self) -> None:
        self._log(f"Listening on {self.host}:{self.port}")
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
            except OSError:
                break
            self._log(f"Connection accepted from {addr[0]}:{addr[1]}")
            ct = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
            with self._lock:
                self.client_threads = [t for t in self.client_threads if t.is_alive()]
                self.client_threads.append(ct)
            ct.start()

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        buf = bytearray()
        session: Dict[str, Any] = {"unlocked": False, "challenge_pending": False, "peer": addr}
        client_sock.settimeout(30.0)
        try:
            while self.running:
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
            session = {"unlocked": False, "challenge_pending": False}
        peer = session.get("peer")
        self._record_event("OUT", record, peer=peer)

        if len(record) < 2:
            # Handle 1-byte tuner poll (`01` observed in cps_20261023_083355.pcap)
            if record == b"\x01":
                resp = struct.pack(">HBH", 0x8001, 0x00, 0x0301) + b"NNNPTW"
                self._record_event("IN", resp, peer=peer, note="tuner_1byte_poll")
                return resp
            return b""

        opcode = (record[0] << 8) | record[1]
        payload = record[2:]
        resp = self._dispatch_opcode(opcode, payload, session)
        if resp:
            self._record_event("IN", resp, peer=peer)
        return resp

    def _dispatch_opcode(self, opcode: int, payload: bytes,
                         session: Dict[str, Any]) -> bytes:
        # Opcode 0x000C: Unlock / Start Session
        if opcode == 0x000C:
            self._log("REQ 0x000C (Unlock / Start Session)")
            return struct.pack(">HB", 0x800C, 0x00)

        # Opcode 0x000D: Lock / End Session
        elif opcode == 0x000D:
            self._log("REQ 0x000D (Lock / End Session)")
            return struct.pack(">HB", 0x800D, 0x00)

        # Opcode 0x0006: Tuner / Mode Subcommand (observed in tuner/write captures)
        elif opcode == 0x0006:
            sub = payload[0] if payload else 0
            self._log(f"REQ 0x0006 (Mode/Tuner sub=0x{sub:02X})")
            return struct.pack(">HB", 0x8006, 0x00)

        # Opcode 0x0106: OP_SESSION (rcmp.py open/commit)
        elif opcode == 0x0106:
            sub = payload[0] if payload else 0
            self._log(f"REQ 0x0106 (OP_SESSION, sub={sub})")
            return struct.pack(">HB", 0x8106, 0x00)

        # Opcode 0x0102: Pre-Prepare / Write Mode Enter
        elif opcode == 0x0102:
            self._log(f"REQ 0x0102 (OP_WRITE_PRE): {payload.hex()}")
            return struct.pack(">HB", 0x8102, 0x00)

        # Opcode 0x000F: Query Firmware / Codeplug Version & Capabilities
        elif opcode == 0x000F:
            sub = payload[0] if payload else 0x42
            self._log(f"REQ 0x000F (Query Version/Cap sub=0x{sub:02X})")
            if sub == 0x00:
                ver = self.firmware_version.encode("ascii") + b"\x00"
                return struct.pack(">HB", 0x800F, 0x00) + ver
            elif sub == 0x10:
                ver = self.codeplug_version.encode("ascii") + b"\x00"
                return struct.pack(">HB", 0x800F, 0x00) + ver
            elif sub == 0x20:
                return struct.pack(">HB", 0x800F, 0x00) + b"R000000\x00"
            elif sub == 0x40:
                return struct.pack(">HBH", 0x800F, 0x00, 0xC52E)
            else:
                # Default 0x42 observed in codeplug read: 80 0f 00 00 24
                return struct.pack(">HBH", 0x800F, 0x00, 0x0024)

        # Opcode 0x0010: Query Model String
        elif opcode == 0x0010:
            self._log("REQ 0x0010 (Query Model)")
            model_bytes = (self.cpg_data.model or "H46UCF9PW6AN").encode("ascii")
            padded = model_bytes.ljust(15, b"\x00")
            return struct.pack(">HB", 0x8010, 0x00) + padded

        # Opcode 0x0011: Query Serial Number
        elif opcode == 0x0011:
            self._log("REQ 0x0011 (Query Serial)")
            ser_bytes = (self.cpg_data.serial or "UNKNOWN").encode("ascii") + b"\x00"
            return struct.pack(">HB", 0x8011, 0x00) + ser_bytes

        # Opcode 0x0012: Query Authorization UUID
        elif opcode == 0x0012:
            self._log("REQ 0x0012 (Query UUID)")
            uuid_hex = self.cpg_data.header.get("uuid") or "d105add323864e539b513a65076458d3"
            try:
                uuid_bytes = bytes.fromhex(uuid_hex)[:16]
            except ValueError:
                uuid_bytes = b"\x00" * 16
            return struct.pack(">HB", 0x8012, 0x00) + uuid_bytes

        # Opcode 0x0001: ReadObject (or 2-byte Tuner Read `00 01 03 xx`)
        elif opcode == 0x0001:
            self._log(f"REQ 0x0001 (ReadObject): {payload.hex()}")
            if len(payload) == 2:
                # Tuner short read (`00 01 03 00` -> `80 01 00 03 00 01 82`)
                hi, lo = payload[0], payload[1]
                tuner_map = {
                    (0x03, 0x00): b"\x01\x82",
                    (0x03, 0x01): b"NNNPTW",
                    (0x03, 0x02): b"\x27\x28\x23\x21\x21\x24",
                    (0x03, 0x03): b"\x28\x2e\x32\x35\x3d\x44",
                    (0x03, 0x05): b"\x44\xff\x44\xff\x45\x7f\x44\x5a\x44\x7f\x43\xff",
                    (0x03, 0x08): b"\x78",
                }
                t_data = tuner_map.get((hi, lo), b"\x00")
                return struct.pack(">HBBB", 0x8001, 0x00, hi, lo) + t_data

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

        # Opcode 0x0100: OP_READ (rcmp.py / RcmpReadClient & CPS Read)
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
            if not data and inst > 0:
                # Exact CPS capture behavior when an instance does not exist:
                # 81 00 81 <part:1> <obj:2> <inst:2> 00 00 00 00 00 00 (14 bytes total)
                return struct.pack(">HBBHHHHH", 0x8100, 0x81, part, obj, inst, 0, 0, 0)

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
                data = payload[11:-2]
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
            self._log(f"REQ 0x0103 (OP_PREPARE): {payload.hex()}")
            return struct.pack(">HB", 0x8103, 0x00)

        # Opcode 0x0107 or 0x2011: UnlockSecurity
        # Supports both:
        #   - 1-step unlock (when challenge_security=False and payload < 32B)
        #   - 2-step 32-byte LFSR seed->response challenge (when challenge_security=True
        #     or when client sends a 32-byte scrambled response)
        elif opcode in (0x0107, 0x2011):
            resp_op = opcode | 0x8000
            self._log(f"REQ 0x{opcode:04X} (UnlockSecurity, len={len(payload)}): {payload.hex()}")

            # Check if payload carries a 32-byte scrambled response to our seed
            if len(payload) >= SEED_LEN:
                candidate = payload[-SEED_LEN:]
                expected = unlock_response(self.seed)
                if candidate == expected:
                    session["unlocked"] = True
                    session["challenge_pending"] = False
                    self._log(f"[+] UnlockSecurity LFSR response VERIFIED! Partition 0x81 unlocked.")
                    return struct.pack(">HB", resp_op, 0x00)
                else:
                    self._log(
                        f"[-] UnlockSecurity LFSR mismatch! got={candidate.hex()} expected={expected.hex()}"
                    )
                    if not self.challenge_security:
                        # In permissive capture mode, still unlock so CPS continues its session!
                        session["unlocked"] = True
                        return struct.pack(">HB", resp_op, 0x00)
                    return struct.pack(">HB", resp_op, 0x01)

            # Step 1: Client requested seed
            if self.challenge_security:
                session["challenge_pending"] = True
                self._log(f"RESP 0x{resp_op:04X} (32-byte seed challenge: {self.seed.hex()})")
                # Return status 0x00 + 32-byte seed (or raw 32-byte seed if SEED_OFFSET == 0)
                return struct.pack(">H", resp_op) + self.seed
            else:
                session["unlocked"] = True
                self._log(f"RESP 0x{resp_op:04X} (status 0 = security unlocked for this session)")
                return struct.pack(">HB", resp_op, 0x00)

        # Unknown / default: log prominently and echo with response flag
        else:
            self._log(f"REQ 0x{opcode:04X} (unknown, payload={payload.hex()})")
            resp_op = opcode | 0x8000
            return struct.pack(">HB", resp_op, 0x00)

    def _lookup_object(self, part: int, obj: int, inst: int) -> bytes:
        with self._lock:
            if (part, obj, inst) in self.cpg_data.objects:
                return self.cpg_data.objects[(part, obj, inst)]
            for (p, o, i), data in self.cpg_data.objects.items():
                if p == part and o == obj and (inst == 0 or i == inst):
                    return data
            # Synthesize default identity objects if missing from dump
            if part == PART_CODEPLUG and obj == 0x0047:
                return bytes.fromhex("002e221225010003000000000000")
            if part == PART_TUNING and obj == 0x1079:
                return b"\x00\x08\x03\xe8" + b"\x00" * 102
        return b""


class SerialPppBridge:
    """Responder-side PPP + TCP (:8002) server over a serial port or PTY.

    Allows Motorola CPS / Depot inside a VM or Wine container (connected to a
    virtual COM port) to dial ``CLIENT`` -> ``CLIENTSERVER``, negotiate LCP and
    IPCP (`192.168.128.1` radio <-> `192.168.128.2` host), and open TCP port
    8002 directly into ``VirtualRadioServer.process_record()``.
    """

    def __init__(self, ser, radio_server: VirtualRadioServer):
        self.ser = ser
        self.radio_server = radio_server
        self.running = False
        self._rxbuf = bytearray()
        self._ident = 1
        self._r_seq = 0x2000
        self._c_nxt = 0

    def serve_forever(self) -> None:
        from open_astro.protocol.ppp_link import (
            ACK, FIN, FLAG, LOCAL_IP, P_IP, P_IPCP, P_LCP, PSH, RADIO_IP, RST,
            SYN, _ip, _tcp, _unstuff, ppp_frame,
        )
        self.running = True
        session: Dict[str, Any] = {"unlocked": False, "challenge_pending": False, "peer": ("serial", 0)}
        tcp_buf = bytearray()
        while self.running:
            chunk = self.ser.read(512)
            if not chunk:
                continue
            self._rxbuf.extend(chunk)

            # 1. Answer Windows RAS / CPS "CLIENT" dial-up probe with "CLIENTSERVER"
            if b"CLIENT" in self._rxbuf and FLAG not in self._rxbuf:
                self.radio_server._log("Serial PPP: received CLIENT -> sending CLIENTSERVER")
                self.ser.write(b"CLIENTSERVER")
                self.ser.flush()
                self._rxbuf.clear()
                # Proactively send radio LCP Configure-Request
                magic = b"\x05\x06\x87\x65\x43\x21"
                self.ser.write(ppp_frame(P_LCP, bytes([0x01, 0x01]) + struct.pack(">H", 4 + len(magic)) + magic))
                self.ser.flush()
                continue

            # 2. Process HDLC 0x7E frames
            while True:
                try:
                    i = self._rxbuf.index(FLAG)
                    j = self._rxbuf.index(FLAG, i + 1)
                except ValueError:
                    break
                raw = bytes(self._rxbuf[i + 1:j])
                del self._rxbuf[:j + 1]
                if not raw:
                    continue
                u = _unstuff(raw)
                if len(u) < 4:
                    continue
                body = u[2:] if u[:2] == b"\xff\x03" else u
                if body[0] & 0x01:
                    proto = body[0]
                    pl = body[1:-2]
                else:
                    proto = struct.unpack(">H", body[:2])[0]
                    pl = body[2:-2]

                if proto == P_LCP and len(pl) >= 4:
                    code, ident = pl[0], pl[1]
                    if code == 0x01:  # Configure-Request -> Configure-Ack
                        self.ser.write(ppp_frame(P_LCP, bytes([0x02, ident]) + pl[2:]))
                        self.ser.flush()
                elif proto == P_IPCP and len(pl) >= 4:
                    code, ident = pl[0], pl[1]
                    if code == 0x01:
                        # Reject VJ compression (0x02), Ack IP-Address (0x03)
                        opts = pl[4:]
                        ack, rej = bytearray(), bytearray()
                        k = 0
                        while k + 2 <= len(opts):
                            otype, olen = opts[k], opts[k + 1]
                            if olen < 2 or k + olen > len(opts):
                                break
                            c_opt = opts[k:k + olen]
                            if otype == 0x02:
                                rej.extend(c_opt)
                            elif otype == 0x03 and c_opt[2:6] == b"\x00\x00\x00\x00":
                                # Host asked for IP assignment -> Nak with 192.168.128.2
                                nak = bytes([0x03, 0x06]) + LOCAL_IP
                                self.ser.write(ppp_frame(P_IPCP, bytes([0x03, ident]) + struct.pack(">H", 4 + len(nak)) + nak))
                                self.ser.flush()
                                break
                            else:
                                ack.extend(c_opt)
                            k += olen
                        else:
                            if rej:
                                self.ser.write(ppp_frame(P_IPCP, bytes([0x04, ident]) + struct.pack(">H", 4 + len(rej)) + bytes(rej)))
                            else:
                                self.ser.write(ppp_frame(P_IPCP, bytes([0x02, ident]) + struct.pack(">H", 4 + len(ack)) + bytes(ack)))
                                # Also advertise our own radio IP 192.168.128.1
                                r_ipcp = bytes([0x03, 0x06]) + RADIO_IP
                                self.ser.write(ppp_frame(P_IPCP, bytes([0x01, 0x01]) + struct.pack(">H", 4 + len(r_ipcp)) + r_ipcp))
                            self.ser.flush()
                elif proto in (0x21, P_IP) and len(pl) >= 40:
                    ihl = (pl[0] & 0x0F) * 4
                    if pl[9] != 6:
                        continue
                    tcp = pl[ihl:]
                    sport, dport, seq, ack_num = struct.unpack(">HHII", tcp[:12])
                    flags = tcp[13]
                    data_off = (tcp[12] >> 4) * 4
                    data = tcp[data_off:]
                    if dport != 8002:
                        continue

                    if flags & SYN:
                        self._c_nxt = (seq + 1) & 0xFFFFFFFF
                        syn_ack = _tcp_radio(dport, sport, self._r_seq, self._c_nxt, SYN | ACK, b"")
                        self._r_seq = (self._r_seq + 1) & 0xFFFFFFFF
                        self._ident = (self._ident + 1) & 0xFFFF
                        self.ser.write(ppp_frame(P_IP, _ip(RADIO_IP, LOCAL_IP, 6, syn_ack, self._ident)))
                        self.ser.flush()
                        continue

                    if data:
                        self._c_nxt = (seq + len(data)) & 0xFFFFFFFF
                        tcp_buf.extend(data)
                        # Send TCP ACK
                        ack_seg = _tcp_radio(dport, sport, self._r_seq, self._c_nxt, ACK, b"")
                        self._ident = (self._ident + 1) & 0xFFFF
                        self.ser.write(ppp_frame(P_IP, _ip(RADIO_IP, LOCAL_IP, 6, ack_seg, self._ident)))
                        self.ser.flush()

                        # Process complete RCMP records in tcp_buf
                        while len(tcp_buf) >= 2:
                            rlen = (tcp_buf[0] << 8) | tcp_buf[1]
                            if len(tcp_buf) < 2 + rlen:
                                break
                            rec = bytes(tcp_buf[2:2 + rlen])
                            del tcp_buf[:2 + rlen]
                            resp_pl = self.radio_server.process_record(rec, session)
                            if resp_pl:
                                resp_frame = struct.pack(">H", len(resp_pl)) + resp_pl
                                seg = _tcp_radio(dport, sport, self._r_seq, self._c_nxt, PSH | ACK, resp_frame)
                                self._r_seq = (self._r_seq + len(resp_frame)) & 0xFFFFFFFF
                                self._ident = (self._ident + 1) & 0xFFFF
                                self.ser.write(ppp_frame(P_IP, _ip(RADIO_IP, LOCAL_IP, 6, seg, self._ident)))
                                self.ser.flush()

                    if flags & FIN:
                        self._c_nxt = (seq + 1) & 0xFFFFFFFF
                        fin_ack = _tcp_radio(dport, sport, self._r_seq, self._c_nxt, FIN | ACK, b"")
                        self._r_seq = (self._r_seq + 1) & 0xFFFFFFFF
                        self._ident = (self._ident + 1) & 0xFFFF
                        self.ser.write(ppp_frame(P_IP, _ip(RADIO_IP, LOCAL_IP, 6, fin_ack, self._ident)))
                        self.ser.flush()


def _tcp_radio(sport: int, dport: int, seq: int, ack: int, flags: int,
               payload: bytes, window: int = 8192) -> bytes:
    from open_astro.protocol.ppp_link import LOCAL_IP, RADIO_IP, _cksum
    hdr = bytearray(20)
    struct.pack_into(">HHIIBBHHH", hdr, 0, sport, dport, seq, ack,
                     0x50, flags, window, 0, 0)
    pseudo = RADIO_IP + LOCAL_IP + bytes([0, 6]) + struct.pack(">H", 20 + len(payload))
    struct.pack_into(">H", hdr, 16, _cksum(pseudo + bytes(hdr) + payload))
    return bytes(hdr) + payload


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
  Security:     lock={server.lock_security}, challenge_32b={server.challenge_security}
  Capture JSON: {server.capture_jsonl or 'Disabled'}
  Capture PCAP: {server.pcap_logger.path if server.pcap_logger else 'Disabled'}
  Status:       Active listening on {server.host}:{server.port}
======================================================================
"""
    print(banner.strip(), flush=True)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Virtual ASTRO 25 Radio RCMP Server & Packet Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "codeplug",
        nargs="?",
        default=DEFAULT_CPG,
        help="Path to .cpg or structural .json codeplug",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (0.0.0.0 or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8002, help="Bind TCP port")
    parser.add_argument("--flashcode", help="Override FLASHcode string (e.g. 400008-006000-1)")
    parser.add_argument("--serial", help="Override serial number string (e.g. 721CLZ0655)")
    parser.add_argument("--tun", help="Optional path to .tun tuning partition file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log all RCMP requests and responses")
    parser.add_argument(
        "--lock-security",
        action="store_true",
        help="Refuse partition 0x81 writes until the client completes UnlockSecurity",
    )
    parser.add_argument(
        "--challenge-security",
        action="store_true",
        help="Send a 32-byte seed on 0x0107/0x2011 and verify the LFSR scrambled response",
    )
    parser.add_argument(
        "--seed-hex",
        help="Custom 32-byte seed in hex for UnlockSecurity challenge",
    )
    parser.add_argument(
        "--capture-jsonl",
        help="Write every RCMP request and response record to a JSONL file",
    )
    parser.add_argument(
        "--capture-pcap",
        help="Write synthetic IPv4/TCP (:8001 <-> :8002) packets to a .pcap file",
    )
    parser.add_argument(
        "--ppp-serial",
        help="Also listen for PPP 'CLIENT' dial-up on a serial port or PTY (e.g. /dev/ttyS0 or COM8)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        cpg_data = load_codeplug(
            args.codeplug,
            serial_override=args.serial,
            flashcode_override=args.flashcode,
            tun_path=args.tun,
        )
    except Exception as e:
        print(f"[-] Failed to load codeplug '{args.codeplug}': {e}", file=sys.stderr)
        return 1

    seed = bytes.fromhex(args.seed_hex) if args.seed_hex else DEFAULT_CHALLENGE_SEED
    server = VirtualRadioServer(
        cpg_data=cpg_data,
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        lock_security=args.lock_security,
        challenge_security=args.challenge_security,
        seed=seed,
        capture_jsonl=args.capture_jsonl,
        capture_pcap=args.capture_pcap,
    )

    try:
        server.start()
    except Exception as e:
        print(f"[-] Failed to bind {args.host}:{args.port}: {e}", file=sys.stderr)
        return 1

    if args.ppp_serial:
        import serial
        ser = serial.Serial(args.ppp_serial, 115200, timeout=0.2)
        bridge = SerialPppBridge(ser, server)
        t = threading.Thread(target=bridge.serve_forever, daemon=True)
        t.start()
        print(f"[*] Serial PPP bridge active on {args.ppp_serial}", flush=True)

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
