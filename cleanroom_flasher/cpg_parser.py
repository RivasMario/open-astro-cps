"""
Motorola ASTRO 25 Binary Codeplug (.cpg) Parser, Decryptor, and Engine.
Supports 100% clean-room, pure Python decryption and encryption of ASTRO 25 codeplugs
across Windows, Linux (Fedora/Ubuntu/Arch), and macOS.

Architecture:
1. Microsoft Compound File Binary (OLE2) structured storage.
2. ADK File Header (AdkFileHeader) parsing for Model, Serial Number, and Key extraction.
3. ADK LCG stream cipher (Linear Congruential Generator) for 9-byte session key decryption.
4. Microsoft Base CSP MD5 -> 40-bit RC4 (zero-padded to 16 bytes) stream cipher for DataStg/Strm_*.
"""
import struct
import hashlib
from typing import Dict, List, Optional, Tuple, Any
try:
    import olefile
    OLEFILE_AVAILABLE = True
except ImportError:
    OLEFILE_AVAILABLE = False


def rc4_crypt(key: bytes, data: bytes) -> bytes:
    """
    Standard RC4 symmetric stream cipher.
    Encrypting and decrypting are identical operations.
    """
    S = list(range(256))
    j = 0
    out = bytearray()
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) % 256])
    return bytes(out)


class AdkLcgCipher:
    """
    Motorola ADK Linear Congruential Generator (LCG) pseudo-random cipher.
    Reversed from fhAdk10c.dll (CFhAdkEncrypt::randomGenerator and decryptChar).
    Used to de-obfuscate the 9-byte session key stored in AdkFileHeader at offset 0x23E.
    """
    @staticmethod
    def lcg_step(seed: int) -> int:
        """CFhAdkEncrypt::randomGenerator: next = (seed * 85 + 25) & 0xFF."""
        return ((seed * 85) + 25) & 0xFF

    @classmethod
    def decrypt(cls, raw: bytes) -> bytes:
        """
        De-obfuscates payload using the ADK LCG stream cipher with 0x1B byte-stuffing escape.
        """
        if len(raw) < 10:
            return raw

        b5 = raw[5]
        b6 = raw[6]
        b8 = raw[8]
        seed = ((b6 + b5) - b8) & 0xFF
        keystream = cls.lcg_step(seed)
        seed = keystream

        out = bytearray()
        escaped = False
        for i in range(9, len(raw)):
            b = raw[i]
            if not escaped:
                if b == 0x1B:
                    escaped = True
                    continue
                else:
                    cipher_char = b
            else:
                escaped = False
                if b == 0xE5:
                    cipher_char = 0x1A
                else:
                    cipher_char = 0x1B

            plain = (cipher_char ^ keystream) & 0xFF
            out.append(plain)
            rnd = cls.lcg_step(seed)
            seed = rnd
            keystream = (keystream + rnd + plain) & 0xFF

        return bytes(out)


# Motorola ASTRO 25 Standard Master Codeplug RC4 Stream Key
# Derived from MD5 of master session key 5838ac3b548e44e920
MASTER_ASTRO25_RC4_KEY = bytes.fromhex("2fdaa3dadbfc87c5a3e3eb87ff4a7d8f")
RECORD_MAGIC = b"\x6d\x35\xf1"


class CpgArchive:
    """
    Represents an open Motorola ASTRO 25 binary codeplug (.cpg).
    Holds decrypted relational streams, radio metadata, and provides
    bidirectional stream encryption.
    """
    def __init__(self, filepath: str):
        if not OLEFILE_AVAILABLE:
            raise RuntimeError("olefile is required to parse .cpg files. Run: pip install olefile")
        self.filepath = filepath
        self.ole: Optional[olefile.OleFileIO] = None
        self.model_number: str = ""
        self.serial_number: str = ""
        self.agency_tag: str = ""
        self.header_raw: bytes = b""
        self.encryption_type: int = 0
        self.session_key_9: bytes = b""
        self.rc4_key_16: bytes = b""
        self.decrypted_streams: Dict[str, bytes] = {}
        self.raw_streams: Dict[str, bytes] = {}
        self._load()

    def _load(self) -> None:
        self.ole = olefile.OleFileIO(self.filepath)

        # 1. Parse AdkFileHeader
        if not self.ole.exists("AdkFileHeader"):
            raise ValueError(f"Invalid ASTRO 25 codeplug: missing AdkFileHeader in {self.filepath}")

        self.header_raw = self.ole.openstream("AdkFileHeader").read()

        # Model Number is at offset 28 (up to 20 ASCII characters)
        raw_model = self.header_raw[28:48].split(b"\x00")[0]
        self.model_number = raw_model.decode("ascii", errors="ignore").strip()

        # Serial Number is at offset 48 (up to 12 ASCII characters)
        raw_serial = self.header_raw[48:60].split(b"\x00")[0]
        self.serial_number = raw_serial.decode("ascii", errors="ignore").strip()

        # Encryption Type flag at offset 0x0C: (byte >> 3) & 0x03
        enc_flag = self.header_raw[0x0C]
        self.encryption_type = (enc_flag >> 3) & 0x03

        # Agency / archive tag at offset 570 (4 chars)
        raw_agency = self.header_raw[570:574].split(b"\x00")[0]
        self.agency_tag = raw_agency.decode("ascii", errors="ignore").strip()

        # 2. Derive Stream Encryption Key
        if self.encryption_type == 1: # CFhAdkSdkCrypto (MD5 -> RC4)
            key_len = self.header_raw[0x23D]
            raw_key_block = self.header_raw[0x23E:0x23E + key_len]
            dec_key_block = AdkLcgCipher.decrypt(raw_key_block)
            self.session_key_9 = dec_key_block[:9]
            derived_key = hashlib.md5(self.session_key_9).digest()

            # Verify if derived key yields the standard record magic b"\x6d\x35\xf1" on Strm_1
            # If not, use the master Motorola ASTRO 25 RC4 key
            if self.ole.exists("DataStg/Strm_1"):
                strm1_raw = self.ole.openstream("DataStg/Strm_1").read()
                if RECORD_MAGIC not in rc4_crypt(derived_key, strm1_raw):
                    if RECORD_MAGIC in rc4_crypt(MASTER_ASTRO25_RC4_KEY, strm1_raw):
                        self.rc4_key_16 = MASTER_ASTRO25_RC4_KEY
                    else:
                        self.rc4_key_16 = derived_key
                else:
                    self.rc4_key_16 = derived_key
            else:
                self.rc4_key_16 = derived_key
        else:
            self.session_key_9 = b""
            self.rc4_key_16 = b""

        # 3. Decrypt All Streams in DataStg
        for entry in self.ole.listdir():
            if entry[0] == "DataStg":
                sname = entry[1]
                raw_bytes = self.ole.openstream(entry).read()
                self.raw_streams[sname] = raw_bytes
                if self.encryption_type == 1 and self.rc4_key_16:
                    self.decrypted_streams[sname] = rc4_crypt(self.rc4_key_16, raw_bytes)
                else:
                    self.decrypted_streams[sname] = raw_bytes

    def close(self) -> None:
        if self.ole:
            self.ole.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_stream(self, name: str) -> Optional[bytes]:
        """Returns the decrypted payload of a stream (e.g. 'Strm_1')."""
        return self.decrypted_streams.get(name)

    def set_stream(self, name: str, data: bytes) -> None:
        """Sets modified decrypted bytes for a stream."""
        self.decrypted_streams[name] = data
        if self.encryption_type == 1 and self.rc4_key_16:
            self.raw_streams[name] = rc4_crypt(self.rc4_key_16, data)
        else:
            self.raw_streams[name] = data

    def find_streams_containing(self, token: bytes) -> List[str]:
        """Search decrypted streams for specific byte sequences or strings."""
        results = []
        for sname, data in self.decrypted_streams.items():
            if token in data:
                results.append(sname)
        return results

    def patch_in_place(self, output_path: str) -> None:
        """
        Saves updated streams and metadata into output .cpg file.
        Uses in-place sector overwrite on an exact binary copy to ensure
        100% compound file binary compliance with Motorola CPS.
        """
        import shutil
        shutil.copyfile(self.filepath, output_path)

        ole_copy = olefile.OleFileIO(output_path, write_mode=True)
        try:
            if self.header_raw and ole_copy.exists("AdkFileHeader"):
                ole_copy.write_stream("AdkFileHeader", self.header_raw)
            for sname, enc_data in self.raw_streams.items():
                stream_path = f"DataStg/{sname}"
                if ole_copy.exists(stream_path):
                    orig_size = ole_copy.get_size(stream_path)
                    if len(enc_data) == orig_size:
                        ole_copy.write_stream(stream_path, enc_data)
        finally:
            ole_copy.close()
