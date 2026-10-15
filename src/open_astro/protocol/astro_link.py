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

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.in_prgm_mode = False

    def connect(self) -> None:
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial is required for hardware communication. Run: pip install pyserial")
        self.connection = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout
        )
        # Assert control lines for ribless USB level shifters
        self.connection.dtr = True
        self.connection.rts = True
        time.sleep(0.05)

    def disconnect(self) -> None:
        if self.connection and self.connection.is_open:
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
        """Sends status query to verify active radio connection."""
        resp = self.send_packet(self.OPCODE_STATUS_PING, timeout=1.0)
        return bool(resp and resp["opcode"] in [self.OPCODE_STATUS_PING, 0x15, 0x00])

    def enter_programming_mode(self) -> bool:
        """Puts radio into programming mode (display usually blanks or shows PROGRAMMING)."""
        resp = self.send_packet(self.OPCODE_PRGM_REQ, payload=b"\x01", timeout=2.0)
        self.in_prgm_mode = bool(resp)
        return self.in_prgm_mode

    def exit_programming_mode(self) -> bool:
        """Exits programming mode and restarts radio."""
        resp = self.send_packet(self.OPCODE_RESTART, timeout=1.5)
        self.in_prgm_mode = False
        return bool(resp)

    def read_radio_info(self) -> Dict[str, str]:
        """Queries radio hardware information (Serial Number, Model, Flashcode)."""
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
