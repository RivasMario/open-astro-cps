"""
AstroFlasher: memory read/write engine for Motorola ASTRO 25 radios.

!! THE WIRE ENCODING IN THIS MODULE IS UNVERIFIED !!

This module calls commands by name (protocol/commands.py), matching the real
transport's confirmed shape (Send(name, payload, device-address) -- see
docs/CPS_BINARY_ANALYSIS.md). Exactly one of those names, ENTER_PROGRAMMING
("EPREQ"), is a real string found inside the actual Motorola PatPort.exe.
Every other name here (UNKNOWN_PING, UNKNOWN_GET_RADIO_INFO,
UNKNOWN_READ_BLOCK, UNKNOWN_WRITE_BLOCK, UNKNOWN_COMMIT, UNKNOWN_REBOOT) is
this project's own placeholder -- there is no evidence a command by any of
those names exists at all, real or otherwise.

Even for EPREQ, the actual bytes that get transmitted when PatPort.exe calls
Send("EPREQ", ...) are not known. This module sends everything through
framing.py's placeholder byte encoding, which static disassembly of the real
transport DLL confirms does NOT match the real protocol (no use of its
START_BYTE anywhere in that DLL). The dual-bank A/B layout, the partition
addresses below, and the CRC32-commit sequence were authored from reasoning
about how the protocol *ought* to work, before the real installer had been
read; nothing in the real installer corresponds to them.

Consequences, in order of severity:
  * Reads are likely to return nothing (the radio will not recognize the frames).
  * A write that is partially understood can corrupt the codeplug partition.
  * If the real address map differs, a write believed to be in-bounds can land
    in the tuning partition and destroy factory RF calibration ("ERROR 01/82"),
    which no amount of software can restore without the original soft-pots.

write_codeplug() therefore refuses to run until the caller passes
allow_unverified_protocol=True. Remove this gate only once the wire encoding
has been confirmed against ground truth (a captured CPS <-> radio session, or
disassembly that locates the real opcode-name -> bytes table).
"""
import os
import sys
import time
import zlib
import struct
from typing import Optional, Callable
from .framing import PacketFramer
from .serial_link import RadioSerialLink
from .commands import (
    DeviceAddress,
    ENTER_PROGRAMMING,
    UNKNOWN_PING,
    UNKNOWN_GET_RADIO_INFO,
    UNKNOWN_READ_BLOCK,
    UNKNOWN_WRITE_BLOCK,
    UNKNOWN_COMMIT,
)
from . import at_interface

# Critical Memory Boundaries -- placeholder addresses, no basis in the real
# installer (see module docstring).
TUNING_START    = 0x0000_4000
TUNING_END      = 0x0000_7FFF
TUNING_LEN      = TUNING_END - TUNING_START  # 16 KB

CODEPLUG_BANK_A = 0x0020_0000
CODEPLUG_BANK_B = 0x0022_0000
CODEPLUG_LEN    = 0x0002_0000  # 128 KB per bank

OPTIMAL_BLOCK_SIZE = 256  # placeholder chunk size, no confirmed basis

class AstroFlasher:
    def __init__(self, serial_link: RadioSerialLink):
        self.link = serial_link
        self.radio_info = {}

    def get_radio_identity(self, allow_unverified_protocol: bool = False) -> dict:
        """
        Queries radio hardware identification.

        Tries the REAL, VERIFIED AT command interface first (at_interface.py --
        see docs/AT_INTERFACE_DISCOVERY.md). This is not gated: AT&V is a
        standard, read-only, measured-safe command, confirmed working against
        a real XTS 2500. Only radios that enumerate as a native Motorola USB
        device (see serial_link.describe_port) are tried this way, since that
        is the only configuration this has been verified against.

        Falls back to the unverified placeholder SB9600 path
        (UNKNOWN_GET_RADIO_INFO) only if the AT interface doesn't answer, or
        for a cable-connected radio the AT path was never tried against.
        """
        link_port = getattr(self.link, "port", None)
        link_connection = getattr(self.link, "connection", None)
        port_info = RadioSerialLink.describe_port(link_port) if link_port else None
        if port_info and port_info.get("native_usb_radio") and link_connection:
            try:
                info = at_interface.get_radio_identity(self.link.connection)
                banner = at_interface.get_firmware_banner(self.link.connection)
                normalized = {
                    "model": info.get("MODEL", "UNKNOWN"),
                    "serial": info.get("SERIAL", "UNKNOWN"),
                    "flashcode": "UNKNOWN",  # not exposed by AT&V
                    "firmware": banner or "UNKNOWN",
                    "radio_name": info.get("RADIO", "UNKNOWN"),
                    "secure": info.get("SECURE", "UNKNOWN"),
                    "raw_at_response": info,
                }
                self.radio_info = normalized
                return normalized
            except at_interface.ATInterfaceError:
                pass  # fall through to the placeholder path below

        resp = self.link.send_command(UNKNOWN_GET_RADIO_INFO, b"",
                                       allow_unverified_protocol=allow_unverified_protocol)
        if not resp:
            raise ConnectionError("Radio did not respond to GET_RADIO_INFO")

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

    def backup_tuning_partition(self, output_dir: str = ".", allow_unverified_protocol: bool = False) -> str:
        """
        MANDATORY SAFETY PRE-FLIGHT:
        Dumps the RF alignment partition (placeholder address range) to a
        local backup file before any write, on the theory that having *a*
        backup is better than none even though the address range itself is
        unconfirmed (see module docstring).
        """
        serial = self.radio_info.get("serial", "UNKNOWN_RADIO")
        backup_filename = os.path.join(output_dir, f"{serial}_tuning_backup.bin")

        tuning_bytes = self._read_memory_range(TUNING_START, TUNING_LEN,
                                                allow_unverified_protocol=allow_unverified_protocol)

        with open(backup_filename, "wb") as f:
            f.write(tuning_bytes)

        return backup_filename

    def read_codeplug(self,
                      start_addr: int = CODEPLUG_BANK_A,
                      length: int = CODEPLUG_LEN,
                      progress_callback: Optional[Callable[[int, int, float], None]] = None,
                      allow_unverified_protocol: bool = False) -> bytes:
        """
        Reads codeplug partition from the radio. Blocked by default -- see
        module docstring; this has the same wire-encoding problem as writes,
        it just can't destroy anything if the encoding is wrong.
        """
        if not allow_unverified_protocol:
            raise RuntimeError(
                "Refusing to read: the wire encoding in flasher.py is an unverified "
                "placeholder (see docs/CPS_BINARY_ANALYSIS.md). A bad read can't damage "
                "the radio, but it also won't return anything real. "
                "Pass allow_unverified_protocol=True to try it anyway."
            )

        if not self.link.ping(allow_unverified_protocol=True):
            raise ConnectionError("Radio did not respond to PING")

        self.get_radio_identity(allow_unverified_protocol=True)

        enter_resp = self.link.send_command(ENTER_PROGRAMMING, bytes([0xA5, 0x5A]),
                                             allow_unverified_protocol=True)
        if not enter_resp or not enter_resp.get("is_ack"):
            raise RuntimeError(f"Radio rejected {ENTER_PROGRAMMING}")

        try:
            self.backup_tuning_partition(allow_unverified_protocol=True)
            codeplug_bytes = self._read_memory_range(start_addr, length, progress_callback,
                                                       allow_unverified_protocol=True)
            return codeplug_bytes
        finally:
            self.link.reboot_radio(allow_unverified_protocol=True)

    def write_codeplug(self,
                       codeplug_bytes: bytes,
                       target_bank: int = CODEPLUG_BANK_B,
                       progress_callback: Optional[Callable[[int, int, float], None]] = None,
                       allow_unverified_protocol: bool = False) -> bool:
        """
        Writes codeplug to the staging bank, validates CRC, and commits.

        Blocked by default: the wire encoding and the address map this
        depends on are unverified (see module docstring). Pass
        allow_unverified_protocol=True to override, accepting that a wrong
        address map can destroy the radio's factory RF calibration.
        """
        if not allow_unverified_protocol:
            raise RuntimeError(
                "Refusing to write: the wire encoding and memory map in flasher.py are "
                "unverified placeholders, never confirmed against a radio or against "
                "Motorola's own code. A write based on a wrong address map can overwrite "
                "the tuning partition and permanently destroy factory RF calibration. "
                "Pass allow_unverified_protocol=True only on a radio you are willing to lose."
            )

        # SAFETY CHECK: Boundary interlock (placeholder address, see module docstring)
        if target_bank < 0x0020_0000:
            raise ValueError(
                f"HARDWARE BOUNDARY LOCK VIOLATION: Refusing write below 0x0020_0000! "
                f"Target address {hex(target_bank)} would overwrite critical calibration or bootloader!"
            )

        if not self.link.ping(allow_unverified_protocol=True):
            raise ConnectionError("Radio did not respond to PING")

        self.get_radio_identity(allow_unverified_protocol=True)

        enter_resp = self.link.send_command(ENTER_PROGRAMMING, bytes([0xA5, 0x5A]),
                                             allow_unverified_protocol=True)
        if not enter_resp or not enter_resp.get("is_ack"):
            raise RuntimeError(f"Radio rejected {ENTER_PROGRAMMING}")

        try:
            self.backup_tuning_partition(allow_unverified_protocol=True)

            total_bytes = len(codeplug_bytes)
            offset = 0
            start_time = time.time()

            while offset < total_bytes:
                chunk = codeplug_bytes[offset:offset + OPTIMAL_BLOCK_SIZE]
                current_addr = target_bank + offset

                addr_bytes = [
                    (current_addr >> 16) & 0xFF,
                    (current_addr >> 8) & 0xFF,
                    current_addr & 0xFF,
                    len(chunk) & 0xFF
                ]
                payload = bytes(addr_bytes) + chunk

                resp = self.link.send_command(UNKNOWN_WRITE_BLOCK, payload, allow_unverified_protocol=True)
                if not resp:
                    raise IOError(f"Write failed at offset {hex(current_addr)}: no response")

                resp_payload = resp.get("payload", b"")
                if len(resp_payload) > 0 and resp_payload[0] != 0x00:
                    status = resp_payload[0]
                    raise IOError(f"Radio reported write error code {status} at address {hex(current_addr)}")

                offset += len(chunk)
                elapsed = time.time() - start_time
                if progress_callback:
                    progress_callback(offset, total_bytes, elapsed)

            # Placeholder commit (see module docstring -- no real basis)
            crc32_val = zlib.crc32(codeplug_bytes) & 0xFFFFFFFF
            bank_id = 0x01 if target_bank == CODEPLUG_BANK_B else 0x00
            commit_payload = struct.pack(">IB", crc32_val, bank_id)

            commit_resp = self.link.send_command(UNKNOWN_COMMIT, commit_payload, allow_unverified_protocol=True)
            if not commit_resp:
                raise RuntimeError("Commit command got no response. Staging bank not activated.")

            commit_status = commit_resp.get("payload", b"")[0] if commit_resp.get("payload") else 0x00
            if commit_status != 0x00:
                raise RuntimeError(f"Radio rejected codeplug commit with status code {commit_status}!")

            return True

        finally:
            self.link.reboot_radio(allow_unverified_protocol=True)

    def _read_memory_range(self,
                           start_addr: int,
                           total_len: int,
                           progress_callback: Optional[Callable[[int, int, float], None]] = None,
                           allow_unverified_protocol: bool = False) -> bytes:
        """Reads a range of memory in placeholder-sized chunks. See module
        docstring -- UNKNOWN_READ_BLOCK has no real-name basis."""
        result = bytearray()
        offset = 0
        start_time = time.time()

        while offset < total_len:
            chunk_size = min(OPTIMAL_BLOCK_SIZE, total_len - offset)
            current_addr = start_addr + offset

            payload = bytes([
                (current_addr >> 16) & 0xFF,
                (current_addr >> 8) & 0xFF,
                current_addr & 0xFF,
                chunk_size & 0xFF
            ])

            resp = self.link.send_command(UNKNOWN_READ_BLOCK, payload, allow_unverified_protocol=True)
            if not resp:
                raise IOError(f"Read memory command failed at address {hex(current_addr)}: no response")

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
