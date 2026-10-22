"""
Serial communication link for Motorola ASTRO 25 radios via USB programming cables.
Cross-platform support for Windows, Linux (Fedora/Ubuntu/Arch), and macOS.
"""
import platform
import time
from typing import List, Optional, Dict
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
        self.port = port or self.auto_detect_radio_port() or get_default_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    @staticmethod
    def list_ports() -> List[Dict[str, str]]:
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        results = []
        for p in ports:
            hwid = (p.hwid or "").lower()
            desc = (p.description or "").lower()
            device_type = "Unknown Serial Device"

            if "2047:0a7c" in hwid or "vid_2047&pid_0a7c" in hwid or "kfdtool" in desc:
                device_type = "P25 Key Variable Loader (KFDtool KVL)"
            elif "0cad:1001" in hwid or "vid_0cad&pid_1001" in hwid:
                device_type = "Motorola ASTRO 25 Native USB (RKN4105 / 0CAD:1001)"
            elif any(k in hwid or k in desc for k in ["1a86:7523", "ch340", "ftdi", "0403:6001", "prolific", "cp210"]):
                device_type = "Motorola ASTRO / Radio Programming Cable"

            results.append({
                "port": p.device,
                "description": p.description,
                "type": device_type,
                "hwid": p.hwid or ""
            })
        return results

    @staticmethod
    def auto_detect_radio_port() -> Optional[str]:
        """Automatically find the first available radio programming cable, excluding KVL devices."""
        if not SERIAL_AVAILABLE:
            return None
        ports = serial.tools.list_ports.comports()
        # Prioritize native Motorola ASTRO 25 USB (0CAD:1001)
        for p in ports:
            hwid = (p.hwid or "").lower()
            if "0cad:1001" in hwid or "vid_0cad&pid_1001" in hwid:
                return p.device
        for p in ports:
            hwid = (p.hwid or "").lower()
            desc = (p.description or "").lower()
            # Skip KVL devices
            if "2047:0a7c" in hwid or "vid_2047&pid_0a7c" in hwid or "kfdtool" in desc:
                continue
            if any(k in hwid or k in desc for k in ["1a86:7523", "ch340", "ftdi", "0403:6001", "prolific", "cp210", "usb serial"]):
                return p.device
        return ports[0].device if ports else None

    @staticmethod
    def auto_detect_kvl_port() -> Optional[str]:
        """Find the connected KFDtool Key Variable Loader (KVL)."""
        if not SERIAL_AVAILABLE:
            return None
        ports = serial.tools.list_ports.comports()
        for p in ports:
            hwid = (p.hwid or "").lower()
            desc = (p.description or "").lower()
            if "2047:0a7c" in hwid or "vid_2047&pid_0a7c" in hwid or "kfdtool" in desc:
                return p.device
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
