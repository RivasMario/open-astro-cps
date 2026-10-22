"""
OpenAstro Modern GUI Backend Server.
Provides local REST API and serves the single-page HTML5/CSS3 application.
"""
import http.server
import socketserver
import json
import os
import sys
import webbrowser
import threading
from typing import Dict, Any, Optional

from ..parsers.json_parser import JsonParser
from ..models import RadioCodeplug, Zone, Channel
from ..protocol.serial_link import RadioSerialLink
from ..protocol.ppp_flasher import AstroPppFlasher

ACTIVE_CODEPLUG_PATH = "comm_pair_codeplug.json"
DEFAULT_PORT = 8080


class OpenAstroApiHandler(http.server.SimpleHTTPRequestHandler):
    """Handles REST API requests and serves static web assets."""
    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(os.path.dirname(__file__), "web")
        super().__init__(*args, directory=static_dir, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            self.send_json_response(self.get_radio_status())
        elif self.path.startswith("/api/codeplug"):
            self.send_json_response(self.get_codeplug_data())
        elif self.path.startswith("/api/ports"):
            self.send_json_response(self.get_ports())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/codeplug"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            self.save_codeplug_data(data)
            self.send_json_response({"status": "saved", "message": "Codeplug saved successfully"})
        elif self.path.startswith("/api/write"):
            result = self.trigger_write()
            self.send_json_response(result)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def get_ports(self) -> Dict[str, Any]:
        detected = RadioSerialLink.auto_detect_radio_port()
        return {
            "detected_radio_port": detected,
            "detected_kvl_port": RadioSerialLink.auto_detect_kvl_port()
        }

    def get_radio_status(self) -> Dict[str, Any]:
        port = RadioSerialLink.auto_detect_radio_port()
        status = {
            "online": False,
            "port": port,
            "serial_number": None,
            "model_number": None,
            "firmware_version": None,
            "family": None
        }
        if port:
            try:
                import serial
                s = serial.Serial(port, 19200, timeout=0.15)
                s.dtr = True
                s.rts = True
                s.write(b"\rAT\r")
                r = s.read(100)
                if b"OK" in r:
                    status["online"] = True
                    s.write(b"AT&V\r")
                    atv = s.read(512).decode("ascii", errors="ignore")
                    for line in atv.splitlines():
                        if ":" in line and not line.startswith("AT"):
                            k, v = line.split(":", 1)
                            k = k.strip().upper()
                            v = v.strip()
                            if k == "SERIAL": status["serial_number"] = v
                            elif k == "MODEL": status["model_number"] = v
                            elif k == "RADIO": status["family"] = v
                s.close()
            except Exception as e:
                status["error"] = str(e)
        return status

    def get_codeplug_data(self) -> Dict[str, Any]:
        if os.path.exists(ACTIVE_CODEPLUG_PATH):
            with open(ACTIVE_CODEPLUG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": "Codeplug file not found"}

    def save_codeplug_data(self, data: Dict[str, Any]) -> None:
        with open(ACTIVE_CODEPLUG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def trigger_write(self) -> Dict[str, Any]:
        port = RadioSerialLink.auto_detect_radio_port() or "COM7"
        try:
            with AstroPppFlasher(port=port) as flasher:
                id_info = flasher.query_at_identity()
                base_cpg = "backups/Radio1_205CMB2249_codeplug.cpg"
                if id_info.get("serial_number") == "205CFR2930":
                    base_cpg = "backups/205CFR2930.cpg"
                
                if not flasher.start_ppp_link():
                    return {"success": False, "error": "Failed to establish PPP link with radio"}
                if not flasher.tcp_connect(8002):
                    return {"success": False, "error": "Failed to connect to Port 8002 on radio"}

                success = flasher.flash_codeplug(base_cpg)
                return {
                    "success": success,
                    "radio_serial": id_info.get("serial_number"),
                    "radio_model": id_info.get("radio_model"),
                    "message": "Radio successfully programmed!"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


def run_gui(host: str = "127.0.0.1", port: int = DEFAULT_PORT, no_browser: bool = False):
    """Start local GUI HTTP server and launch browser."""
    print("=" * 60)
    print(" OpenAstro CPS Modern GUI (Pure Python & Web Architecture)")
    print(f" URL: http://{host}:{port}")
    print(" Zero reliance on Motorola software or legacy Windows XP DLLs")
    print("=" * 60)

    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    server = ReusableServer((host, port), OpenAstroApiHandler)
    url = f"http://{host}:{port}"

    if not no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down OpenAstro GUI server.")
        server.server_close()
