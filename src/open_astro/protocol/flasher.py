"""
AstroFlasher: Safe, high-speed memory read/write engine for Motorola ASTRO 25 radios.
Implements the SB9600 memory protocol with hardware boundary locks, dual-bank commit,
mandatory pre-flight calibration backups, and automated software reboots.
"""
import os
import sys
import time
import zlib
import struct
from typing import Optional, Callable
from .framing import PacketFramer
from .serial_link import RadioSerialLink

# Critical Memory Boundaries
TUNING_START    = 0x0000_4000
TUNING_END      = 0x0000_7FFF
TUNING_LEN      = TUNING_END - TUNING_START  # 16 KB

CODEPLUG_BANK_A = 0x0020_0000
CODEPLUG_BANK_B = 0x0022_0000
CODEPLUG_LEN    = 0x0002_0000  # 128 KB per bank

OPTIMAL_BLOCK_SIZE = 256  # 256 bytes per SB9600 chunk

class AstroFlasher:
    def __init__(self, serial_link: RadioSerialLink):
        self.link = serial_link
        self.radio_info = {}

    def get_radio_identity(self) -> dict:
        """Queries radio hardware identification via Opcode 0x14."""
        resp = self.link.send_command(0x14, b"")
        if not resp or resp.get("opcode") != 0x15:
            raise ConnectionError("Radio failed to respond to GET_RADIO_INFO (0x14)")
        
        payload = resp.get("payload", b"")
        strings = [s.decode("latin1", errors="replace") for s in payload.split(b"\x00") if s]
        
        info = {
            "model": strings[0] if len(strings) > 0 else "UNKNOWN",
            "serial": strings[1] if len(strings) > 1 else "UNKNOWN",
            "flashcode": strings[2] if len(strings) > 2 else "UNKNOWN",
            "firmware": strings[3] if len(strings) > 3 else "UNKNOWN",
        }
        self.radio_info = info
        return info

    def backup_tuning_partition(self, output_dir: str = ".") -> str:
        """
        MANDATORY SAFETY PRE-FLIGHT:
        Dumps the RF alignment partition (0x0000_4000 to 0x0000_7FFF) to a local backup file.
        This contains the unique factory crystal oscillator warping, power curves, and filters.
        """
        serial = self.radio_info.get("serial", "UNKNOWN_RADIO")
        backup_filename = os.path.join(output_dir, f"{serial}_tuning_backup.bin")
        
        # Read the 16KB tuning partition
        tuning_bytes = self._read_memory_range(TUNING_START, TUNING_LEN)
        
        with open(backup_filename, "wb") as f:
            f.write(tuning_bytes)
            
        return backup_filename

    def read_codeplug(self, 
                      start_addr: int = CODEPLUG_BANK_A, 
                      length: int = CODEPLUG_LEN,
                      progress_callback: Optional[Callable[[int, int, float], None]] = None) -> bytes:
        """
        Reads codeplug partition from the radio.
        """
        # 1. Ping
        if not self.link.ping():
            raise ConnectionError("Radio did not respond to PING (0x00)")

        # 2. Query Identity
        self.get_radio_identity()

        # 3. Enter Programming Mode
        enter_resp = self.link.send_command(0x10, bytes([0xA5, 0x5A]))
        if not enter_resp or enter_resp.get("opcode") != 0x01:
            raise RuntimeError("Radio rejected ENTER_PROGRAMMING_MODE (0x10)")

        try:
            # 4. Mandatory tuning partition backup
            self.backup_tuning_partition()

            # 5. Read codeplug memory block by block
            codeplug_bytes = self._read_memory_range(start_addr, length, progress_callback)
            return codeplug_bytes

        finally:
            # 6. Exit Programming Mode and software reboot
            self.link.reboot_radio()

    def write_codeplug(self, 
                       codeplug_bytes: bytes, 
                       target_bank: int = CODEPLUG_BANK_B,
                       progress_callback: Optional[Callable[[int, int, float], None]] = None) -> bool:
        """
        Safely writes codeplug to staging bank, validates CRC, and commits.
        Enforces strict memory boundary protection against tuning partition corruption.
        """
        # SAFETY CHECK: Boundary interlock
        if target_bank < 0x0020_0000:
            raise ValueError(
                f"HARDWARE BOUNDARY LOCK VIOLATION: Refusing write below 0x0020_0000! "
                f"Target address {hex(target_bank)} would overwrite critical calibration or bootloader!"
            )

        # 1. Ping
        if not self.link.ping():
            raise ConnectionError("Radio did not respond to PING (0x00)")

        # 2. Query Identity
        self.get_radio_identity()

        # 3. Enter Programming Mode
        enter_resp = self.link.send_command(0x10, bytes([0xA5, 0x5A]))
        if not enter_resp or enter_resp.get("opcode") != 0x01:
            raise RuntimeError("Radio rejected ENTER_PROGRAMMING_MODE (0x10)")

        try:
            # 4. Mandatory tuning backup before any write
            self.backup_tuning_partition()

            # 5. Write blocks
            total_bytes = len(codeplug_bytes)
            offset = 0
            start_time = time.time()

            while offset < total_bytes:
                chunk = codeplug_bytes[offset:offset + OPTIMAL_BLOCK_SIZE]
                current_addr = target_bank + offset

                # Payload: [ADDR_HI, ADDR_MID, ADDR_LO] + [CHUNK_LEN] + [DATA...]
                # Note: In SB9600 8-bit length encoding, 256 bytes is encoded as 0x00
                addr_bytes = [
                    (current_addr >> 16) & 0xFF,
                    (current_addr >> 8) & 0xFF,
                    current_addr & 0xFF,
                    len(chunk) & 0xFF
                ]
                payload = bytes(addr_bytes) + chunk

                resp = self.link.send_command(0x30, payload)
                if not resp or resp.get("opcode") != 0x31:
                    raise IOError(f"Write failed at offset {hex(current_addr)}! Opcode: {resp.get('opcode') if resp else 'None'}")
                
                resp_payload = resp.get("payload", b"")
                if len(resp_payload) > 0 and resp_payload[0] != 0x00:
                    status = resp_payload[0]
                    raise IOError(f"Radio reported write error code {status} at address {hex(current_addr)}")

                offset += len(chunk)
                elapsed = time.time() - start_time
                if progress_callback:
                    progress_callback(offset, total_bytes, elapsed)

            # 6. Final Commit & Bank Switch (Opcode 0x32)
            crc32_val = zlib.crc32(codeplug_bytes) & 0xFFFFFFFF
            bank_id = 0x01 if target_bank == CODEPLUG_BANK_B else 0x00
            commit_payload = struct.pack(">IB", crc32_val, bank_id)

            commit_resp = self.link.send_command(0x32, commit_payload)
            if not commit_resp or commit_resp.get("opcode") != 0x33:
                # If radio didn't ACK commit, warn or trigger rollback
                raise RuntimeError("Radio CRC32 commit command (0x32) failed. Staging bank not activated.")

            commit_status = commit_resp.get("payload", b"")[0] if commit_resp.get("payload") else 0x00
            if commit_status != 0x00:
                raise RuntimeError(f"Radio rejected codeplug commit with status code {commit_status}!")

            return True

        finally:
            # 7. Exit Programming Mode and software watchdog reboot
            self.link.reboot_radio()

    def _read_memory_range(self, 
                           start_addr: int, 
                           total_len: int,
                           progress_callback: Optional[Callable[[int, int, float], None]] = None) -> bytes:
        """Reads a range of ColdFire memory via Opcode 0x20 in optimal chunks."""
        result = bytearray()
        offset = 0
        start_time = time.time()

        while offset < total_len:
            chunk_size = min(OPTIMAL_BLOCK_SIZE, total_len - offset)
            current_addr = start_addr + offset

            # Payload: [ADDR_HI, ADDR_MID, ADDR_LO] + [CHUNK_LEN]
            payload = bytes([
                (current_addr >> 16) & 0xFF,
                (current_addr >> 8) & 0xFF,
                current_addr & 0xFF,
                chunk_size & 0xFF
            ])

            resp = self.link.send_command(0x20, payload)
            if not resp or resp.get("opcode") != 0x21:
                raise IOError(f"Read memory command (0x20) failed at address {hex(current_addr)}")

            resp_payload = resp.get("payload", b"")
            if len(resp_payload) < 1:
                raise IOError("Invalid empty read memory response payload")

            status = resp_payload[0]
            if status != 0x00:
                raise IOError(f"Radio reported read error status {status} at address {hex(current_addr)}")

            data = resp_payload[1:]
            result.extend(data)
            offset += len(data)

            elapsed = time.time() - start_time
            if progress_callback:
                progress_callback(offset, total_len, elapsed)

        return bytes(result)
