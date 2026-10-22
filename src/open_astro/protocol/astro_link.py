"""
Motorola ASTRO 25 Serial Programming & Flashing Protocol (XTS 2500, XTS 5000, PRC-153).
Implements SB9600 framing, OBAR (On-Board Auto-Recovery), and memory block transfers.
"""
import time
from typing import Optional, Dict, Any, List
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .framing import PacketFramer
from ..models import RadioCodeplug, Zone, Channel, EncryptionKey

class AstroRadioLink:
    """
    Communicates with Motorola ASTRO 25 series radios over serial programming cables.
    Default: 19200 baud, 8N1.
    """
    # Standard SB9600 / ASTRO 25 Opcodes
    OPCODE_NULL = 0x00
    OPCODE_PRGM_REQ = 0x01       # Enter programming mode
    OPCODE_STATUS_PING = 0x14    # Radio ping / status query
    OPCODE_RADIO_INFO = 0x11     # Query radio serial, model, flashcode
    OPCODE_READ_BLOCK = 0x30     # Read memory block
    OPCODE_WRITE_BLOCK = 0x31    # Write memory block
    OPCODE_RESTART = 0x15        # Reboot radio / exit programming mode

    # SBEP Opcodes (Serial Bus Expanded Protocol)
    SBEP_EXIT = 0x10
    SBEP_READ_DATA = 0x11
    SBEP_WRITE_DATA = 0x17
    SBEP_REPLY_DATA = 0x80
    SBEP_WRITE_ACK = 0x84
    SBEP_ACK = 0x50
    SBEP_NAK = 0x60

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.in_prgm_mode = False
        self.in_sbep_mode = False

    def connect(self) -> None:
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial is required for hardware communication. Run: pip install pyserial")
        self.connection = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
            write_timeout=0.5
        )
        # Assert control lines for ribless USB level shifters & OEM RKN4105 USB cable
        self.connection.dtr = True
        self.connection.rts = True
        time.sleep(0.05)

    def disconnect(self) -> None:
        if self.connection and self.connection.is_open:
            if self.in_sbep_mode:
                try:
                    self.exit_sbep_mode()
                except Exception:
                    pass
            if self.in_prgm_mode:
                try:
                    self.exit_programming_mode()
                except Exception:
                    pass
            self.connection.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def send_at_command(self, cmd: str, wait: float = 0.25) -> str:
        """Send an AT command to an ASTRO 25 radio over USB (0CAD:1001) and return ASCII response."""
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")
        self.connection.reset_input_buffer()
        self.connection.write((cmd.strip() + "\r").encode("ascii"))
        self.connection.flush()
        time.sleep(wait)
        raw = self.connection.read(self.connection.in_waiting or 512)
        return raw.decode("ascii", errors="ignore")

    def query_at_info(self) -> Dict[str, str]:
        """
        Query Motorola ASTRO 25 radio identity via native USB AT&V and ATI commands.
        Supported on RKN4105 OEM USB cables (USB VID:PID 0CAD:1001).
        """
        info: Dict[str, str] = {}
        try:
            atv = self.send_at_command("AT&V", wait=0.3)
            if "MODEL:" in atv or "SERIAL:" in atv or "RADIO:" in atv:
                for line in atv.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("AT"):
                        k, v = line.split(":", 1)
                        k = k.strip().upper()
                        v = v.strip()
                        if k == "RADIO":
                            info["radio_family"] = v
                        elif k == "MODEL":
                            info["radio_model"] = v
                        elif k == "SERIAL":
                            info["serial_number"] = v
                        elif k == "SECURE":
                            info["secure_version"] = v
                        elif k == "WV304":
                            info["ppp_ip"] = v
                        elif k == "PORT":
                            info["port_mode"] = v
                ati2 = self.send_at_command("ATI2", wait=0.2)
                for line in ati2.splitlines():
                    if "Host Version:" in line:
                        info["host_version"] = line.split(":", 1)[1].strip()
                ati3 = self.send_at_command("ATI3", wait=0.2)
                for line in ati3.splitlines():
                    if "DSP Version:" in line:
                        info["dsp_version"] = line.split(":", 1)[1].strip()
        except Exception:
            pass
        return info

    def enter_datlcl_ppp_mode(self, high_speed_baud: int = 115200) -> bool:
        """
        Execute the Motorola ASTRO 25 CPS local data link handshake:
        AT#DATLCL=1 -> OK -> AT+IPR=115200 -> OK -> CLIENT...
        """
        r1 = self.send_at_command("AT#DATLCL=1", wait=0.3)
        if "OK" not in r1 and "CLIENT" not in r1:
            return False
        if high_speed_baud != self.baudrate:
            r2 = self.send_at_command(f"AT+IPR={high_speed_baud}", wait=0.3)
            if "OK" in r2 or "CLIENT" in r2:
                self.connection.baudrate = high_speed_baud
                self.baudrate = high_speed_baud
        return True

    def enter_sbep_over_at(self) -> bool:
        """Switch ASTRO 25 USB interface from AT command parser into SBEP binary mode."""
        resp = self.send_at_command("AT#SBEP", wait=0.25)
        if "OK" in resp:
            self.in_sbep_mode = True
            return True
        return False

    def exit_sbep_mode(self) -> None:
        """Send SBEP Exit opcode (0x10) and de-assert control lines."""
        if not self.connection or not self.connection.is_open:
            return
        pkt = PacketFramer.build_sbep_packet(self.SBEP_EXIT, None)
        try:
            self.connection.write(pkt)
            self.connection.flush()
        except Exception:
            pass
        self.in_sbep_mode = False

    def sbep_read_memory(self, address: int, length: int = 0x20) -> Optional[bytes]:
        """Read a block of memory (up to 255 bytes) at 24-bit address via SBEP opcode 0x11."""
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")
        req_data = bytes([
            length & 0xFF,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF
        ])
        pkt = PacketFramer.build_sbep_packet(self.SBEP_READ_DATA, req_data)
        self.connection.reset_input_buffer()
        self.connection.write(pkt)
        self.connection.flush()

        raw = self.connection.read(length + 16)
        if not raw:
            return None
        # Strip local bus echo if present
        if raw.startswith(pkt):
            raw = raw[len(pkt):]
        # Check SBEP ACK (0x50)
        if raw and raw[0] == self.SBEP_ACK:
            raw = raw[1:]
        parsed = PacketFramer.parse_sbep_packet(raw)
        if not parsed or parsed["opcode"] != self.SBEP_REPLY_DATA:
            return None
        payload = parsed["payload"]
        if len(payload) < 3 + length:
            return None
        return payload[3:3 + length]

    def sbep_write_memory(self, address: int, data: bytes) -> bool:
        """Write a block of memory at 24-bit address via SBEP opcode 0x17."""
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")
        req_data = bytes([
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF
        ]) + data
        pkt = PacketFramer.build_sbep_packet(self.SBEP_WRITE_DATA, req_data)
        self.connection.reset_input_buffer()
        self.connection.write(pkt)
        self.connection.flush()

        raw = self.connection.read(32)
        if raw.startswith(pkt):
            raw = raw[len(pkt):]
        if raw and raw[0] == self.SBEP_ACK:
            raw = raw[1:]
        parsed = PacketFramer.parse_sbep_packet(raw)
        return bool(parsed and parsed["opcode"] == self.SBEP_WRITE_ACK)

    def send_packet(self, opcode: int, payload: bytes = b"", timeout: Optional[float] = None) -> Optional[dict]:
        """Builds, sends, and waits for a validated response packet."""
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")

        pkt = PacketFramer.build_packet(opcode, payload)
        self.connection.reset_input_buffer()
        self.connection.write(pkt)
        self.connection.flush()

        wait_time = timeout or self.timeout
        start_time = time.time()
        buf = bytearray()
        while time.time() - start_time < wait_time:
            chunk = self.connection.read(self.connection.in_waiting or 1)
            if chunk:
                buf.extend(chunk)
                parsed = PacketFramer.parse_packet(bytes(buf))
                if parsed:
                    return parsed
            else:
                time.sleep(0.01)
        return None

    def ping(self) -> bool:
        """Sends status query to verify active radio connection (supports AT and SB9600)."""
        at_info = self.query_at_info()
        if at_info:
            return True
        resp = self.send_packet(self.OPCODE_STATUS_PING, timeout=1.0)
        return bool(resp and resp["opcode"] in [self.OPCODE_STATUS_PING, 0x15, 0x00])

    def enter_programming_mode(self) -> bool:
        """Puts radio into programming mode (display usually blanks or shows PROGRAMMING)."""
        # 1. Check if connected over USB AT command parser
        try:
            at_resp = self.send_at_command("AT", wait=0.15)
            if "OK" in at_resp:
                if self.enter_sbep_over_at():
                    self.in_prgm_mode = True
                    return True
        except Exception:
            pass

        # 2. Direct SB9600 packet request
        resp = self.send_packet(self.OPCODE_PRGM_REQ, payload=b"\x01", timeout=2.0)
        self.in_prgm_mode = bool(resp)
        return self.in_prgm_mode

    def exit_programming_mode(self) -> bool:
        """Exits programming mode and restarts radio."""
        if self.in_sbep_mode:
            self.exit_sbep_mode()
            self.in_prgm_mode = False
            return True
        resp = self.send_packet(self.OPCODE_RESTART, timeout=1.5)
        self.in_prgm_mode = False
        return bool(resp)

    def read_radio_info(self) -> Dict[str, str]:
        """Queries radio hardware information (Serial Number, Model, Flashcode) via USB AT or SB9600."""
        at_info = self.query_at_info()
        if at_info:
            return at_info

        resp = self.send_packet(self.OPCODE_RADIO_INFO, timeout=2.0)
        if not resp:
            return {}

        payload = resp["payload"]
        # Standard ASTRO 25 info payload format:
        # [0:10] Serial number ASCII
        # [10:24] Model number ASCII
        # [24:38] Flashcode ASCII
        info = {}
        if len(payload) >= 10:
            info["serial_number"] = payload[:10].decode("ascii", errors="ignore").strip()
        if len(payload) >= 24:
            info["radio_model"] = payload[10:24].decode("ascii", errors="ignore").strip()
        if len(payload) >= 38:
            info["flashcode"] = payload[24:38].decode("ascii", errors="ignore").strip()
        return info

