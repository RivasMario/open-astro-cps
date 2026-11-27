"""Local OpenAstro CPS Web App (http://127.0.0.1:8765).

Provides a browser UI over open-astro-cps's real parsers, FLASHcode calculator,
and simulated/network RCMP transport (Partition 0x82 strictly blocked).
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from open_astro.models.flashcode import (
    FEATURE_FLAGS,
    PROFILES,
    FlashcodeDecoder,
    format_flashcode,
    set_feature,
    software_feature_slugs,
)
from open_astro.parsers.cpg_decode import CpgDecoder, CpgParser
from tools.mock_radio_capture import MockRadioServer, _frame_with_crc, _load_cpg_objects

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUPS_DIR = REPO_ROOT / "backups"

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OpenAstro CPS — Local Web App</title>
  <style>
    :root { --bg:#0c0e12; --panel:#14171e; --border:#2a3140; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --yellow:#d29922; --red:#f85149; }
    * { box-sizing:border-box; }
    body { margin:0; padding:24px; font-family:"Segoe UI",-apple-system,sans-serif; background:var(--bg); color:var(--text); }
    .wrap { max-width:1200px; margin:0 auto; }
    h1 { margin:0 0 4px; font-size:24px; color:#f0f6fc; }
    .sub { color:var(--muted); font-size:13px; margin-bottom:20px; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    @media (max-width:900px) { .grid { grid-template-columns:1fr; } }
    .card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px; margin-bottom:16px; }
    .card h2 { margin:0 0 12px; font-size:15px; text-transform:uppercase; letter-spacing:0.6px; color:var(--accent); }
    select, input, button { background:#0b0d11; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:13px; }
    button { background:#1f6feb; border-color:#388bfd; font-weight:600; cursor:pointer; }
    button:hover { background:#388bfd; }
    button.sec { background:#21262d; border-color:#30363d; }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:10px; }
    table { width:100%; border-collapse:collapse; font-size:13px; margin-top:8px; }
    th, td { text-align:left; padding:7px 8px; border-bottom:1px solid #222733; }
    th { color:var(--muted); font-size:12px; }
    pre { background:#090b0f; border:1px solid var(--border); border-radius:6px; padding:10px; font-size:12px; overflow:auto; max-height:260px; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:700; }
    .ok { background:rgba(63,185,80,0.18); color:var(--green); }
    .lock { background:rgba(248,81,73,0.18); color:var(--red); }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>OpenAstro CPS — Local Web App</h1>
    <div class="sub">Cross-Platform Codeplug Inspector, FLASHcode Builder &amp; Simulated/Network RCMP Flasher · <span class="pill lock">0x82 Firewall Active</span></div>

    <div class="grid">
      <div class="card">
        <h2>1. Codeplug Inspector (.cpg)</h2>
        <div class="row">
          <select id="cpgSelect"></select>
          <button onclick="loadCpg()">Load Codeplug</button>
        </div>
        <div id="cpgSummary" style="font-size:13px;color:var(--muted);margin-bottom:8px;">Select a backup .cpg to decode live.</div>
        <div style="max-height:280px;overflow:auto;">
          <table><thead><tr><th>Zone / Ch</th><th>Name</th><th>RX (MHz)</th><th>TX (MHz)</th><th>Mode</th></tr></thead><tbody id="chanRows"></tbody></table>
        </div>
      </div>

      <div class="card">
        <h2>2. FLASHcode Builder (Partition 0x81)</h2>
        <div class="row">
          <select id="fcProfile">
            <option value="recommended">recommended (P25 + FPP + ADP)</option>
            <option value="max-nonucm" selected>max-nonucm (All 40 Software Features)</option>
            <option value="max-ucm">max-ucm (All 48 Bits incl. UCM)</option>
          </select>
          <input id="fcStart" value="000008-002410-2" style="width:160px;" />
          <button onclick="calcFlashcode()">Calculate</button>
        </div>
        <pre id="fcOut">Click Calculate to generate verified Luhn mod-10 FLASHcode...</pre>
      </div>
    </div>

    <div class="card">
      <h2>3. Simulated Radio Flash &amp; ADP Key Persistence Test</h2>
      <div class="row">
        <label style="font-size:13px;">ADP Key (10 hex chars):</label>
        <input id="adpKey" value="a1b2c3d4e5" style="width:140px;font-family:Consolas,monospace;" />
        <button onclick="runSim()">Run Simulated Flash + Reboot + Read-Back</button>
      </div>
      <pre id="simOut">Ready. Uses the selected .cpg backup in a simulated RCMP radio (0x80 RW, 0x81 RW-Locked, 0x82 Blocked).</pre>
    </div>
  </div>

  <script>
    async function init() {
      const res = await fetch('/api/cpgs');
      const data = await res.json();
      const sel = document.getElementById('cpgSelect');
      data.files.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f; opt.textContent = f;
        sel.appendChild(opt);
      });
      if (data.files.length) loadCpg();
      calcFlashcode();
    }

    async function loadCpg() {
      const file = document.getElementById('cpgSelect').value;
      const res = await fetch('/api/decode?file=' + encodeURIComponent(file));
      const d = await res.json();
      document.getElementById('cpgSummary').innerHTML =
        `<strong>${d.radio_model || 'ASTRO 25'}</strong> · Serial: <code>${d.serial || '?'}</code> · Zones: <strong>${d.zones.length}</strong> · Objects: <strong>${d.object_count}</strong>`;
      const tbody = document.getElementById('chanRows');
      tbody.innerHTML = '';
      d.zones.forEach(z => {
        (z.channels || []).forEach(c => {
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>${z.name}</td><td>${c.name || ''}</td><td>${c.rx_freq || ''}</td><td>${c.tx_freq || ''}</td><td>${c.mode || ''}</td>`;
          tbody.appendChild(tr);
        });
      });
    }

    async function calcFlashcode() {
      const profile = document.getElementById('fcProfile').value;
      const start = document.getElementById('fcStart').value;
      const res = await fetch(`/api/flashcode?profile=${encodeURIComponent(profile)}&start=${encodeURIComponent(start)}`);
      const d = await res.json();
      document.getElementById('fcOut').textContent =
        `From: ${d.from}\nTo:   ${d.to}  (Luhn check OK)\nEnabled (${d.enabled.length}):\n  + ` + d.enabled.join('\n  + ') +
        `\n\nReplay flag:\n  --edit 81:1006:0:${d.edit_hex}`;
    }

    async function runSim() {
      const file = document.getElementById('cpgSelect').value;
      const key = document.getElementById('adpKey').value;
      const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file, key})
      });
      const d = await res.json();
      document.getElementById('simOut').textContent = JSON.stringify(d, null, 2);
    }

    init();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            raw = HTML_PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if parsed.path == "/api/cpgs":
            files = sorted(p.name for p in BACKUPS_DIR.glob("*.cpg")) if BACKUPS_DIR.exists() else []
            self._send_json({"files": files})
            return

        if parsed.path == "/api/decode":
            qs = parse_qs(parsed.query)
            fname = qs.get("file", [""])[0]
            target = (BACKUPS_DIR / fname).resolve()
            if not target.is_file() or target.parent != BACKUPS_DIR.resolve():
                self._send_json({"error": "Invalid file"}, 400)
                return
            try:
                dec = CpgDecoder(str(target))
                cp = dec.decode()
                parser = CpgParser(str(target))
                zones = []
                for z in cp.zones:
                    chans = [{
                        "name": c.name,
                        "rx_freq": f"{c.rx_freq_mhz:.5f}" if getattr(c, "rx_freq_mhz", None) else "",
                        "tx_freq": f"{c.tx_freq_mhz:.5f}" if getattr(c, "tx_freq_mhz", None) else "",
                        "mode": getattr(c, "mode", ""),
                    } for c in z.channels]
                    zones.append({"name": z.name, "channels": chans})
                self._send_json({
                    "radio_model": getattr(cp, "model", "ASTRO 25"),
                    "serial": getattr(cp, "serial", "?"),
                    "zones": zones,
                    "object_count": len(parser.objects()),
                })
            except Exception as exc:
                self._send_json({"error": str(exc), "zones": [], "object_count": 0}, 200)
            return

        if parsed.path == "/api/flashcode":
            qs = parse_qs(parsed.query)
            profile = qs.get("profile", ["max-nonucm"])[0]
            start = qs.get("start", ["000008-002410-2"])[0]
            payload = start.replace("-", "")[:12].ljust(12, "0")
            if profile == "max-ucm":
                slugs = list(FEATURE_FLAGS.keys())
            elif profile == "recommended":
                slugs = list(PROFILES["recommended"])
            else:
                slugs = software_feature_slugs()
            for slug in slugs:
                if slug in FEATURE_FLAGS:
                    nib, bit = FEATURE_FLAGS[slug][:2]
                    payload = set_feature(payload, nib, bit, True)
            to_fc = format_flashcode(payload)
            decoded_fc = FlashcodeDecoder().decode(to_fc)
            enabled = [getattr(f, "name", str(f)) for f in decoded_fc]
            ascii_fc = to_fc.encode("ascii") + b"\x00"
            self._send_json({
                "from": start,
                "to": to_fc,
                "enabled": enabled,
                "edit_hex": ascii_fc.hex(),
            })
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/simulate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        req = json.loads(self.rfile.read(length).decode("utf-8"))
        fname = req.get("file", "205CFR2930.cpg")
        key_hex = req.get("key", "a1b2c3d4e5").strip()
        key_bytes = bytes.fromhex(key_hex)[:5].ljust(5, b"\x00")
        target = (BACKUPS_DIR / fname).resolve()
        if not target.is_file() or target.parent != BACKUPS_DIR.resolve():
            self._send_json({"error": "Invalid .cpg file"}, 400)
            return

        objs = _load_cpg_objects(target)
        srv = MockRadioServer("127.0.0.1", 0, objs, None)
        t = threading.Thread(target=lambda: (srv.serve_once(), srv.serve_once()), daemon=True)
        t.start()

        def xfer(cli: socket.socket, payload: bytes) -> bytes:
            cli.sendall(_frame_with_crc(payload))
            rlen = struct.unpack(">H", cli.recv(2))[0]
            return cli.recv(rlen)

        with socket.create_connection(("127.0.0.1", srv.bound_port), timeout=5) as cli:
            xfer(cli, bytes.fromhex("010600"))
            xfer(cli, bytes.fromhex("0102"))
            xfer(cli, bytes.fromhex("010380000201f4"))
            xfer(cli, bytes.fromhex("010180005d0000000500000005") + key_bytes)
            r82 = xfer(cli, bytes.fromhex("01018200010000000200000002cafe"))
            xfer(cli, bytes.fromhex("010601"))

        with socket.create_connection(("127.0.0.1", srv.bound_port), timeout=5) as cli:
            xfer(cli, bytes.fromhex("010600"))
            adp_back = xfer(cli, bytes.fromhex("010080005d000000050000"))[12:-2]
            ser_back = xfer(cli, bytes.fromhex("01008110040000000a0000"))[12:-2]
            xfer(cli, bytes.fromhex("010601"))

        srv.close()
        self._send_json({
            "cpg": fname,
            "objects_loaded": len(objs),
            "partition_0x82_blocked": r82[2] == 0x01,
            "adp_key_written": key_bytes.hex(),
            "adp_key_post_reboot": adp_back.hex(),
            "persisted": adp_back == key_bytes,
            "serial_raw_hex": ser_back.hex(),
        })


def main() -> None:
    ap = argparse.ArgumentParser(description="OpenAstro CPS Local Web App")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"OpenAstro Web App running at {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
