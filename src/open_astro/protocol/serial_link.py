"""
Serial communication link for Motorola ASTRO 25 radios.
Cross-platform support for Windows, Linux (Fedora/Ubuntu/Arch), and macOS.

Transport note (hardware-verified 2026-10-20):
The XTS 1500 / 2500 / MT 1500 does NOT need an FTDI cable. The radio itself
enumerates as a USB CDC-ACM device:

    idVendor  0x0CAD  Motorola CGISS
    idProduct 0x1001  "MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO"
    bInterfaceClass 2/2/1 (Communications / Abstract modem / AT-commands)

Linux binds cdc_acm and exposes it as /dev/ttyACM0 (root:dialout 0660).
Baud/parity settings are therefore cosmetic over USB, but are still applied
for RS-232/FTDI-cabled radios (XTS 5000 Hirose, mobiles via RIB).
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

# Motorola CGISS USB vendor ID. The radio is the USB device; no cable chip involved.
MOTOROLA_VID = 0x0CAD
MOTOROLA_PIDS = {
    0x1001: "XTS 1500 / XTS 2500 / MT 1500",
}

# USB-to-UART bridge chips used by "ribless" cables for radios without native USB
# (XTS 5000 / XTL mobiles). Matched on VID:PID, not on description text.
CABLE_VID_PIDS = {
    (0x0403, None): "FTDI",
    (0x067B, None): "Prolific PL2303",
    (0x1A86, None): "WCH CH340/CH341",
    (0x10C4, None): "Silicon Labs CP210x",
}


def get_default_port() -> str:
    if platform.system() == "Windows":
        return "COM1"
    elif platform.system() == "Darwin":
        return "/dev/tty.usbserial"
    else:
        return "/dev/ttyACM0"


def _candidates():
    """USB serial ports only, ranked: native Motorola radios first, then cables.

    Legacy 16550 ports (/dev/ttyS0-31) are always excluded. They have no hwid and
    are present by the dozen on any PC, so picking ports[0] blindly -- as earlier
    versions did -- selected /dev/ttyS31 and could never reach the radio.
    """
    if not SERIAL_AVAILABLE:
        return []
    radios, cables = [], []
    for p in serial.tools.list_ports.comports():
        if p.vid is None or p.pid is None:
            continue  # no USB hwid => motherboard serial port, never a radio
        if p.vid == MOTOROLA_VID:
            radios.append(p)
        elif (p.vid, None) in CABLE_VID_PIDS:
            cables.append(p)
    return radios + cables


class RadioSerialLink:
    def __init__(self, port: Optional[str] = None, baudrate: int = 19200, timeout: float = 2.0):
        self.port = port or self.auto_detect_port() or get_default_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    @staticmethod
    def list_ports() -> List[str]:
        """All serial ports, annotated. Legacy ttyS* are tagged so they are not
        mistaken for a radio."""
        if not SERIAL_AVAILABLE:
            return []
        out = []
        for p in serial.tools.list_ports.comports():
            if p.vid == MOTOROLA_VID:
                tag = f"[RADIO: Motorola {MOTOROLA_PIDS.get(p.pid, 'unknown model')}]"
            elif p.vid is not None and (p.vid, None) in CABLE_VID_PIDS:
                tag = f"[CABLE: {CABLE_VID_PIDS[(p.vid, None)]}]"
            elif p.vid is None:
                tag = "[legacy serial - not a radio]"
            else:
                tag = "[other USB serial]"
            out.append(f"{p.device} ({p.description}) {tag}")
        return out

    @staticmethod
    def auto_detect_port() -> Optional[str]:
        """Return the most likely radio port, or None. Never guesses a legacy ttyS*."""
        cands = _candidates()
        return cands[0].device if cands else None

    @staticmethod
    def describe_port(device: str) -> Optional[dict]:
        """Identify what is on a given port before opening it."""
        if not SERIAL_AVAILABLE:
            return None
        for p in serial.tools.list_ports.comports():
            if p.device != device:
                continue
            native = p.vid == MOTOROLA_VID
            return {
                "device": p.device,
                "description": p.description,
                "vid": p.vid,
                "pid": p.pid,
                "native_usb_radio": native,
                "model_hint": MOTOROLA_PIDS.get(p.pid) if native else None,
            }
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
        except PermissionError as e:
            raise ConnectionError(
                f"Permission denied opening {self.port}: {e}\n"
                f"       {self.port} is root:dialout 0660. Fix with either:\n"
                f"         sudo usermod -aG dialout $USER   (then log out/in, or: newgrp dialout)\n"
                f"         sudo cp scripts/99-openastro.rules /etc/udev/rules.d/ && "
                f"sudo udevadm control --reload-rules && sudo udevadm trigger"
            )
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
