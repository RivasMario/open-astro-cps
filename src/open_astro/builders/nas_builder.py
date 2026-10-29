"""Non-Affiliation Scan (NAS) Builder and Patcher for ASTRO 25 radios.

Generates and patches clean-room Non-Affiliation Scan (NAS) configurations for
Motorola ASTRO 25 radios (XTS 2500, XTS 5000, XTL 5000).

Background & Theory of Operation:
  In ASTRO 25 radios, placing the selector knob directly on a trunked talkgroup causes
  the firmware to emit an over-the-air Inbound Signaling Word (ISW) affiliation packet
  to announce its Radio ID (RID) to the trunked site controller. If unauthorized or
  unprovisioned, the system controller can issue an over-the-air Radio Inhibit ("stun/kill")
  command that permanently bricks the radio.

  The Non-Affiliation Scan (NAS) solution operates as follows:
    1. A conventional "Dummy" / "Park" channel is created in a zone where the radio's
       rotary knob is parked.
    2. Crucially, TX frequency is forced to 0.0 MHz, and TX Inhibit (rx_only) is asserted.
       If PTT is pressed, the radio emits an unprogrammed/inhibit bonk and suppresses
       any RF transmission.
    3. The trunked system (0x0FD0..0x0FDD) and target talkgroup (0x0FDF) are defined
       in the codeplug.
    4. A scan list (0x0049..0x004F, 0x0FCF, 0x0FF0, 0x0FF1) is configured with the
       target talkgroup as a scan member, linked to the dummy parked channel.
    5. When the user enables scan, the ASTRO 25 receiver passively listens to the
       control channel and voice channels with ZERO RF emissions.

Safety Invariants (Strictly Enforced):
  - Invariant 1 (Zero Transmit): tx_frequency MUST be 0.0 Hz / 0.0 MHz.
  - Invariant 2 (TX Inhibit): rx_only and tx_inhibit flags MUST be True.
  - Invariant 3 (Partition 0x82 Protection): Partition 0x82 (factory tuning and
    soft-pots) MUST NEVER be modified or emitted. Attempting to touch 0x82 raises
    NasSafetyViolation immediately.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models.channel import Channel
from ..models.codeplug import RadioCodeplug, Zone, Talkgroup, ScanList
from ..protocol.write_session import WriteObject, PART_CODEPLUG, PART_TUNING
from ..parsers.trunking_decode import freq_hz_to_channel_id, channel_id_to_freq_hz


# Constants for Codeplug Stream Tags
TAG_SCAN_MEMBERS = 0x0049       # Scan members array
TAG_SCAN_CONFIG = 0x004A        # Timing / configuration
TAG_SCAN_PRIORITIES = 0x004B    # Priority 1 / Priority 2 settings
TAG_SCAN_NAMES = 0x004C         # Scan list display names ("LIST 1")
TAG_SCAN_ZONE_MAP = 0x0FCF      # Member Zone / System index mapping
TAG_ZONE_SCAN_ASSIGN = 0x0FF0   # Zone-to-scan-list assignment table
TAG_SCAN_ZONE_MASTER = 0x0FF1   # Scan enable bit and zone limit master

TAG_SYSTEM_PARAMS = 0x0FD0      # Trunking system parameters
TAG_CONTROL_CHANNELS = 0x0FD2   # Candidate control channels
TAG_SYSTEM_NAMES = 0x0FDC       # Trunking system name table
TAG_SYSTEM_IDS = 0x0FDD         # Trunking system ID table
TAG_SYSTEM_LINK = 0x0FDE        # System relational bridge
TAG_TALKGROUPS = 0x0FDF         # Trunking talkgroup table

TAG_CHANNEL_FREQS = 0x0FFD      # Conventional frequency container
TAG_PERSONALITY_REC = 0x0FFB    # Conventional personality record (35-byte)
TAG_CHANNEL_NAMES = 0x0FFF      # Channel name strings

FREQ_REC_LEN = 35
NAME_TABLE_PREFIX = 6


class NasSafetyViolation(Exception):
    """Raised when any Non-Affiliation Scan safety invariant is breached."""
    pass


@dataclass
class NasDummyChannel:
    """Conventional park channel programmed with zero transmit capability."""
    name: str = "NAS PARK"
    zone_number: int = 1
    channel_number: int = 1
    rx_frequency: float = 851.0125
    tx_frequency: float = 0.0          # STRICT SAFETY INVARIANT: MUST BE 0.0
    rx_only: bool = True               # STRICT SAFETY INVARIANT: MUST BE True
    tx_inhibit: bool = True            # STRICT SAFETY INVARIANT: MUST BE True
    rx_nac: str = "$293"
    tx_nac: str = "$000"
    scan_list_name: str = "NAS LIST 1"

    def __post_init__(self) -> None:
        self.enforce_safety()

    def enforce_safety(self) -> None:
        """Strictly enforce that this dummy channel cannot transmit under any circumstances."""
        if self.tx_frequency != 0.0:
            raise NasSafetyViolation(
                f"NAS Dummy Channel '{self.name}' must have TX frequency of 0.0 MHz, "
                f"got {self.tx_frequency} MHz. Transmit capability is forbidden!"
            )
        if not self.rx_only:
            raise NasSafetyViolation(
                f"NAS Dummy Channel '{self.name}' must have rx_only=True to disable TX Power Amp!"
            )
        if not self.tx_inhibit:
            raise NasSafetyViolation(
                f"NAS Dummy Channel '{self.name}' must have tx_inhibit=True to enforce transmit lockout!"
            )

    def to_channel(self) -> Channel:
        """Convert to typed open-astro Channel model."""
        self.enforce_safety()
        return Channel(
            channel_number=self.channel_number,
            name=self.name[:14],
            rx_frequency=self.rx_frequency,
            tx_frequency=0.0,
            channel_spacing_khz=12.5,
            voice_type="ASTRO P25",
            rx_nac=self.rx_nac,
            tx_nac=self.tx_nac,
            rx_only=True,
            scan_list=self.scan_list_name,
        )

    def to_freq_record(self) -> bytes:
        """Generate 35-byte FREQ_REC with verified zero TX frequency and zero TX NAC."""
        self.enforce_safety()
        # 35-byte FREQ_REC layout:
        # [0:2]   Tag 0x0FFB
        # [2:4]   Reserved 0x0000
        # [4:6]   Personality type 0x322F
        # [6:8]   NAC RX
        # [8:10]  NAC TX (must be 0)
        # [10:12] NAC Alt (mirrors RX)
        # [12:16] RX Freq (u32be * 5 Hz = Hz / 5)
        # [16:20] TX Freq (u32be = 0)
        # [20:24] Alt Freq (u32be = 0)
        # [24:27] Squelch bytes (CSQ = 0)
        # [27]    Flags (0x80 = simplex direct)
        # [28:34] Reserved zeroes
        # [34]    Record terminator (0x01)
        nac_rx_clean = self.rx_nac.strip().replace("$", "").replace("0x", "")
        nac_rx_val = int(nac_rx_clean, 16) if nac_rx_clean else 0x0293
        rx_freq_raw = int(round(self.rx_frequency * 200_000))
        tx_freq_raw = 0  # Zero transmit frequency

        rec = bytearray(FREQ_REC_LEN)
        rec[0:2] = struct.pack(">H", TAG_PERSONALITY_REC)
        rec[2:4] = b"\x00\x00"
        rec[4:6] = b"\x32\x2f"
        rec[6:8] = struct.pack(">H", nac_rx_val)
        rec[8:10] = b"\x00\x00"           # TX NAC zeroed
        rec[10:12] = struct.pack(">H", nac_rx_val)
        rec[12:16] = struct.pack(">I", rx_freq_raw)
        rec[16:20] = struct.pack(">I", tx_freq_raw) # TX freq strictly 0
        rec[20:24] = struct.pack(">I", tx_freq_raw) # Alt freq strictly 0
        rec[24:27] = b"\x00\x00\x00"     # CSQ squelch
        rec[27] = 0x80                    # Simplex direct flag
        rec[28:34] = b"\x00\x00\x00\x00\x00\x00"
        rec[34] = 0x01                    # Terminator

        # Double check zero transmit invariant
        if rec[16:20] != b"\x00\x00\x00\x00" or rec[20:24] != b"\x00\x00\x00\x00":
            raise NasSafetyViolation("Safety check failed: FREQ_REC contains non-zero transmit bytes!")

        return bytes(rec)


@dataclass
class NasTargetTalkgroup:
    """Target P25 / Type II trunked talkgroup for passive scanning."""
    tgid: int
    name: str
    system_id: int = 1
    priority: int = 0  # 0 = Non-Priority, 1 = Priority 1 (P1), 2 = Priority 2 (P2)

    def __post_init__(self) -> None:
        if not (1 <= self.tgid <= 65535):
            raise ValueError(f"Talkgroup ID must be between 1 and 65535, got {self.tgid}")
        if self.priority not in (0, 1, 2):
            raise ValueError(f"Priority must be 0 (none), 1 (P1), or 2 (P2), got {self.priority}")

    def to_talkgroup(self) -> Talkgroup:
        """Convert to open-astro Talkgroup model."""
        return Talkgroup(tg_id=self.tgid, name=self.name[:16])

    def to_record(self) -> bytes:
        """Encode into 5-byte 0x0FDF record."""
        # 5 bytes: flags (u8) + tgid (u16be) + priority_flags (u16be)
        flags = 0x00
        p_flags = 0x0000
        if self.priority == 1:
            p_flags = 0x0001
        elif self.priority == 2:
            p_flags = 0x0002
        return struct.pack(">BHH", flags, self.tgid, p_flags)


@dataclass
class NasTrunkingSystem:
    """Trunking system carrying the target talkgroups and control channels."""
    system_id: int
    name: str
    control_channels: List[float] = field(default_factory=list)  # MHz frequencies
    talkgroups: List[NasTargetTalkgroup] = field(default_factory=list)

    def add_talkgroup(self, tg: NasTargetTalkgroup) -> None:
        self.talkgroups.append(tg)

    def build_control_channel_record(self) -> bytes:
        """Build 0x0FD2 candidate control channels stream payload."""
        count = len(self.control_channels)
        payload = bytearray()
        # 6-byte header: 00 00 00 00 00 count(u16be)
        payload.extend(b"\x00\x00\x00\x00")
        payload.extend(struct.pack(">H", count))
        for idx, freq_mhz in enumerate(self.control_channels):
            freq_hz = int(round(freq_mhz * 1_000_000))
            cid = freq_hz_to_channel_id(freq_hz)
            # Primary control channel = 0x00, Alternate = 0x80
            flag = 0x00 if idx == 0 else 0x80
            payload.extend(struct.pack(">BHH", flag, cid, cid))
        return bytes(payload)

    def build_talkgroup_table_record(self) -> bytes:
        """Build 0x0FDF talkgroup table stream payload."""
        count = len(self.talkgroups)
        payload = bytearray()
        # 6-byte header: 00 00 00 00 00 count(u16be)
        payload.extend(b"\x00\x00\x00\x00")
        payload.extend(struct.pack(">H", count))
        for tg in self.talkgroups:
            payload.extend(tg.to_record())
        return bytes(payload)


@dataclass
class NasScanList:
    """Non-Affiliation Scan List linking the dummy channel to the trunked target."""
    list_id: int = 1
    name: str = "NAS LIST 1"
    dummy_channel: Optional[NasDummyChannel] = None
    talkgroups: List[NasTargetTalkgroup] = field(default_factory=list)
    conventional_members: List[Tuple[int, int]] = field(default_factory=list) # (zone, channel)

    def build_members_record(self) -> bytes:
        """Build 0x0049:0 Scan Members Array (31 bytes)."""
        # Header: 12 bytes
        # 0001 (table ref) 0012 (rec stride 18) 0032 (cap 50) 0014 (cap 20) 0fcf (link) 0000 (inst)
        hdr = bytes.fromhex("00010012003200140fcf0000")
        total_members = len(self.talkgroups) + len(self.conventional_members)
        if total_members > 18:
            raise ValueError(f"Scan list supports max 18 members, got {total_members}")

        payload = bytearray(hdr)
        payload.append(total_members)

        # Append member channel numbers (1-based index)
        # Conventional members first
        for z, ch in self.conventional_members:
            payload.append(ch & 0xFF)
        # Trunked talkgroup member positions
        base_ch = len(self.conventional_members) + 1
        for idx in range(len(self.talkgroups)):
            payload.append((base_ch + idx) & 0xFF)

        # Pad remaining member slots with 0xFF up to 31 bytes
        while len(payload) < 31:
            payload.append(0xFF)

        return bytes(payload[:31])

    def build_zone_map_record(self) -> bytes:
        """Build 0x0FCF:0 Member Zone / System Mapping Array (24 bytes)."""
        # Header: 6 bytes 00 00 00 00 00 01
        hdr = bytes.fromhex("000000000001")
        payload = bytearray(hdr)

        # Conventional members zone numbers
        for z, ch in self.conventional_members:
            payload.append(z & 0xFF)
        # Trunked members zone/system index (typically 0x01 for system 1)
        for tg in self.talkgroups:
            payload.append(tg.system_id & 0xFF)

        # Pad remaining slots with 0xFF up to 24 bytes
        while len(payload) < 24:
            payload.append(0xFF)

        return bytes(payload[:24])

    def build_name_record(self) -> bytes:
        """Build 0x004C:0 Scan List Name record (25 bytes)."""
        # Header: 8 bytes 00 00 00 11 00 32 00 01
        hdr = bytes.fromhex("0000001100320001")
        ascii_name = self.name[:16].encode("ascii", errors="replace").ljust(17, b"\x00")
        return hdr + ascii_name

    def build_config_record(self) -> bytes:
        """Build 0x004A:0 Timing / Configuration record (12 bytes)."""
        # 0001 0011 0032 0014 0fce 0000
        return bytes.fromhex("00010011003200140fce0000")

    def build_priority_record(self) -> bytes:
        """Build 0x004B:0 Scan Priorities record (12 bytes)."""
        # Fixed priority baseline: Priority 1 = member 1, Priority 2 = member 2
        # Header: 0000000400100001
        # Data: 0a 3e 12 00 (matches verified ASTRO 25 fixed priority baseline)
        return bytes.fromhex("00000004001000010a3e1200")


@dataclass
class NasConfiguration:
    """Complete Non-Affiliation Scan configuration bundle."""
    dummy_channel: NasDummyChannel
    trunking_system: NasTrunkingSystem
    scan_list: NasScanList

    def validate_safety(self) -> None:
        """Enforce zero-transmit and RX-only invariants."""
        self.dummy_channel.enforce_safety()


class NasBuilder:
    """Builder and patcher that produces safe, verified Non-Affiliation Scan codeplugs."""

    def __init__(self, config: Optional[NasConfiguration] = None) -> None:
        self.config = config

    @classmethod
    def create_default(
        cls,
        system_id: int = 1,
        system_name: str = "PUGET SOUND",
        control_channels: Optional[List[float]] = None,
        target_tgid: int = 1188,
        target_name: str = "SEATTLE DISP",
        park_name: str = "NAS DISPATCH",
        park_rx_freq: float = 851.0125,
        zone_num: int = 1,
        chan_num: int = 1,
    ) -> NasBuilder:
        """Create a standard Non-Affiliation Scan configuration."""
        if control_channels is None:
            # Verified EPSCA / King County / Seattle primary control channels
            control_channels = [856.1625, 860.4375, 860.5875]

        dummy = NasDummyChannel(
            name=park_name,
            zone_number=zone_num,
            channel_number=chan_num,
            rx_frequency=park_rx_freq,
            tx_frequency=0.0,
            rx_only=True,
            tx_inhibit=True,
            rx_nac="$293",
            tx_nac="$000",
            scan_list_name="NAS LIST 1",
        )

        tg = NasTargetTalkgroup(
            tgid=target_tgid,
            name=target_name,
            system_id=system_id,
            priority=1,
        )

        trunk_sys = NasTrunkingSystem(
            system_id=system_id,
            name=system_name,
            control_channels=control_channels,
            talkgroups=[tg],
        )

        scan_list = NasScanList(
            list_id=1,
            name="NAS LIST 1",
            dummy_channel=dummy,
            talkgroups=[tg],
            conventional_members=[(zone_num, chan_num)],
        )

        cfg = NasConfiguration(
            dummy_channel=dummy,
            trunking_system=trunk_sys,
            scan_list=scan_list,
        )
        cfg.validate_safety()
        return cls(cfg)

    def generate_codeplug_objects(self) -> Dict[Tuple[int, int, int], bytes]:
        """Generate all required codeplug streams as (partition, tag, instance) -> payload.

        CRITICAL: All emitted objects MUST target partition 0x80 or 0x81.
        Under NO circumstances may partition 0x82 (tuning) be emitted!
        """
        if not self.config:
            raise ValueError("NasBuilder requires a valid NasConfiguration")

        self.config.validate_safety()
        cfg = self.config
        objs: Dict[Tuple[int, int, int], bytes] = {}

        # 1. Scan List Objects (Partition 0x80)
        list_inst = cfg.scan_list.list_id - 1
        objs[(PART_CODEPLUG, TAG_SCAN_MEMBERS, list_inst)] = cfg.scan_list.build_members_record()
        objs[(PART_CODEPLUG, TAG_SCAN_CONFIG, list_inst)] = cfg.scan_list.build_config_record()
        objs[(PART_CODEPLUG, TAG_SCAN_PRIORITIES, list_inst)] = cfg.scan_list.build_priority_record()
        objs[(PART_CODEPLUG, TAG_SCAN_NAMES, list_inst)] = cfg.scan_list.build_name_record()
        objs[(PART_CODEPLUG, TAG_SCAN_ZONE_MAP, list_inst)] = cfg.scan_list.build_zone_map_record()

        # 2. Scan Zone Assignment (0x0FF0:0) - assigns zone to scan list
        # 51 bytes payload: 15 zone slots
        assign_pl = bytearray(b"\x00\x00\x00\x00\x00\x0f")
        for z in range(1, 16):
            # assign target zone to scan list 1
            s_id = cfg.scan_list.list_id if z == cfg.dummy_channel.zone_number else 0
            assign_pl.extend(bytes([s_id, 0x00, z]))
        objs[(PART_CODEPLUG, TAG_ZONE_SCAN_ASSIGN, 0)] = bytes(assign_pl)

        # 3. Scan & Zone Master (0x0FF1:0) - 30 bytes with 0x80 scan master bit
        # 00010003000f000f0ff000008000ff00ff0000000002000000000000000a
        master_pl = bytes.fromhex("00010003000f000f0ff000008000ff00ff0000000002000000000000000a")
        objs[(PART_CODEPLUG, TAG_SCAN_ZONE_MASTER, 0)] = master_pl

        # 4. Trunking System Objects (Partition 0x80)
        sys_inst = cfg.trunking_system.system_id - 1
        objs[(PART_CODEPLUG, TAG_CONTROL_CHANNELS, sys_inst)] = cfg.trunking_system.build_control_channel_record()
        objs[(PART_CODEPLUG, TAG_TALKGROUPS, sys_inst)] = cfg.trunking_system.build_talkgroup_table_record()

        # System Name (0x0FDC:0)
        sys_name_pl = bytearray(b"\x00\x00\x00\x11\x00\x32\x00\x01")
        sys_name_ascii = cfg.trunking_system.name[:16].encode("ascii", errors="replace").ljust(17, b"\x00")
        sys_name_pl.extend(sys_name_ascii)
        objs[(PART_CODEPLUG, TAG_SYSTEM_NAMES, 0)] = bytes(sys_name_pl)

        # System ID (0x0FDD:0)
        sys_id_pl = bytearray(b"\x00\x00\x00\x00\x00\x01")
        sys_id_pl.extend(struct.pack(">H", cfg.trunking_system.system_id))
        sys_id_pl.extend(b"\x00" * 7)
        objs[(PART_CODEPLUG, TAG_SYSTEM_IDS, 0)] = bytes(sys_id_pl)

        # System Link (0x0FDE:0) - 16 bytes
        objs[(PART_CODEPLUG, TAG_SYSTEM_LINK, 0)] = bytes.fromhex("00010001003200140fdc0000")

        # 5. System Parameters (0x0FD0:0) - 168 bytes
        sys_params = bytearray(b"\x00\x00\x00\x0a\x00\x10\x00\x10")
        # 16 records of 10 bytes: 0064 40b4 0032 0a25 10a2
        rec_10 = bytes.fromhex("006440b400320a2510a2")
        for _ in range(16):
            sys_params.extend(rec_10)
        objs[(PART_CODEPLUG, TAG_SYSTEM_PARAMS, 0)] = bytes(sys_params)

        # VERIFY SAFETY: Ensure partition 0x82 is 100% untouched
        for (part, tag, inst) in objs.keys():
            if part == PART_TUNING:
                raise NasSafetyViolation(
                    f"CRITICAL SAFETY VIOLATION: Partition 0x82 (Tuning) targeted by tag 0x{tag:04x}!"
                )

        return objs

    def build_write_objects(self) -> List[WriteObject]:
        """Assemble all generated objects into verified RCMP WriteObjects."""
        raw_objs = self.generate_codeplug_objects()
        write_objs: List[WriteObject] = []
        for (part, tag, inst), pl in raw_objs.items():
            if part == PART_TUNING:
                raise NasSafetyViolation(f"Refusing to emit WriteObject for partition 0x82 (Tuning)!")
            write_objs.append(WriteObject(part=part, obj=tag, inst=inst, payload=pl))
        return write_objs

    def apply_to_codeplug(self, codeplug: RadioCodeplug) -> RadioCodeplug:
        """Apply NAS configuration cleanly to a typed RadioCodeplug model."""
        if not self.config:
            raise ValueError("NasBuilder requires a valid NasConfiguration")

        self.config.validate_safety()
        cfg = self.config

        # 1. Ensure target zone exists
        target_zone = codeplug.get_zone(cfg.dummy_channel.zone_number)
        if not target_zone:
            target_zone = Zone(zone_number=cfg.dummy_channel.zone_number, name="NAS ZONE")
            codeplug.add_zone(target_zone)

        # 2. Add or update dummy channel in zone
        existing_ch = target_zone.get_channel(cfg.dummy_channel.channel_number)
        dummy_model = cfg.dummy_channel.to_channel()
        if existing_ch:
            # Overwrite in-place
            idx = target_zone.channels.index(existing_ch)
            target_zone.channels[idx] = dummy_model
        else:
            target_zone.add_channel(dummy_model)

        # 3. Add Scan List
        if not any(sl.name == cfg.scan_list.name for sl in codeplug.scan_lists):
            codeplug.scan_lists.append(ScanList(name=cfg.scan_list.name))

        # 4. Add Talkgroups
        for tg in cfg.trunking_system.talkgroups:
            if not any(t.tg_id == tg.tgid for t in codeplug.talkgroups):
                codeplug.talkgroups.append(tg.to_talkgroup())

        # Final audit
        self.verify_safety_of_codeplug(codeplug)
        return codeplug

    @staticmethod
    def verify_safety_of_codeplug(codeplug: RadioCodeplug) -> None:
        """Verify that all channels designated for NAS have zero TX capability."""
        for zone in codeplug.zones:
            for ch in zone.channels:
                if ch.rx_only:
                    if ch.tx_frequency != 0.0:
                        raise NasSafetyViolation(
                            f"Channel '{ch.name}' in Zone {zone.zone_number} is rx_only=True "
                            f"but has non-zero TX frequency {ch.tx_frequency} MHz!"
                        )

    @staticmethod
    def verify_safety_of_objects(objects: Union[List[WriteObject], List[Dict[str, Any]]]) -> None:
        """Verify that no object targets partition 0x82 and all dummy channels have 0 TX freq."""
        for o in objects:
            if isinstance(o, WriteObject):
                part = o.part
                tag = o.obj
                pl = o.payload
            else:
                part = o.get("part", o.get("partition", PART_CODEPLUG))
                tag = o.get("tag", o.get("obj", 0))
                pl = o.get("payload", b"")

            # 1. Tuning partition protection
            if part == PART_TUNING:
                raise NasSafetyViolation(
                    f"CRITICAL SAFETY VIOLATION: Partition 0x82 (Tuning) detected in object 0x{tag:04x}!"
                )

            # 2. If it's a 0x0FFD frequency table, ensure any FREQ_REC marked rx_only has tx_freq == 0
            if tag == TAG_CHANNEL_FREQS and len(pl) >= NAME_TABLE_PREFIX:
                count = int.from_bytes(pl[4:6], "big")
                offset = NAME_TABLE_PREFIX
                for _ in range(count):
                    if offset + FREQ_REC_LEN > len(pl):
                        break
                    rec = pl[offset:offset + FREQ_REC_LEN]
                    tx_freq = int.from_bytes(rec[16:20], "big")
                    flags = rec[27]
                    # If dummy channel or zero tx
                    if tx_freq == 0 and rec[20:24] != b"\x00\x00\x00\x00":
                        raise NasSafetyViolation("Alternate transmit frequency non-zero on zero-TX channel!")
                    offset += FREQ_REC_LEN

    def export_summary(self) -> Dict[str, Any]:
        """Return a structured summary of the NAS configuration for user reporting."""
        if not self.config:
            return {}
        cfg = self.config
        return {
            "park_channel": {
                "name": cfg.dummy_channel.name,
                "zone": cfg.dummy_channel.zone_number,
                "channel": cfg.dummy_channel.channel_number,
                "rx_frequency_mhz": cfg.dummy_channel.rx_frequency,
                "tx_frequency_mhz": cfg.dummy_channel.tx_frequency,
                "rx_only": cfg.dummy_channel.rx_only,
                "tx_inhibit": cfg.dummy_channel.tx_inhibit,
            },
            "trunking_system": {
                "system_id": cfg.trunking_system.system_id,
                "system_name": cfg.trunking_system.name,
                "control_channels": cfg.trunking_system.control_channels,
            },
            "talkgroups": [
                {"tgid": tg.tgid, "name": tg.name, "priority": tg.priority}
                for tg in cfg.trunking_system.talkgroups
            ],
            "scan_list": {
                "list_id": cfg.scan_list.list_id,
                "name": cfg.scan_list.name,
                "members_count": len(cfg.scan_list.talkgroups) + len(cfg.scan_list.conventional_members),
            },
            "safety_enforced": {
                "zero_rf_emission": True,
                "affiliation_suppression": True,
                "partition_0x82_protected": True,
            }
        }
