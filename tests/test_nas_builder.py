"""Tests for the Non-Affiliation Scan (NAS) Builder and Safety Enforcer.

Validates that:
  1. The TX Inhibit flag (rx_only=True, tx_inhibit=True) is strictly enforced.
  2. The conventional dummy channel cannot transmit under any circumstances (tx_freq == 0.0).
  3. Partition 0x82 (factory tuning/soft-pots) is strictly protected and never touched.
  4. NAS Scan lists and trunking system records match ASTRO 25 codeplug structures.
"""
import os
import struct
import pytest

from open_astro.builders.nas_builder import (
    NasSafetyViolation,
    NasDummyChannel,
    NasTargetTalkgroup,
    NasScanList,
    NasTrunkingSystem,
    NasConfiguration,
    NasBuilder,
    TAG_SCAN_MEMBERS,
    TAG_SCAN_CONFIG,
    TAG_SCAN_PRIORITIES,
    TAG_SCAN_NAMES,
    TAG_SCAN_ZONE_MAP,
    TAG_ZONE_SCAN_ASSIGN,
    TAG_SCAN_ZONE_MASTER,
    TAG_CONTROL_CHANNELS,
    TAG_TALKGROUPS,
    TAG_SYSTEM_NAMES,
    TAG_SYSTEM_IDS,
    TAG_PERSONALITY_REC,
)
from open_astro.models.codeplug import RadioCodeplug, Zone
from open_astro.protocol.write_session import (
    PartitionPolicy,
    PART_CODEPLUG,
    PART_TUNING,
    WriteObject,
)
from open_astro.parsers.cpg_parser import CpgParser

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = os.path.join(REPO_DIR, "schema", "partition_map.json")
BACKUP_CPG = os.path.join(REPO_DIR, "backups", "Radio1_205CMB2249_codeplug.cpg")


class TestNasDummyChannelSafety:
    """Validate that the dummy park channel strictly suppresses RF transmission."""

    def test_default_dummy_channel_is_safe(self):
        dummy = NasDummyChannel()
        assert dummy.tx_frequency == 0.0
        assert dummy.rx_only is True
        assert dummy.tx_inhibit is True

    def test_nonzero_tx_freq_raises_safety_violation(self):
        with pytest.raises(NasSafetyViolation, match="TX frequency of 0.0 MHz"):
            NasDummyChannel(tx_frequency=851.5125)

    def test_disabled_rx_only_raises_safety_violation(self):
        with pytest.raises(NasSafetyViolation, match="rx_only=True"):
            NasDummyChannel(rx_only=False)

    def test_disabled_tx_inhibit_raises_safety_violation(self):
        with pytest.raises(NasSafetyViolation, match="tx_inhibit=True"):
            NasDummyChannel(tx_inhibit=False)

    def test_to_channel_model_enforces_zero_tx(self):
        dummy = NasDummyChannel(name="PARK CH", channel_number=5, rx_frequency=851.0125)
        ch = dummy.to_channel()
        assert ch.name == "PARK CH"
        assert ch.channel_number == 5
        assert ch.rx_frequency == 851.0125
        assert ch.tx_frequency == 0.0
        assert ch.rx_only is True

    def test_freq_record_payload_has_strictly_zero_tx_bytes(self):
        dummy = NasDummyChannel(rx_frequency=851.0125)
        rec = dummy.to_freq_record()
        assert len(rec) == 35

        # Check tag
        assert int.from_bytes(rec[0:2], "big") == TAG_PERSONALITY_REC

        # Check RX frequency non-zero (851.0125 MHz * 200,000 = 170,202,500 = 0x0A251584)
        rx_raw = int.from_bytes(rec[12:16], "big")
        assert rx_raw == 170_202_500

        # STRICT INVARIANTS: TX Frequency and Alt Frequency must be exactly 0
        tx_raw = int.from_bytes(rec[16:20], "big")
        alt_tx_raw = int.from_bytes(rec[20:24], "big")
        assert tx_raw == 0, "Transmit frequency in FREQ_REC is non-zero!"
        assert alt_tx_raw == 0, "Alt transmit frequency in FREQ_REC is non-zero!"

        # TX NAC must be 0
        tx_nac = int.from_bytes(rec[8:10], "big")
        assert tx_nac == 0


class TestPartition0x82Protection:
    """Validate that Partition 0x82 (Tuning / Soft-pots) is strictly untouchable."""

    def test_builder_never_emits_partition_0x82(self):
        builder = NasBuilder.create_default()
        objs = builder.generate_codeplug_objects()

        for (part, tag, inst) in objs.keys():
            assert part != PART_TUNING, f"Partition 0x82 was emitted by tag 0x{tag:04x}!"
            assert part in (PART_CODEPLUG, 0x81), f"Unexpected partition 0x{part:02x}"

    def test_write_objects_never_contain_partition_0x82(self):
        builder = NasBuilder.create_default()
        write_objs = builder.build_write_objects()

        assert len(write_objs) > 0
        for wo in write_objs:
            assert wo.part != 0x82
            assert wo.part == PART_CODEPLUG

    def test_verify_safety_refuses_partition_0x82(self):
        bad_object = WriteObject(part=0x82, obj=TAG_SCAN_MEMBERS, inst=0, payload=b"\x00" * 31)
        with pytest.raises(NasSafetyViolation, match="Partition 0x82"):
            NasBuilder.verify_safety_of_objects([bad_object])

    def test_verify_safety_refuses_partition_0x82_dict(self):
        bad_dict = {"partition": 0x82, "tag": 0x0049, "instance": 0, "payload": b"\x00" * 31}
        with pytest.raises(NasSafetyViolation, match="Partition 0x82"):
            NasBuilder.verify_safety_of_objects([bad_dict])

    def test_policy_allowlist_agrees_with_builder_objects(self):
        """Every object emitted by NasBuilder must pass PartitionPolicy allowlist check."""
        if not os.path.exists(MAP_PATH):
            pytest.skip("partition_map.json not present")
        pol = PartitionPolicy.load(MAP_PATH)
        builder = NasBuilder.create_default()
        write_objs = builder.build_write_objects()

        for wo in write_objs:
            # Must not raise
            pol.check(wo.part, wo.obj)


class TestNasScanListAndTrunkingStructure:
    """Validate that scan lists and trunking system records are byte-accurate."""

    def test_scan_members_record_layout(self):
        dummy = NasDummyChannel(channel_number=1, zone_number=1)
        tg = NasTargetTalkgroup(tgid=1188, name="SEATTLE DISP", system_id=1, priority=1)
        scan_list = NasScanList(
            list_id=1,
            name="NAS LIST 1",
            dummy_channel=dummy,
            talkgroups=[tg],
            conventional_members=[(1, 1)],
        )

        members_rec = scan_list.build_members_record()
        assert len(members_rec) == 31
        # Header (12 bytes)
        assert members_rec[:12] == bytes.fromhex("00010012003200140fcf0000")
        # Member count at offset 12: 1 conventional + 1 talkgroup = 2 members
        assert members_rec[12] == 2
        # Member slots: Ch 1 (conventional), slot 2 (talkgroup)
        assert members_rec[13] == 1
        assert members_rec[14] == 2
        # Padding: rest should be 0xFF
        assert all(b == 0xFF for b in members_rec[15:31])

    def test_scan_zone_map_record_layout(self):
        dummy = NasDummyChannel()
        tg = NasTargetTalkgroup(tgid=1188, name="SEATTLE DISP", system_id=1)
        scan_list = NasScanList(
            list_id=1,
            name="NAS LIST 1",
            dummy_channel=dummy,
            talkgroups=[tg],
            conventional_members=[(1, 1)],
        )

        zone_rec = scan_list.build_zone_map_record()
        assert len(zone_rec) == 24
        # Header (6 bytes)
        assert zone_rec[:6] == bytes.fromhex("000000000001")
        # Zone slots: Zone 1 for conventional member, System 1 for trunked talkgroup
        assert zone_rec[6] == 1
        assert zone_rec[7] == 1
        # Remainder padded with 0xFF
        assert all(b == 0xFF for b in zone_rec[8:24])

    def test_scan_name_record_layout(self):
        scan_list = NasScanList(name="SEATTLE SCAN")
        name_rec = scan_list.build_name_record()
        assert len(name_rec) == 25
        # Header 8 bytes
        assert name_rec[:8] == bytes.fromhex("0000001100320001")
        # Name string (17 bytes null padded)
        name_str = name_rec[8:].rstrip(b"\x00").decode("ascii")
        assert name_str == "SEATTLE SCAN"

    def test_control_channels_record_layout(self):
        sys = NasTrunkingSystem(
            system_id=1,
            name="PUGET SOUND",
            control_channels=[856.1625, 860.4375],
        )
        ctrl_rec = sys.build_control_channel_record()
        # 6 byte header + 2 * 5-byte records = 16 bytes
        assert len(ctrl_rec) == 16
        count = int.from_bytes(ctrl_rec[4:6], "big")
        assert count == 2

        # Record 1: primary flag 0x00, 856.1625 MHz -> channel ID 826 (0x033A)
        assert ctrl_rec[6] == 0x00
        cid1 = int.from_bytes(ctrl_rec[7:9], "big")
        assert cid1 == 826

        # Record 2: alternate flag 0x80, 860.4375 MHz -> channel ID 1510 (0x05E6)
        assert ctrl_rec[11] == 0x80
        cid2 = int.from_bytes(ctrl_rec[12:14], "big")
        assert cid2 == 1510

    def test_talkgroup_table_record_layout(self):
        sys = NasTrunkingSystem(
            system_id=1,
            name="PUGET SOUND",
            talkgroups=[
                NasTargetTalkgroup(tgid=1188, name="SEATTLE DISP", priority=1),
                NasTargetTalkgroup(tgid=930, name="FIRE DISP", priority=0),
            ]
        )
        tg_rec = sys.build_talkgroup_table_record()
        # 6 byte header + 2 * 5-byte records = 16 bytes
        assert len(tg_rec) == 16
        count = int.from_bytes(tg_rec[4:6], "big")
        assert count == 2

        # Record 1: TGID 1188 (0x04A4) with Priority 1 flag (0x0001)
        tg1_id = int.from_bytes(tg_rec[7:9], "big")
        tg1_p = int.from_bytes(tg_rec[9:11], "big")
        assert tg1_id == 1188
        assert tg1_p == 0x0001

        # Record 2: TGID 930 (0x03A2) with Priority 0 flag (0x0000)
        tg2_id = int.from_bytes(tg_rec[12:14], "big")
        tg2_p = int.from_bytes(tg_rec[14:16], "big")
        assert tg2_id == 930
        assert tg2_p == 0x0000


class TestNasCodeplugApplication:
    """Validate applying NAS configuration to high-level RadioCodeplug objects."""

    def test_apply_to_codeplug_adds_dummy_and_scan_list(self):
        codeplug = RadioCodeplug(
            radio_model="Motorola XTS 2500 Model II",
            bandsplit="700/800 MHz",
        )
        builder = NasBuilder.create_default(
            target_tgid=1742,
            target_name="TAC 1",
            park_name="PARK TAC",
            zone_num=1,
            chan_num=1,
        )

        updated_cp = builder.apply_to_codeplug(codeplug)
        assert updated_cp.total_channels() >= 1

        z1 = updated_cp.get_zone(1)
        assert z1 is not None
        ch1 = z1.get_channel(1)
        assert ch1 is not None
        assert ch1.name == "PARK TAC"
        assert ch1.tx_frequency == 0.0
        assert ch1.rx_only is True

        # Scan list added
        assert any(sl.name == "NAS LIST 1" for sl in updated_cp.scan_lists)

        # Talkgroup added
        assert any(tg.tg_id == 1742 for tg in updated_cp.talkgroups)

    def test_codeplug_safety_verifier_detects_corrupted_tx_channel(self):
        codeplug = RadioCodeplug(
            radio_model="Motorola XTS 2500 Model II",
            bandsplit="700/800 MHz",
        )
        builder = NasBuilder.create_default()
        updated_cp = builder.apply_to_codeplug(codeplug)

        # Deliberately violate safety invariant: set tx_frequency on an rx_only channel
        z1 = updated_cp.get_zone(1)
        ch1 = z1.get_channel(1)
        ch1.tx_frequency = 851.5125

        with pytest.raises(NasSafetyViolation, match="non-zero TX frequency"):
            NasBuilder.verify_safety_of_codeplug(updated_cp)

    def test_export_summary(self):
        builder = NasBuilder.create_default(
            system_id=1,
            system_name="KING COUNTY",
            target_tgid=1188,
            target_name="SEATTLE DISP",
        )
        summary = builder.export_summary()
        assert summary["park_channel"]["tx_frequency_mhz"] == 0.0
        assert summary["park_channel"]["rx_only"] is True
        assert summary["trunking_system"]["system_name"] == "KING COUNTY"
        assert summary["talkgroups"][0]["tgid"] == 1188
        assert summary["safety_enforced"]["zero_rf_emission"] is True
        assert summary["safety_enforced"]["partition_0x82_protected"] is True


class TestNasEndToEndRealCodeplug:
    """Validate NAS builder compatibility against real backup codeplug."""

    def test_backup_codeplug_nas_generation_and_policy(self):
        if not os.path.exists(BACKUP_CPG) or not os.path.exists(MAP_PATH):
            pytest.skip("Test requires real backup CPG and partition_map.json")

        cp = CpgParser(BACKUP_CPG)
        dir_entries = cp.directory()
        cp.close()

        # Build NAS WriteObjects
        builder = NasBuilder.create_default(
            target_tgid=1188,
            target_name="SEATTLE DISP",
        )
        write_objs = builder.build_write_objects()

        pol = PartitionPolicy.load(MAP_PATH)
        for wo in write_objs:
            # Must satisfy PartitionPolicy (never touches 0x82, in allowable ranges)
            pol.check(wo.part, wo.obj)

        # Audit with verify_safety_of_objects
        NasBuilder.verify_safety_of_objects(write_objs)
