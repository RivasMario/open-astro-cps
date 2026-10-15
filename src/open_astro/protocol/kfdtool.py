"""
KFDtool hardware adapter and P25 TIA-102.AACD 3-wire keyloading protocol implementation.
Supports Motorola ASTRO 25 radios (XTS 2500, XTS 5000, PRC-153) and P25 Key Fill Devices (KVL).
"""
import time
from typing import List, Optional, Tuple, Dict, Any
from enum import IntEnum

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class P25Algorithm(IntEnum):
    DES_XL = 0x80
    DES_OFB = 0x81
    AES_256 = 0x84
    ADP = 0xAA          # Motorola ADP (40-bit RC4 software encryption)

    @classmethod
    def from_str(cls, name: str) -> "P25Algorithm":
        mapping = {
            "adp": cls.ADP,
            "rc4": cls.ADP,
            "aes": cls.AES_256,
            "aes256": cls.AES_256,
            "aes-256": cls.AES_256,
            "des": cls.DES_OFB,
            "des-ofb": cls.DES_OFB,
            "des-xl": cls.DES_XL,
        }
        clean = name.strip().lower()
        if clean not in mapping:
            raise ValueError(f"Unsupported algorithm '{name}'. Choose from: ADP, AES-256, DES-OFB, DES-XL")
        return mapping[clean]


class KfdtoolAdapter:
    """
    Communicates with KFDtool hardware adapter over USB CDC serial (115200 8N1).
    Implements the framing and adapter protocol opcodes.
    """
    SOM_EOM = 0x61            # 'a' (start of message / end of message)
    SOM_EOM_PLACEHOLDER = 0x62 # 'b'
    ESC = 0x63                # 'c'
    ESC_PLACEHOLDER = 0x64    # 'd'

    # Adapter Command Opcodes
    CMD_READ = 0x11
    CMD_WRITE_INFO = 0x12
    CMD_ENTER_BSL = 0x13
    CMD_RESET = 0x14
    CMD_SELF_TEST = 0x15
    CMD_SEND_KEY_SIG = 0x16
    CMD_SEND_BYTE = 0x17

    # Adapter Response Opcodes
    RSP_ERROR = 0x20
    RSP_READ = 0x21
    RSP_WRITE_INFO = 0x22
    RSP_ENTER_BSL = 0x23
    RSP_RESET = 0x24
    RSP_SELF_TEST = 0x25
    RSP_SEND_KEY_SIG = 0x26
    RSP_SEND_BYTE = 0x27

    # Broadcast Opcode (incoming byte from radio)
    BCST_RECEIVE_BYTE = 0x31

    # Read Sub-Opcodes
    READ_AP_VER = 0x01
    READ_FW_VER = 0x02
    READ_UNIQUE_ID = 0x03
    READ_MODEL_ID = 0x04
    READ_HW_REV = 0x05
    READ_SER_NUM = 0x06

    def __init__(self, port: str, timeout: float = 1.0):
        self.port = port
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None

    def connect(self) -> None:
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial is required for KFDtool communication. Run: pip install pyserial")
        self.connection = serial.Serial(
            port=self.port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout
        )

    def disconnect(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @classmethod
    def frame_packet(cls, payload: bytes) -> bytes:
        """Escape and delimit payload with SOM/EOM delimiters."""
        escaped = bytearray()
        escaped.append(cls.SOM_EOM)
        for b in payload:
            if b == cls.ESC:
                escaped.append(cls.ESC)
                escaped.append(cls.ESC_PLACEHOLDER)
            elif b == cls.SOM_EOM:
                escaped.append(cls.ESC)
                escaped.append(cls.SOM_EOM_PLACEHOLDER)
            else:
                escaped.append(b)
        escaped.append(cls.SOM_EOM)
        return bytes(escaped)

    @classmethod
    def unframe_packet(cls, raw: bytes) -> List[bytes]:
        """Parse stream of raw bytes into unframed payload packets."""
        packets = []
        in_packet = False
        escaped = False
        curr = bytearray()

        for b in raw:
            if not in_packet:
                if b == cls.SOM_EOM:
                    in_packet = True
                    curr.clear()
                    escaped = False
            else:
                if escaped:
                    if b == cls.ESC_PLACEHOLDER:
                        curr.append(cls.ESC)
                    elif b == cls.SOM_EOM_PLACEHOLDER:
                        curr.append(cls.SOM_EOM)
                    else:
                        curr.append(b)
                    escaped = False
                elif b == cls.ESC:
                    escaped = True
                elif b == cls.SOM_EOM:
                    packets.append(bytes(curr))
                    curr.clear()
                    in_packet = False
                else:
                    curr.append(b)
        return packets

    def send_command(self, payload: bytes, wait_resp: bool = True) -> Optional[bytes]:
        if not self.connection or not self.connection.is_open:
            raise ConnectionError("KFDtool connection is closed.")
        
        framed = self.frame_packet(payload)
        self.connection.write(framed)
        self.connection.flush()

        if not wait_resp:
            return None

        # Read response packet
        raw = bytearray()
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            chunk = self.connection.read(self.connection.in_waiting or 1)
            if chunk:
                raw.extend(chunk)
                packets = self.unframe_packet(bytes(raw))
                if packets:
                    return packets[0]
            else:
                time.sleep(0.01)
        raise TimeoutError("Timed out waiting for KFDtool adapter response.")

    def read_firmware_version(self) -> str:
        cmd = bytes([self.CMD_READ, self.READ_FW_VER])
        resp = self.send_command(cmd)
        if resp and len(resp) >= 5 and resp[0] == self.RSP_READ:
            # resp: [0x21, 0x02, major, minor, patch]
            return f"{resp[2]}.{resp[3]}.{resp[4]}"
        return "Unknown"

    def read_hardware_revision(self) -> str:
        cmd = bytes([self.CMD_READ, self.READ_HW_REV])
        resp = self.send_command(cmd)
        if resp and len(resp) >= 4 and resp[0] == self.RSP_READ:
            return f"Rev {resp[2]}.{resp[3]}"
        return "Unknown"

    def read_model_id(self) -> int:
        cmd = bytes([self.CMD_READ, self.READ_MODEL_ID])
        resp = self.send_command(cmd)
        if resp and len(resp) >= 3 and resp[0] == self.RSP_READ:
            return resp[2]
        return 0

    def send_key_signature(self) -> bool:
        """Sends key signature pulse to wake radio crypto module into KEYLOAD mode."""
        cmd = bytes([self.CMD_SEND_KEY_SIG, 0x00])
        resp = self.send_command(cmd)
        return bool(resp and resp[0] == self.RSP_SEND_KEY_SIG)

    def send_byte(self, byte_val: int) -> bool:
        """Sends a single byte over the 3-wire line."""
        cmd = bytes([self.CMD_SEND_BYTE, 0x00, byte_val & 0xFF])
        resp = self.send_command(cmd)
        return bool(resp and resp[0] == self.RSP_SEND_BYTE)

    def receive_byte(self, timeout: float = 1.0) -> Optional[int]:
        """Waits for an incoming byte broadcast (0x31) from the radio on the 3-wire bus."""
        start_time = time.time()
        buf = bytearray()
        while time.time() - start_time < timeout:
            chunk = self.connection.read(self.connection.in_waiting or 1)
            if chunk:
                buf.extend(chunk)
                packets = self.unframe_packet(bytes(buf))
                for pkt in packets:
                    if len(pkt) >= 3 and pkt[0] == self.BCST_RECEIVE_BYTE:
                        return pkt[2]
            else:
                time.sleep(0.01)
        return None

    def self_test(self) -> bool:
        cmd = bytes([self.CMD_SELF_TEST])
        resp = self.send_command(cmd)
        return bool(resp and resp[0] == self.RSP_SELF_TEST)


class P25ThreeWireLink:
    """
    Implements P25 TIA-102.AACD 3-wire session management, KMM framing, and key operations.
    """
    OPCODE_READY_REQ = 0xC0
    OPCODE_READY_GENERAL_MODE = 0xD0
    OPCODE_DISCONNECT = 0xC1
    OPCODE_TRANSFER_DONE = 0x92
    OPCODE_DISCONNECT_ACK = 0x90
    OPCODE_KMM = 0xC2

    KMM_MID_MODIFY_KEY = 0x80
    KMM_MID_ZEROIZE = 0x82

    def __init__(self, adapter: KfdtoolAdapter):
        self.adapter = adapter

    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """
        Calculates 16-bit CRC for P25 TIA-102.AACD 3-wire frames (Poly 0x1021, init 0xFFFF).
        """
        crc = 0xFFFF
        for b in data:
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def build_kmm_frame(self, kmm_body: bytes) -> bytes:
        """
        Wraps KMM body in 3-wire preamble, frame length, and CRC16.
        Preamble: [0x00, 0xFF, 0xFF, 0xFF] + kmm_body -> CRC
        Frame: [0xC2, len_hi, len_lo, kmm_body..., crc_hi, crc_lo]
        """
        preamble = bytes([0x00, 0xFF, 0xFF, 0xFF])
        crc_data = preamble + kmm_body
        crc = self.calculate_crc16(crc_data)

        length = len(kmm_body)
        frame = bytearray()
        frame.append(self.OPCODE_KMM)
        frame.append((length >> 8) & 0xFF)
        frame.append(length & 0xFF)
        frame.extend(kmm_body)
        frame.append((crc >> 8) & 0xFF)
        frame.append(crc & 0xFF)
        return bytes(frame)

    def init_session(self, timeout: float = 2.0) -> bool:
        """
        Initiates 3-wire keyloading session with target radio:
        1. Sends key signature pulse to trigger radio into KEYLOAD mode.
        2. Sends 0xC0 (READY_REQ).
        3. Awaits 0xD0 (READY_GENERAL_MODE) response.
        """
        if not self.adapter.send_key_signature():
            return False
        
        time.sleep(0.05)
        if not self.adapter.send_byte(self.OPCODE_READY_REQ):
            return False

        resp = self.adapter.receive_byte(timeout=timeout)
        return resp == self.OPCODE_READY_GENERAL_MODE

    def end_session(self, timeout: float = 1.0) -> bool:
        """
        Terminates 3-wire keyloading session:
        1. Sends 0xC1 (DISCONNECT), expects 0xC1.
        2. Sends 0x92 (TRANSFER_DONE), expects 0x90 (DISCONNECT_ACK).
        """
        self.adapter.send_byte(self.OPCODE_DISCONNECT)
        self.adapter.receive_byte(timeout=timeout)
        self.adapter.send_byte(self.OPCODE_TRANSFER_DONE)
        resp = self.adapter.receive_byte(timeout=timeout)
        return resp == self.OPCODE_DISCONNECT_ACK

    def send_frame(self, frame_bytes: bytes) -> bool:
        """Transmits a full KMM frame byte-by-byte through the adapter."""
        for b in frame_bytes:
            if not self.adapter.send_byte(b):
                return False
        return True

    def build_modify_key_command(
        self,
        key_id: int,
        algorithm: P25Algorithm,
        key_data_hex: str,
        keyset_id: int = 1,
        sln: int = 0
    ) -> bytes:
        """
        Builds standard P25 TIA-102.AACD ModifyKeyCommand KMM.
        """
        raw_key = bytes.fromhex(key_data_hex.strip())
        key_len = len(raw_key)

        body = bytearray()
        body.append(0x00) # Message Number
        body.append(0x00)
        body.append(self.KMM_MID_MODIFY_KEY) # Message ID = 0x80
        body.append(0x00)
        body.append(0x00)
        body.append(keyset_id & 0xFF)
        body.append(int(algorithm) & 0xFF)
        body.append(key_len & 0xFF)
        body.append(0x01) # Number of keys = 1

        # KeyItem: SLN (2 bytes), KeyId (2 bytes), KeyData (N bytes), Flags (1 byte)
        body.append((sln >> 8) & 0xFF)
        body.append(sln & 0xFF)
        body.append((key_id >> 8) & 0xFF)
        body.append(key_id & 0xFF)
        body.extend(raw_key)
        body.append(0x00) # Flags: KEK=0, Erase=0

        return bytes(body)

    def build_zeroize_command(self) -> bytes:
        """
        Builds standard P25 ZeroizeCommand KMM.
        """
        body = bytearray()
        body.append(0x00)
        body.append(0x00)
        body.append(self.KMM_MID_ZEROIZE) # Message ID = 0x82
        body.append(0x00)
        body.append(0x00)
        return bytes(body)
