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
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to open port {self.port}: {e}")

    def disconnect(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def send_command(self, opcode: int, payload: bytes = b"") -> bytes:
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("Radio link is not open.")
        
        packet = PacketFramer.build_packet(opcode, payload)
        self.connection.write(packet)
        self.connection.flush()
        
        # Read response
        response = self.connection.read(256)
        return response
