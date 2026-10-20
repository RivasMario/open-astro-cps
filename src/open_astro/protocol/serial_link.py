"""
Serial communication link for Motorola ASTRO 25 radios via USB programming cables.
Cross-platform support for Windows, Linux (Fedora/Ubuntu/Arch), and macOS.
"""
import platform
import time
from typing import List, Optional
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .framing import PacketFramer

def get_default_port() -> str:
    if platform.system() == "Windows":
        return "COM1"
    elif platform.system() == "Darwin":
        return "/dev/tty.usbserial"
    else:
        return "/dev/ttyUSB0"

class RadioSerialLink:
    def __init__(self, port: Optional[str] = None, baudrate: int = 19200, timeout: float = 2.0):
        self.port = port or self.auto_detect_port() or get_default_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    @staticmethod
    def list_ports() -> List[str]:
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [f"{p.device} ({p.description})" for p in ports]

    @staticmethod
    def auto_detect_port() -> Optional[str]:
        """Automatically find the first available USB-to-serial programming cable."""
        if not SERIAL_AVAILABLE:
            return None
        ports = serial.tools.list_ports.comports()
        # Look for FTDI, Prolific, CH340, or generic USB Serial
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["ftdi", "prolific", "ch340", "cp210", "usb serial"]):
                return p.device
        if ports:
            return ports[0].device
        return None

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial is required for hardware serial communication. Install with: pip install pyserial")
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            # Minimize latency if underlying driver supports it
            try:
                self.connection.set_buffer_size(rx_size=4096, tx_size=4096)
            except (AttributeError, NotImplementedError):
                pass
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to open port {self.port}: {e}")

    def disconnect(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def read_packet(self, timeout: Optional[float] = None) -> Optional[dict]:
        """
        Reads a framed SB9600 packet using deterministic boundary parsing.
        Returns immediately upon receiving a complete packet instead of stalling for timeout.
        """
        if not self.connection or not self.connection.is_open:
            return None
        
        orig_timeout = self.connection.timeout
        if timeout is not None:
            self.connection.timeout = timeout

        try:
            # 1. Scan for START_BYTE (0x05)
            start_time = time.time()
            max_wait = timeout or self.timeout
            while True:
                b = self.connection.read(1)
                if not b:
                    if time.time() - start_time > max_wait:
                        return None
                    continue
                if b[0] == 0x05:
                    break

            # 2. Read length byte
            len_byte = self.connection.read(1)
            if not len_byte:
                return None
            length = len_byte[0]

            # 3. Read remaining bytes: body (length) + checksum (1)
            remaining_to_read = length + 1
            body_and_csum = self.connection.read(remaining_to_read)
            if len(body_and_csum) < remaining_to_read:
                return None

            raw_packet = bytes([0x05, length]) + body_and_csum
            return PacketFramer.parse_packet(raw_packet)

        finally:
            if timeout is not None:
                self.connection.timeout = orig_timeout

    def send_command(self, opcode: int, payload: bytes = b"") -> Optional[dict]:
        """
        Transmits an SB9600 command and immediately reads the framed response packet.
        """
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")
        
        packet = PacketFramer.build_packet(opcode, payload)
        self.connection.write(packet)
        self.connection.flush()
        
        # Read exact framed packet response
        return self.read_packet()

    def ping(self) -> bool:
        """Pings radio using Opcode 0x00. Returns True if radio returns 0x01 ACK."""
        resp = self.send_command(0x00, b"")
        return resp is not None and resp.get("opcode") == 0x01

    def reboot_radio(self) -> bool:
        """
        Commands ColdFire CPU to perform software watchdog reboot (Opcode 0x11).
        Eliminates the need for manual power knob toggling!
        """
        resp = self.send_command(0x11, bytes([0x01]))
        return resp is not None and resp.get("opcode") == 0x01
