"""
Serial communication link for Motorola ASTRO 25 radios via USB programming cables.
"""
import time
from typing import List, Optional
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .framing import PacketFramer

class RadioSerialLink:
    def __init__(self, port: str = "COM1", baudrate: int = 19200, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    @staticmethod
    def list_ports() -> List[str]:
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [f"{p.device} ({p.description})" for p in ports]

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
