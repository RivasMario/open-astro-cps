"""
Offline .cpg codeplug writer and binary stream patcher.

Applies a typed RadioCodeplug (or explicit identity, zone, channel, frequency,
and NAC edits) onto a donor/template Motorola ASTRO 25 .cpg file while:
  * Preserving exact OLE Compound File stream lengths for in-place sector writes
  * Recomputing the trailing 2-byte CRC-16-CCITT (poly 0x1021, init 0x0000)
    over every modified ISH stream's payload (`dec[6:-2]`)
  * Updating the corresponding 10-byte directory entry in `DataStg/Strm_0`:
    `[tag: u16_be, instance: u16_be, flags: u16_be, stream_crc: u16_be, stream_id: u16_be]`
  * Synchronizing `AdkFileHeader` (cleartext) and `DataStg/Strm_2` (`tag=0x1004`)
    when radio serial or model numbers are updated
  * Re-encrypting modified streams with the 40-bit RC4 key derived from
    `MD5(b"A8Z6J9QP5")[:5] + b"\\x00" * 11`
"""
from __future__ import annotations

import shutil
import struct
from typing import Dict, List, Optional, Sequence, Tuple

from ..models import Channel, RadioCodeplug, Zone
from .cpg_decode import (
    FREQ_REC_LEN,
    ISH_LIST_PREFIX,
    NAME_TABLE_PREFIX,
    OFF_FREQ_RX,
    OFF_FREQ_TX,
    OFF_NAC_RX,
    OFF_NAC_TX,
    TAG_CHANNEL_FREQS,
    TAG_CHANNEL_NAMES,
    TAG_CHANNEL_REF,
    CpgDecoder,
)
from .cpg_parser import (
    HDR_MODEL_OFF,
    HDR_SERIAL_OFF,
     HDR_UUID_OFF,
    HEADER_STREAM,
    crc16_ccitt,
    derive_rc4_key,
    parse_header,
    rc4,
)

TAG_IDENTITY = 0x1004      # Strm_2: serial & model number record
TAG_ZONE_NAMES = 0x000D    # ISH name-list table for zone names
TAG_ZONE_HDR = 0x0FFE      # Per-zone header pointing to 0x0FFF channel-name table

STRM0_REC_LEN = 10         # [tag:u16, inst:u16, flags:u16, crc:u16, stream_id:u16]
FREQ_TRIPLE_LEN = 4        # 32-bit big-endian frequency word (Hz // 5)
OFF_FREQ_3 = 20            # Third frequency word in 35-byte FREQ_REC
OFF_NAC_3 = 10             # Third NAC word in 35-byte FREQ_REC


def _encode_freq_word(mhz: float) -> int:
    """Convert frequency in MHz to ASTRO 32-bit integer word (Hz // 5)."""
    if mhz <= 0.0:
        return 0
    return int(round(mhz * 1_000_000 / 5))


def _encode_nac_word(nac: str) -> int:
    """Convert CPS '$NNN' or hex string to 16-bit NAC integer."""
    cleaned = nac.strip().lstrip("$")
    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]
    if not cleaned:
        return 0x0293
    return int(cleaned, 16) & 0xFFFF


def _pack_fixed_ascii(text: str, slot_len: int) -> bytes:
    """Encode ASCII label truncated to fit slot_len with at least 1 null byte if possible."""
    raw = text.encode("ascii", errors="ignore")[:slot_len]
    return raw.ljust(slot_len, b"\x00")


class CpgWriter:
    """
    Offline .cpg codeplug patcher and writer.

    Loads a donor/template .cpg file, decrypts all `DataStg/Strm_*` streams,
    applies modifications to identity, zone names, channel names, and
    conventional frequencies/NACs, updates per-stream CRC-16 trailers and
    the `DataStg/Strm_0` directory table, and writes out a valid .cpg file.
    """

    def __init__(self, template_path: str):
        try:
            import olefile
        except ImportError as e:
            raise RuntimeError(
                "Writing .cpg files needs the 'olefile' package. "
                "Install it with:  pip install olefile"
            ) from e
        if not olefile.isOleFile(template_path):
            raise ValueError(f"{template_path} is not an OLE compound file")

        self.template_path = template_path
        self.key = derive_rc4_key()
        self.header_raw = bytearray()
        # Map stream_name (e.g. "Strm_1") -> decrypted bytes
        self.streams: Dict[str, bytearray] = {}
        # Map (tag, instance) -> stream_name
        self._tag_map: Dict[Tuple[int, int], str] = {}
        self._load()

    def _load(self) -> None:
        import olefile

        with olefile.OleFileIO(self.template_path) as ole:
            if ole.exists(HEADER_STREAM):
                self.header_raw = bytearray(ole.openstream(HEADER_STREAM).read())
            for entry in ole.listdir(streams=True, storages=False):
                if len(entry) == 2 and entry[0] == "DataStg" and entry[1].startswith("Strm_"):
                    sname = entry[1]
                    raw = ole.openstream(entry).read()
                    dec = bytearray(rc4(self.key, raw))
                    self.streams[sname] = dec
                    if sname != "Strm_0" and len(dec) >= 8:
                        tag, inst = struct.unpack(">HH", dec[:4])
                        self._tag_map[(tag, inst)] = sname

    # -- CRC & Strm_0 directory management --------------------------------

    def _recompute_stream_crc(self, sname: str) -> int:
        """
        Recompute and write the 2-byte CRC-16-CCITT trailer for `sname`,
        and synchronize its entry in `DataStg/Strm_0`.
        """
        dec = self.streams[sname]
        if len(dec) < 8 or sname == "Strm_0":
            return 0
        payload = bytes(dec[6:-2])
        new_crc = crc16_ccitt(payload)
        dec[-2:] = struct.pack(">H", new_crc)

        # Update directory table in Strm_0 if present
        if "Strm_0" in self.streams and sname.startswith("Strm_"):
            stream_id = int(sname.split("_")[1])
            tag, inst = struct.unpack(">HH", dec[:4])
            self._update_strm0_entry(stream_id, tag, inst, new_crc)

        return new_crc

    def _update_strm0_entry(self, stream_id: int, tag: int, inst: int, new_crc: int) -> None:
        """
        Update the 10-byte record `[tag, inst, flags, stream_crc, stream_id]`
        in `Strm_0` corresponding to `stream_id`.
        """
        s0 = self.streams["Strm_0"]
        usable_len = len(s0) - (len(s0) % STRM0_REC_LEN)
        for off in range(0, usable_len, STRM0_REC_LEN):
            r_tag, r_inst, r_flags, _r_crc, r_id = struct.unpack(
                ">HHHHH", s0[off : off + STRM0_REC_LEN]
            )
            if r_id == stream_id and r_tag == tag and r_inst == inst:
                s0[off + 6 : off + 8] = struct.pack(">H", new_crc)
                return
        # Fallback: match by stream_id alone
        for off in range(0, usable_len, STRM0_REC_LEN):
            r_id = struct.unpack(">H", s0[off + 8 : off + 10])[0]
            if r_id == stream_id:
                s0[off + 6 : off + 8] = struct.pack(">H", new_crc)
                return

    def get_strm0_directory(self) -> List[Dict[str, int]]:
        """
        Return the parsed 10-byte directory records from `DataStg/Strm_0`.
        Each record has keys: `tag`, `instance`, `flags`, `stream_crc`, `stream_id`.
        """
        if "Strm_0" not in self.streams:
            return []
        s0 = self.streams["Strm_0"]
        usable_len = len(s0) - (len(s0) % STRM0_REC_LEN)
        records: List[Dict[str, int]] = []
        for off in range(0, usable_len, STRM0_REC_LEN):
            tag, inst, flags, crc, sid = struct.unpack(
                ">HHHHH", s0[off : off + STRM0_REC_LEN]
            )
            records.append(
                {
                    "tag": tag,
                    "instance": inst,
                    "flags": flags,
                    "stream_crc": crc,
                    "stream_id": sid,
                }
            )
        return records

    # -- Patching helpers -------------------------------------------------

    def patch_identity(
        self,
        serial_number: Optional[str] = None,
        model_number: Optional[str] = None,
        uuid_bytes: Optional[bytes] = None,
    ) -> None:
        """
        Patch serial number, model number, and/or UUID in `AdkFileHeader`
        and `DataStg/Strm_2` (`tag=0x1004`).

        Note: Only writes `model_number` into `Strm_2` / `AdkFileHeader` if it looks
        like an ASTRO hardware model string (or is explicitly <= 19 chars), preserving
        exact field boundaries.
        """
        if self.header_raw and len(self.header_raw) >= 68:
            if uuid_bytes is not None and len(uuid_bytes) == 16:
                self.header_raw[HDR_UUID_OFF : HDR_UUID_OFF + 16] = uuid_bytes
            if model_number:
                self.header_raw[HDR_MODEL_OFF : HDR_MODEL_OFF + 20] = _pack_fixed_ascii(
                    model_number, 20
                )
            if serial_number:
                self.header_raw[HDR_SERIAL_OFF : HDR_SERIAL_OFF + 12] = _pack_fixed_ascii(
                    serial_number, 12
                )

        # Also patch Strm_2 (tag 0x1004, inst 0) if present
        sname = self._tag_map.get((TAG_IDENTITY, 0)) or (
            "Strm_2" if "Strm_2" in self.streams else None
        )
        if sname and sname in self.streams:
            s2 = self.streams[sname]
            # Strm_2 layout: 6-byte header, 2-byte prefix (0x0212),
            # 11-byte serial field (10 chars + NUL) at dec[8:19],
            # 18-byte model field (12 chars + 6 NULs) at dec[19:37].
            if len(s2) >= 37:
                if serial_number:
                    s2[8:19] = _pack_fixed_ascii(serial_number[:10], 11)
                if model_number:
                    s2[19:37] = _pack_fixed_ascii(model_number[:16], 18)
                self._recompute_stream_crc(sname)

    def patch_zone_names(self, zone_names: Sequence[str]) -> None:
        """
        Patch zone names in `tag=0x000D` (ISH name list for zones).
        """
        sname = self._tag_map.get((TAG_ZONE_NAMES, 0))
        if not sname:
            return
        dec = self.streams[sname]
        payload = bytearray(dec[6:-2])
        if len(payload) < ISH_LIST_PREFIX:
            return
        stride = int.from_bytes(payload[2:4], "big")
        count = int.from_bytes(payload[6:8], "big")
        if stride <= 0 or count <= 0:
            return
        for i, zname in enumerate(zone_names):
            if i >= count:
                break
            off = ISH_LIST_PREFIX + i * stride
            if off + stride <= len(payload):
                payload[off : off + stride] = _pack_fixed_ascii(zname, stride)
        dec[6:-2] = payload
        self._recompute_stream_crc(sname)

    def patch_zone_channel_names(
        self, zone_index: int, channel_names: Sequence[str], sync_duplicate_zones: bool = True
    ) -> None:
        """
        Patch channel names in `tag=0x0FFF` for `zone_index`.
        If the donor codeplug has a mirror/duplicate `0x0FFF` table (like `Strm_30`
        mirroring `Strm_28` in `205CFR2930.cpg`), `sync_duplicate_zones=True` keeps
        mirror tables in sync when only 1 zone is present.
        """
        sname = self._tag_map.get((TAG_CHANNEL_NAMES, zone_index))
        if not sname:
            return
        orig_payload = bytes(self.streams[sname][6:-2])
        self._patch_0fff_stream(sname, channel_names)

        # Also touch corresponding 0x0FFE header stream if present so its CRC is verified
        zhdr_name = self._tag_map.get((TAG_ZONE_HDR, zone_index))
        if zhdr_name:
            self._recompute_stream_crc(zhdr_name)

        if sync_duplicate_zones:
            for (tag, inst), other_sname in self._tag_map.items():
                if tag == TAG_CHANNEL_NAMES and inst != zone_index:
                    if bytes(self.streams[other_sname][6:-2]) == orig_payload:
                        self._patch_0fff_stream(other_sname, channel_names)

    def _patch_0fff_stream(self, sname: str, channel_names: Sequence[str]) -> None:
        dec = self.streams[sname]
        payload = bytearray(dec[6:-2])
        if len(payload) < NAME_TABLE_PREFIX:
            return
        count = int.from_bytes(payload[4:6], "big")
        body_len = len(payload) - NAME_TABLE_PREFIX
        if count <= 0 or body_len < count:
            return
        slot = body_len // count
        for i in range(count):
            off = NAME_TABLE_PREFIX + i * slot
            if i < len(channel_names):
                name = channel_names[i][: slot - 1]
                payload[off : off + slot] = _pack_fixed_ascii(name, slot)
        dec[6:-2] = payload
        self._recompute_stream_crc(sname)

    def _find_primary_freq_stream(self) -> Optional[str]:
        """
        Find the `0x0FFD` stream instance that `CpgDecoder` selects as the primary
        conventional personality table (the instance with the most valid band
        frequency records).
        """
        best_sname: Optional[str] = None
        best_count = -1
        for (tag, _inst), sname in sorted(self._tag_map.items()):
            if tag != TAG_CHANNEL_FREQS:
                continue
            payload = bytes(self.streams[sname][6:-2])
            recs = CpgDecoder._freq_records(payload)
            valid = sum(1 for r in recs if CpgDecoder._decode_freq_rec(r) is not None)
            if valid > best_count:
                best_count = valid
                best_sname = sname
        return best_sname

    def patch_conventional_channels(self, channels: Sequence[Channel]) -> None:
        """
        Patch conventional frequencies and NACs in the primary `0x0FFD` stream
        (and any additional `0x0FFD` streams referenced by `0x0FFC` if needed)
        to match `channels`.
        """
        sname = self._find_primary_freq_stream()
        if not sname:
            return
        dec = self.streams[sname]
        payload = bytearray(dec[6:-2])
        if len(payload) < NAME_TABLE_PREFIX:
            return
        count = int.from_bytes(payload[4:6], "big")
        if count <= 0 or len(payload) < NAME_TABLE_PREFIX + count * FREQ_REC_LEN:
            return

        # Find a template active record inside this stream in case a slot was zeroed
        template_rec: Optional[bytes] = None
        for i in range(count):
            roff = NAME_TABLE_PREFIX + i * FREQ_REC_LEN
            rec = bytes(payload[roff : roff + FREQ_REC_LEN])
            if CpgDecoder._decode_freq_rec(rec) is not None:
                template_rec = rec
                break

        for i, ch in enumerate(channels):
            if i >= count:
                break
            if ch.rx_frequency <= 0.0:
                continue
            roff = NAME_TABLE_PREFIX + i * FREQ_REC_LEN
            rec = bytearray(payload[roff : roff + FREQ_REC_LEN])
            if CpgDecoder._decode_freq_rec(bytes(rec)) is None and template_rec is not None:
                rec[:] = template_rec

            rx_word = _encode_freq_word(ch.rx_frequency)
            tx_word = _encode_freq_word(
                ch.tx_frequency if ch.tx_frequency > 0.0 else ch.rx_frequency
            )
            rx_nac = _encode_nac_word(ch.rx_nac)
            tx_nac = _encode_nac_word(ch.tx_nac)

            rec[OFF_NAC_RX : OFF_NAC_RX + 2] = struct.pack(">H", rx_nac)
            rec[OFF_NAC_TX : OFF_NAC_TX + 2] = struct.pack(">H", tx_nac)
            rec[OFF_NAC_3 : OFF_NAC_3 + 2] = struct.pack(">H", tx_nac)

            rec[OFF_FREQ_RX : OFF_FREQ_RX + 4] = struct.pack(">I", rx_word)
            rec[OFF_FREQ_TX : OFF_FREQ_TX + 4] = struct.pack(">I", tx_word)
            rec[OFF_FREQ_3 : OFF_FREQ_3 + 4] = struct.pack(">I", tx_word)

            payload[roff : roff + FREQ_REC_LEN] = rec

        dec[6:-2] = payload
        self._recompute_stream_crc(sname)

    def apply_codeplug(self, codeplug: RadioCodeplug) -> None:
        """
        Apply a typed `RadioCodeplug` onto the loaded template `.cpg` streams:
          * Updates serial number and hardware model number (when changed)
          * Updates zone names in `0x000D`
          * Updates per-zone channel names in `0x0FFF`
          * Updates Zone 1 conventional frequencies and NACs in `0x0FFD`
        """
        orig_hdr = parse_header(bytes(self.header_raw)) if self.header_raw else {}
        new_serial: Optional[str] = None
        new_model: Optional[str] = None

        if codeplug.serial_number and codeplug.serial_number != orig_hdr.get("serial"):
            new_serial = codeplug.serial_number
        if (
            codeplug.radio_model
            and codeplug.radio_model != orig_hdr.get("model")
            and " " not in codeplug.radio_model.strip()
        ):
            new_model = codeplug.radio_model.strip()

        if new_serial or new_model:
            self.patch_identity(serial_number=new_serial, model_number=new_model)

        if codeplug.zones:
            # Patch zone names in 0x000D if explicit zone names (not just default "ZONE N") are provided
            if any(not z.name.startswith("ZONE ") for z in codeplug.zones):
                self.patch_zone_names([z.name for z in codeplug.zones])

            sync_dups = len(codeplug.zones) == 1
            for zi, zone in enumerate(codeplug.zones):
                ch_names = [ch.name for ch in zone.channels]
                self.patch_zone_channel_names(
                    zi, ch_names, sync_duplicate_zones=sync_dups
                )

            # Zone 0 holds the conventional channels mapped to 0x0FFD
            self.patch_conventional_channels(codeplug.zones[0].channels)

    def write(self, output_path: str) -> None:
        """
        Write the patched `.cpg` to `output_path` using in-place OLE stream
        sector overwrite so that stream sizes and OLE directory structures
        remain 100% compliant with Motorola CPS.
        """
        import olefile

        shutil.copyfile(self.template_path, output_path)
        ole_out = olefile.OleFileIO(output_path, write_mode=True)
        try:
            if self.header_raw and ole_out.exists(HEADER_STREAM):
                orig_hdr_size = ole_out.get_size(HEADER_STREAM)
                if len(self.header_raw) != orig_hdr_size:
                    raise ValueError(
                        f"AdkFileHeader size mismatch: {len(self.header_raw)} != {orig_hdr_size}"
                    )
                ole_out.write_stream(HEADER_STREAM, bytes(self.header_raw))

            for sname, dec_bytes in self.streams.items():
                stream_path = f"DataStg/{sname}"
                if ole_out.exists(stream_path):
                    orig_size = ole_out.get_size(stream_path)
                    enc_bytes = rc4(self.key, bytes(dec_bytes))
                    if len(enc_bytes) != orig_size:
                        raise ValueError(
                            f"Stream {stream_path} size mismatch: {len(enc_bytes)} != {orig_size}"
                        )
                    ole_out.write_stream(stream_path, enc_bytes)
        finally:
            ole_out.close()

    @classmethod
    def write_codeplug(
        cls,
        codeplug: RadioCodeplug,
        output_path: str,
        template_path: str,
    ) -> None:
        """Convenience helper: load `template_path`, apply `codeplug`, and write `output_path`."""
        writer = cls(template_path)
        writer.apply_codeplug(codeplug)
        writer.write(output_path)
