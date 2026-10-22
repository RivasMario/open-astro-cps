"""
Unit tests for OpenAstro CPS Modern GUI backend server and REST endpoints.
"""
import unittest
import json
import urllib.request
import threading
import time
import socketserver
from open_astro.gui.server import OpenAstroApiHandler


class TestOpenAstroGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class ReusableServer(socketserver.TCPServer):
            allow_reuse_address = True

        cls.port = 18088
        cls.server = ReusableServer(("127.0.0.1", cls.port), OpenAstroApiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_api_status_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("online", data)
        self.assertIn("port", data)

    def test_api_ports_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/ports"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("detected_radio_port", data)
        self.assertIn("detected_kvl_port", data)

    def test_api_codeplug_get(self):
        url = f"http://127.0.0.1:{self.port}/api/codeplug"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("zones", data)
        self.assertIn("serial_number", data)

    def test_static_index_html(self):
        url = f"http://127.0.0.1:{self.port}/index.html"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        html = req.read().decode("utf-8")
        self.assertIn("OpenAstro CPS", html)
        self.assertIn("channel-table", html)


if __name__ == "__main__":
    unittest.main()
