"""
Unit tests for cleanroom_flasher/rcmp_socket_transport.py and cleanroom_flasher/kvl_probe.py.
"""
import os
import socket
import struct
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cleanroom_flasher.rcmp_socket_transport import (
    ACCESS_READ_ONLY,
    ACCESS_READ_WRITE,
    ACCESS_READ_WRITE_LOCKED,
    OP_ENTER_MODE,
    OP_LOCK,
    OP_QUERY_UUID,
    OP_READ_ISH,
    OP_UNLOCK,
    OP_WRITE_ISH,
    RESP_FLAG,
    RcmpError,
    RcmpSocketTransport,
    detect_radio_ip,
    partition_is_writable,
    serialize_rcmp_ish_read,
)
from cleanroom_flasher.kvl_probe import (
    CMD_READ,
    CMD_SELF_TEST,
    ESC,
    ESC_PLACEHOLDER,
    READ_AP_VER,
    READ_FW_VER,
    READ_HW_REV,
    READ_MODEL_ID,
    READ_SER_NUM,
    RSP_READ,
    RSP_SELF_TEST,
    SOM_EOM,
    SOM_EOM_PLACEHOLDER,
    XTS_RADIO_VIDPID,
    candidate_ports,
    frame,
    identify,
    unframe,
    xfer,
)


class TestRcmpSocketTransport(unittest.TestCase):
    def test_partition_is_writable(self):
        self.assertFalse(partition_is_writable(ACCESS_READ_ONLY))
        self.assertTrue(partition_is_writable(ACCESS_READ_WRITE))
        self.assertFalse(partition_is_writable(ACCESS_READ_WRITE_LOCKED))
        self.assertFalse(partition_is_writable(99))

    def test_frame_layout(self):
        # Empty payload -> length = 2, opcode = 0x000C
        f = RcmpSocketTransport._frame(OP_UNLOCK, b"")
        self.assertEqual(f, b"\x00\x02\x00\x0c")

        # Non-empty payload -> length = 2 + len(payload)
        payload = b"\xde\xad\xbe\xef"
        f2 = RcmpSocketTransport._frame(OP_READ_ISH, payload)
        self.assertEqual(f2[:4], struct.pack(">HH", 6, OP_READ_ISH))
        self.assertEqual(f2[4:], payload)

    def test_serialize_rcmp_ish_read(self):
        tlv = serialize_rcmp_ish_read(partition=0x80, item_id=2, offset=0, length=166)
        self.assertEqual(tlv[0], 1)
        self.assertEqual(tlv[1], 0x80)
        self.assertEqual(tlv[2], 0)
        self.assertEqual(struct.unpack("!H", tlv[3:5])[0], 2)
        self.assertEqual(tlv[5], 0)
        self.assertEqual(struct.unpack("!H", tlv[6:8])[0], 0)
        self.assertEqual(tlv[8], 0)
        self.assertEqual(struct.unpack("!H", tlv[9:11])[0], 166)

    def test_send_and_probe_over_socketpair(self):
        s_client, s_server = socket.socketpair()
        try:
            transport = RcmpSocketTransport(radio_ip="192.168.128.1", port=8002)
            transport.sock = s_client

            fake_uuid = bytes(range(1, 17))
            fake_ish_data = b"H46UCF9PW6AN\x00205CFR2930\x00"

            def radio_responder():
                # 1. Receive OP_UNLOCK (0x000C)
                hdr = s_server.recv(2)
                (length,) = struct.unpack(">H", hdr)
                req = s_server.recv(length)
                (op,) = struct.unpack(">H", req[:2])
                self.assertEqual(op, OP_UNLOCK)
                # Send response: [len=3][resp_op=0x800C][status=0x00]
                s_server.sendall(struct.pack(">HHB", 3, RESP_FLAG | OP_UNLOCK, 0x00))

                # 2. Receive OP_QUERY_UUID (0x0012)
                hdr = s_server.recv(2)
                (length,) = struct.unpack(">H", hdr)
                req = s_server.recv(length)
                (op,) = struct.unpack(">H", req[:2])
                self.assertEqual(op, OP_QUERY_UUID)
                s_server.sendall(
                    struct.pack(">HHB", 3 + len(fake_uuid), RESP_FLAG | OP_QUERY_UUID, 0x00)
                    + fake_uuid
                )

                # 3. Receive OP_READ_ISH (0x0100)
                hdr = s_server.recv(2)
                (length,) = struct.unpack(">H", hdr)
                req = s_server.recv(length)
                (op,) = struct.unpack(">H", req[:2])
                self.assertEqual(op, OP_READ_ISH)
                s_server.sendall(
                    struct.pack(">HHB", 3 + len(fake_ish_data), RESP_FLAG | OP_READ_ISH, 0x00)
                    + fake_ish_data
                )

            t = threading.Thread(target=radio_responder, daemon=True)
            t.start()

            res = transport.probe(read_ish_id=2, partition=0x80, read_len=166)
            t.join(timeout=2.0)

            self.assertEqual(res["unlock_status"], 0x00)
            self.assertEqual(res["uuid"], fake_uuid.hex())
            self.assertIn("read_ish", res)
            self.assertEqual(res["read_ish"]["item_id"], 2)
            self.assertEqual(res["read_ish"]["status"], 0x00)
            self.assertEqual(res["read_ish"]["data_hex"], fake_ish_data.hex())
        finally:
            s_client.close()
            s_server.close()

    def test_send_opcode_mismatch_raises(self):
        s_client, s_server = socket.socketpair()
        try:
            transport = RcmpSocketTransport(radio_ip="192.168.128.1")
            transport.sock = s_client
            # Pre-load a response with wrong opcode (0x8099 instead of 0x800C)
            s_server.sendall(struct.pack(">HHB", 3, 0x8099, 0x00))
            with self.assertRaises(RcmpError) as ctx:
                transport.unlock()
            self.assertIn("opcode mismatch", str(ctx.exception))
        finally:
            s_client.close()
            s_server.close()

    def test_write_methods_are_hard_gated(self):
        transport = RcmpSocketTransport(radio_ip="192.168.128.1")
        with self.assertRaises(RcmpError):
            transport.write_ish(b"test")
        with self.assertRaises(RcmpError):
            transport.enter_write_mode()
        with self.assertRaises(RcmpError):
            transport.commit(b"\x00" * 16)

    @patch("cleanroom_flasher.rcmp_socket_transport.subprocess.run")
    def test_detect_radio_ip_parses_ppp0_peer(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="4: ppp0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500\n"
                   "    inet 192.168.128.2 peer 192.168.128.1/32 scope global ppp0\n"
        )
        self.assertEqual(detect_radio_ip("ppp0"), "192.168.128.1")


class TestKvlProbe(unittest.TestCase):
    def test_frame_and_unframe_plain(self):
        payload = bytes([CMD_READ, READ_FW_VER])
        framed = frame(payload)
        self.assertEqual(framed[0], SOM_EOM)
        self.assertEqual(framed[-1], SOM_EOM)
        self.assertEqual(framed[1:-1], payload)

        unframed = unframe(framed)
        self.assertEqual(unframed, [payload])

    def test_frame_and_unframe_with_escapes(self):
        # Payload containing SOM_EOM (0x61), SOM_EOM_PLACEHOLDER (0x62), ESC (0x63), ESC_PLACEHOLDER (0x64)
        payload = bytes([0x11, SOM_EOM, SOM_EOM_PLACEHOLDER, ESC, ESC_PLACEHOLDER, 0xFF])
        framed = frame(payload)
        # Inner bytes must not contain raw SOM_EOM (0x61)
        self.assertNotIn(SOM_EOM, framed[1:-1])
        # Must round-trip cleanly
        unframed = unframe(framed)
        self.assertEqual(unframed, [payload])

    def test_unframe_multiple_packets_with_leading_noise(self):
        p1 = bytes([RSP_READ, READ_FW_VER, 1, 2, 0])
        p2 = bytes([RSP_SELF_TEST, 0x00])
        stream = b"\x00\xffnoise" + frame(p1) + b"\xfe" + frame(p2)
        self.assertEqual(unframe(stream), [p1, p2])

    @patch("cleanroom_flasher.kvl_probe.serial.tools.list_ports.comports")
    def test_candidate_ports_excludes_xts_radio_vidpid(self, mock_comports):
        radio_port = MagicMock()
        radio_port.device = "/dev/ttyACM0"
        radio_port.vid, radio_port.pid = XTS_RADIO_VIDPID

        pico_port = MagicMock()
        pico_port.device = "/dev/ttyACM1"
        pico_port.vid, pico_port.pid = (0x2E8A, 0x000A)

        clone_port = MagicMock()
        clone_port.device = "/dev/ttyUSB0"
        clone_port.vid, clone_port.pid = (0x10C4, 0xEA60)

        mock_comports.return_value = [radio_port, pico_port, clone_port]

        cands = candidate_ports(None)
        self.assertNotIn("/dev/ttyACM0", cands)
        self.assertEqual(cands, ["/dev/ttyACM1", "/dev/ttyUSB0"])

    @patch("cleanroom_flasher.kvl_probe.serial.Serial")
    def test_identify_adapter_protocol(self, mock_serial_cls):
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser

        # Prepare queued responses for FW_VER, AP_VER, HW_REV, MODEL_ID, SER_NUM, SELF_TEST
        responses = [
            frame(bytes([RSP_READ, READ_FW_VER, 1, 3, 0])),
            frame(bytes([RSP_READ, READ_AP_VER, 1, 0, 0])),
            frame(bytes([RSP_READ, READ_HW_REV, 2, 1])),
            frame(bytes([RSP_READ, READ_MODEL_ID, 0x01])),
            frame(bytes([RSP_READ, READ_SER_NUM, 0xCA, 0xFE, 0xBA, 0xBE])),
            frame(bytes([RSP_SELF_TEST, 0x00])),
        ]

        def fake_read(_n):
            if responses:
                return responses.pop(0)
            return b""

        mock_ser.in_waiting = 16
        mock_ser.read.side_effect = fake_read

        info = identify("/dev/ttyACM1", run_self_test=True)
        self.assertIsNotNone(info)
        self.assertEqual(info["port"], "/dev/ttyACM1")
        self.assertEqual(info["fw"], "1.3.0")
        self.assertEqual(info["ap"], "1.0.0")
        self.assertEqual(info["hw"], "2.1")
        self.assertEqual(info["model_id"], 1)
        self.assertEqual(info["serial"], "cafebabe")
        self.assertEqual(info["self_test"], "pass")


if __name__ == "__main__":
    unittest.main()
