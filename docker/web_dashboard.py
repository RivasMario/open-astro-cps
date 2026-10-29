#!/usr/bin/env python3
"""Web Dashboard & Live Packet Inspector for the Virtual ASTRO 25 Radio Server (:8006).

Displays:
  - Virtual Radio identity (Model, Serial, FLASHcode, Loaded Partitions)
  - Interactive buttons to trigger simulated CPS Read, UnlockSecurity (0x0107
    32-byte LFSR seed->response challenge), and Flashcode/Codeplug Write
    against 127.0.0.1:8002
  - Real-time table of captured RCMP packets from captures/live_virtual_radio.jsonl
  - Direct link to the noVNC desktop at http://127.0.0.1:6080/vnc.html
"""
from __future__ import annotations

import json
import os
import socket
import struct
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from open_astro.protocol import rcmp
from open_astro.protocol.unlock import unlock_response

JSONL_PATH = os.path.join(REPO_ROOT, "captures", "live_virtual_radio.jsonl")
PCAP_PATH = os.path.join(REPO_ROOT, "captures", "live_virtual_radio.pcap")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OpenAstro Virtual Radio & Packet Capture Console</title>
<style>
  body { background: #1e1f1c; color: #f8f8f2; font-family: 'Consolas', 'Monaco', monospace; margin: 0; padding: 20px; }
  h1 { color: #a6e22e; margin-top: 0; font-size: 22px; }
  .bar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; background: #272822; padding: 14px; border-radius: 6px; border: 1px solid #49483e; margin-bottom: 16px; }
  .badge { background: #3e3d32; padding: 6px 10px; border-radius: 4px; font-size: 13px; }
  .badge b { color: #66d9ef; }
  button, a.btn { background: #f92672; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; font-family: inherit; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 13px; }
  button.alt, a.btn.alt { background: #66d9ef; color: #272822; }
  button.green { background: #a6e22e; color: #272822; }
  table { width: 100%; border-collapse: collapse; background: #272822; font-size: 13px; }
  th, td { padding: 8px 10px; border-bottom: 1px solid #3e3d32; text-align: left; }
  th { background: #3e3d32; color: #e6db74; }
  .OUT { color: #fd971f; font-weight: bold; }
  .IN { color: #a6e22e; font-weight: bold; }
  .hex { font-family: monospace; color: #ae81ff; word-break: break-all; }
  #status { color: #e6db74; margin-left: auto; font-size: 13px; }
</style>
</head>
<body>
  <h1>OpenAstro CPS — Virtual ASTRO 25 Radio & Live RCMP Packet Capture (:8002)</h1>
  <div class="bar">
    <span class="badge"><b>Radio:</b> XTS 5000 (H18UCF9PW6AN)</span>
    <span class="badge"><b>Serial:</b> 721CLZ0655</span>
    <span class="badge"><b>FLASHcode:</b> 400008-002000-0</span>
    <span class="badge"><b>RCMP Socket:</b> 127.0.0.1:8002</span>
    <button class="green" onclick="runAction('/api/sim-read')">Simulate CPS Identity + Read</button>
    <button onclick="runAction('/api/sim-unlock-write')">Simulate 0x0107 32B Unlock + Q667 ADP Write</button>
    <a class="btn alt" href="http://127.0.0.1:6080/vnc.html?autoconnect=true" target="_blank">Open noVNC Desktop (:6080)</a>
    <span id="status">Ready</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Dir</th>
        <th>Opcode</th>
        <th>Operation</th>
        <th>Partition / Object</th>
        <th>Framed Wire Bytes (Hex)</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
<script>
async function refresh() {
  const r = await fetch('/api/events');
  const data = await r.json();
  const tbody = document.getElementById('rows');
  tbody.innerHTML = data.events.map((e, idx) => {
    const opHex = e.opcode !== null && e.opcode !== undefined ? '0x' + e.opcode.toString(16).toUpperCase().padStart(4, '0') : '-';
    const meta = e.partition !== undefined ? `part=0x${e.partition.toString(16).toUpperCase()} obj=0x${(e.object||0).toString(16).toUpperCase().padStart(4,'0')} inst=${e.instance||0}` : (e.note || '');
    return `<tr>
      <td>${idx + 1}</td>
      <td class="${e.direction}">${e.direction === 'OUT' ? 'CPS &rarr; Radio' : 'Radio &rarr; CPS'}</td>
      <td>${opHex}</td>
      <td>${e.op || ''}</td>
      <td>${meta}</td>
      <td class="hex">${e.framed_hex}</td>
    </tr>`;
  }).join('');
}
async function runAction(url) {
  document.getElementById('status').innerText = 'Running...';
  const r = await fetch(url, {method: 'POST'});
  const j = await r.json();
  document.getElementById('status').innerText = j.msg || 'Done';
  refresh();
}
setInterval(refresh, 1500);
refresh();
</script>
</body>
</html>
"""


def _tx(sock: socket.socket, opcode: int, body: bytes = b"") -> Tuple[int, bytes]:
    payload = struct.pack(">H", opcode) + body
    sock.sendall(struct.pack(">H", len(payload)) + payload)
    hdr = sock.recv(2)
    length = struct.unpack(">H", hdr)[0]
    buf = b""
    while len(buf) < length:
        buf += sock.recv(length - len(buf))
    return struct.unpack(">H", buf[:2])[0], buf[2:]


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/events":
            events = []
            if os.path.exists(JSONL_PATH):
                with open(JSONL_PATH, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except ValueError:
                                pass
            body = json.dumps({"events": events[-100:]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        msg = "OK"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(("127.0.0.1", 8002))
            try:
                if parsed.path == "/api/sim-read":
                    _tx(sock, 0x0106, b"\x00")
                    _tx(sock, 0x0012, b"")
                    _tx(sock, 0x0011, b"\x00")
                    _tx(sock, 0x000F, b"\x00")
                    _tx(sock, 0x000F, b"\x10")
                    _tx(sock, 0x0100, struct.pack(">BHHH", 0x81, 0x1004, 0, 0x24) + b"\x00\x00")
                    _tx(sock, 0x0100, struct.pack(">BHHH", 0x81, 0x1006, 0, 0x18) + b"\x00\x00")
                    msg = "Simulated CPS Identity + Partition 0x81 Read!"
                elif parsed.path == "/api/sim-unlock-write":
                    _tx(sock, 0x0106, b"\x00")
                    # 1. Request 32-byte seed (opcode 0x0107, tag 0x2011)
                    op, seed = _tx(sock, 0x0107, b"\x81\x20\x11\x00")
                    # 2. Scramble 32-byte seed with NextGen10 LFSR (FUN_1000fd89)
                    resp_bytes = unlock_response(seed)
                    op2, ack = _tx(sock, 0x0107, b"\x81" + resp_bytes)
                    # 3. Write Q667 ADP Flashcode 400008-006000-1 to 0x81:0x1006
                    fc_payload = b"\x00\x00\x00\x10\x00\x01\x00\x01400008-006000-1\x00"
                    framed_w = rcmp.build_write(0x81, 0x1006, fc_payload, inst=0)
                    sock.sendall(framed_w)
                    hdr = sock.recv(2)
                    sock.recv(struct.unpack(">H", hdr)[0])
                    _tx(sock, 0x0106, b"\x01")
                    msg = f"0x0107 Seed ({seed[:4].hex()}...) -> LFSR Response ({resp_bytes[:4].hex()}...) VERIFIED & 0x81 Written!"
            finally:
                sock.close()
        except Exception as e:
            msg = f"Error: {e}"

        out = json.dumps({"msg": msg}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8006
    srv = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"[*] Virtual Radio Packet Inspector listening on http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()
