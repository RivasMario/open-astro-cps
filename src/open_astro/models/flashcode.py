"""
Motorola ASTRO 25 Flashcode Decoder & Feature Matrix.
Decodes 12-digit ASTRO 25 / XTS / XTL flashcodes (e.g., 500008-000488-2).
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class FlashcodeFeature:
    code: str
    name: str
    description: str

# Feature bit definitions by nibble index (0 to 11) and bit mask (1, 2, 4, 8)
FLASHCODE_MATRIX: Dict[Tuple[int, int], FlashcodeFeature] = {
    # Nibble 0
    (0, 8): FlashcodeFeature("H38/G24", "SmartZone Systems Software", "Enables SmartZone wide-area trunking operation"),
    (0, 4): FlashcodeFeature("Q806/G806", "ASTRO Digital Operation", "Enables ASTRO IMBE digital voice CAI"),
    (0, 2): FlashcodeFeature("H35", "Conventional Systems Software", "Enables conventional analog and digital channels"),
    (0, 1): FlashcodeFeature("Q173/G173", "SmartZone Omnilink", "Multi-zone SmartZone roaming and wide-area networking"),

    # Nibble 1
    (1, 8): FlashcodeFeature("H14/G114", "Enhanced Digital ID Display", "Displays caller P25 radio ID on screen"),
    (1, 4): FlashcodeFeature("H869", "Hardware Multikey Encryption", "Enables multi-key encryption UCM module support"),
    (1, 2): FlashcodeFeature("H37/G50", "SmartNet Systems Software", "Type II SmartNet trunking protocol"),
    (1, 1): FlashcodeFeature("Q387", "Conventional Voting Scan", "Receiver voting across multiple repeater sites"),

    # Nibble 2
    (2, 8): FlashcodeFeature("Q352", "Soft ID", "Transmits digital unit ID over MDC-1200 / ASTRO"),
    (2, 4): FlashcodeFeature("Q351", "StatAlert (MDC-1200)", "MDC-1200 analog signaling, PTT ID, and call alert"),
    (2, 2): FlashcodeFeature("Q498", "Junior OTAR", "Over-the-Air Rekeying for single keyset systems"),
    (2, 1): FlashcodeFeature("Q388", "Tactical OTAR", "Tactical tactical over-the-air rekeying protocol"),

    # Nibble 3
    (3, 8): FlashcodeFeature("H02/G90", "Enhanced Secure Operation", "Advanced encryption key strapping and multi-key support"),
    (3, 4): FlashcodeFeature("Q947", "APCO Packet Data Interface", "P25 raw packet data transfer / GPS / IP"),
    (3, 2): FlashcodeFeature("Q157", "Emergency Call", "Emergency button transmission and alarm dispatch"),
    (3, 1): FlashcodeFeature("Q390", "Dual Priority Scan", "Monitors two priority channels while scanning"),

    # Nibble 4
    (4, 8): FlashcodeFeature("Q182", "Radio Control Protocol", "Serial computer control and remote head protocol"),
    (4, 4): FlashcodeFeature("Q391", "Over the Air Scanning", "Centralized scan list management from system controller"),
    (4, 2): FlashcodeFeature("Q398", "Mixed Mode Operation", "Seamless automatic switching between Analog and Digital P25"),
    (4, 1): FlashcodeFeature("Q445", "Fireground Accountability", "Accountability software for tactical incident command"),

    # Nibble 5
    (5, 8): FlashcodeFeature("Q53", "Front Panel Programming (FPP)", "Allows full channel frequency and tone programming from keypad"),
    (5, 4): FlashcodeFeature("Q446", "Fireground Voice", "Specialized audio filtering for PASS alarms and SCBA masks"),
    (5, 2): FlashcodeFeature("Q361/G361", "P25 Digital CAI", "Project 25 Common Air Interface Phase 1 FDMA"),
    (5, 1): FlashcodeFeature("Q52", "Federal Government FPP", "Restricted military / federal FPP mode"),

    # Nibble 6
    (6, 8): FlashcodeFeature("H46", "One-Touch Status/Message", "Instant status update signaling buttons"),
    (6, 4): FlashcodeFeature("H868", "Multikey Operation", "Stores up to 48 unique encryption keys"),
    (6, 2): FlashcodeFeature("H18/G18", "Enhanced Trunking", "Failsoft, dynamic regrouping, and private calls"),
    (6, 1): FlashcodeFeature("Q179", "Direct Frequency Entry", "Direct numeric keypad frequency entry"),

    # Nibble 7
    (7, 8): FlashcodeFeature("Q399", "Advanced System Key (ASK)", "Hardware USB dongle security key support"),
    (7, 4): FlashcodeFeature("Q374", "Enhanced Zone/Channel", "Up to 512 channels across multiple zones"),
    (7, 2): FlashcodeFeature("Q447", "Digital Tone Signaling", "P25 digital selective paging and alerting"),
    (7, 1): FlashcodeFeature("Q574", "Enhanced Channel Scan", "Talkgroup scan and multi-system priority scan"),

    # Nibble 8
    (8, 8): FlashcodeFeature("H39", "Selective Call Decode", "Decodes individual private unit calls"),
    (8, 4): FlashcodeFeature("Q667", "Motorola ADP Encryption", "Software 40-bit RC4 encryption (no hardware UCM required)"),
    (8, 2): FlashcodeFeature("Q888", "Software System Key (SSK)", "Software file-based system key authentication"),
    (8, 1): FlashcodeFeature("Q375", "Unit-to-Unit Call", "Direct radio-to-radio digital private conversation"),

    # Nibble 9
    (9, 8): FlashcodeFeature("H865", "DES / DES-OFB / DES-XL", "Standard 56-bit DES cryptographic algorithm"),
    (9, 4): FlashcodeFeature("H869", "AES-256 Encryption", "Type-1 / FIPS 140-2 AES-256 hardware cryptographic module"),
    (9, 2): FlashcodeFeature("Q575", "Call Alert Decode", "Displays incoming paging alerts from dispatch"),
    (9, 1): FlashcodeFeature("Q448", "Secondary P25 Control", "Multi-frequency control channel hunting"),

    # Nibble 10
    (10, 8): FlashcodeFeature("Q507", "12.5 kHz Channel Spacing", "Mandatory narrow-band channel raster"),
    (10, 4): FlashcodeFeature("Q508", "25.0 kHz Channel Spacing", "Wide-band channel spacing (pre-narrowbanding / marine / amateur)"),
    (10, 2): FlashcodeFeature("Q376", "Private Conversation", "Encrypted private calling support"),
    (10, 1): FlashcodeFeature("Q362", "ASTRO 25 TDMA Phase 2", "P25 Phase 2 2-slot TDMA operation"),

    # Nibble 11
    (11, 8): FlashcodeFeature("Q363", "Dynamic Dual Mode (DDM)", "Automatic migration between Phase 1 and Phase 2 TDMA"),
    (11, 4): FlashcodeFeature("Q576", "Emergency Alarm & Voice", "High-priority emergency preemptive transmission"),
    (11, 2): FlashcodeFeature("Q377", "Radio Inhibit (Stun/Kill)", "Over-the-air remote radio stun and disable"),
    (11, 1): FlashcodeFeature("Q577", "Failsoft Operation", "Repeater fallback mode during system infrastructure loss")
}


# Q667 "Motorola ADP Encryption" lives at nibble 8, bit 4.
ADP_Q667 = (8, 4)

# Feature bits that need physical hardware the radio may not have installed.
# Setting the flashcode bit does NOT activate these without the module; the tool
# warns when one is enabled so nobody expects e.g. AES from a bit flip alone.
HARDWARE_GATED = {
    (1, 4): "H869 Hardware Multikey (needs UCM)",
    (6, 4): "H868 Multikey 48-key (needs UCM)",
    (7, 8): "Q399 Advanced System Key (needs USB dongle)",
    (9, 8): "H865 DES/DES-XL (needs crypto module)",
    (9, 4): "H869 AES-256 (needs UCM crypto module)",
}


def luhn_check_digit(payload: str) -> str:
    """Compute the Motorola ASTRO 25 flashcode check digit.

    VERIFIED-BIN: PatPort.exe `conCalculateFlashcode` @ VA 0x00a0b631 (check core
    0xa0bbe1-0xa0bd96). Standard Luhn mod-10 over the 12 nibble VALUES, with the
    even-from-left indices {0,2,4,6,8,10} doubled; each doubled value is split into
    its tens+units digits and summed (idiv 10). check = (10 - total % 10) % 10.
    """
    p = payload.strip().upper()
    if len(p) != 12:
        raise ValueError(f"flashcode payload must be 12 hex nibbles, got {len(p)}")
    total = 0
    for i, ch in enumerate(p):
        n = int(ch, 16)                      # 0..15; raises ValueError on non-hex
        d = 2 * n if i % 2 == 0 else n       # even indices (0-based, from left) doubled
        total += (d // 10) + (d % 10)        # sum the decimal digits of d
    return str((10 - total % 10) % 10)       # single decimal digit 0..9


def format_flashcode(payload: str) -> str:
    """12-nibble payload -> canonical `AAAAAA-BBBBBB-C` with computed check digit."""
    p = payload.strip().upper()
    if len(p) != 12:
        raise ValueError(f"flashcode payload must be 12 hex nibbles, got {len(p)}")
    return f"{p[:6]}-{p[6:12]}-{luhn_check_digit(p)}"


def verify_flashcode(full: str) -> bool:
    """True if the trailing check digit of a full `AAAAAA-BBBBBB-C` is correct."""
    clean = full.strip().upper().replace("-", "")
    if len(clean) != 13:
        raise ValueError("full flashcode must be 13 chars (12 payload + 1 check)")
    return luhn_check_digit(clean[:12]) == clean[12]


def set_feature(payload: str, nibble: int, bit: int, on: bool = True) -> str:
    """Return a new 12-nibble payload with (nibble, bit) set or cleared."""
    if not (0 <= nibble <= 11):
        raise ValueError("nibble index must be 0..11")
    if bit not in (1, 2, 4, 8):
        raise ValueError("bit must be one of 1, 2, 4, 8")
    chars = list(payload.strip().upper())
    v = int(chars[nibble], 16)
    chars[nibble] = "%X" % ((v | bit) if on else (v & ~bit))
    return "".join(chars)


def feature_bits(payload: str):
    """Yield (nibble, bit) for every set feature bit in the payload."""
    p = payload.strip().upper()
    for i, ch in enumerate(p):
        n = int(ch, 16)
        for b in (8, 4, 2, 1):
            if n & b:
                yield (i, b)


# Friendly CLI feature slugs -> (nibble, bit), mirroring FLASHCODE_MATRIX.
# Anything whose (nibble,bit) is in HARDWARE_GATED needs a UCM/dongle. ADP is
# SOFTWARE (no UCM). Names are stable CLI identifiers.
FEATURE_FLAGS = {
    "astro-digital": (0, 4), "conventional": (0, 2), "smartzone": (0, 8), "omnilink": (0, 1),
    "digital-id": (1, 8), "hw-multikey": (1, 4), "smartnet": (1, 2), "voting-scan": (1, 1),
    "soft-id": (2, 8), "statalert": (2, 4), "otar-junior": (2, 2), "otar-tactical": (2, 1),
    "enhanced-secure": (3, 8), "packet-data": (3, 4), "emergency": (3, 2), "dual-priority-scan": (3, 1),
    "radio-control": (4, 8), "ota-scanning": (4, 4), "mixed-mode": (4, 2), "fireground-acct": (4, 1),
    "fpp": (5, 8), "fireground-voice": (5, 4), "p25": (5, 2), "fed-fpp": (5, 1),
    "status-msg": (6, 8), "multikey-48": (6, 4), "enhanced-trunking": (6, 2), "direct-freq-entry": (6, 1),
    "ask": (7, 8), "enhanced-zone": (7, 4), "digital-tone-sig": (7, 2), "enhanced-scan": (7, 1),
    "selective-call": (8, 8), "adp": (8, 4), "software-sys-key": (8, 2), "unit-to-unit": (8, 1),
    "des": (9, 8), "aes-256": (9, 4), "call-alert": (9, 2), "secondary-p25": (9, 1),
    "spacing-12.5": (10, 8), "spacing-25": (10, 4), "private-conv": (10, 2), "tdma-p2": (10, 1),
    "ddm": (11, 8), "emergency-alarm": (11, 4), "radio-inhibit": (11, 2), "failsoft": (11, 1),
}


def software_feature_slugs():
    """Feature slugs that do NOT need a UCM/dongle (safe on a no-UCM radio)."""
    return [s for s, nb in FEATURE_FLAGS.items() if nb not in HARDWARE_GATED]


# Curated preset loads. `recommended` is a sane no-UCM P25 conventional radio;
# the `max-*` presets are built programmatically in the CLI (all bits, UCM-gated).
PROFILES = {
    "recommended": [
        "astro-digital", "conventional", "p25", "tdma-p2", "fpp", "enhanced-scan",
        "enhanced-zone", "emergency", "emergency-alarm", "direct-freq-entry",
        "mixed-mode", "adp", "unit-to-unit", "selective-call", "call-alert", "failsoft",
    ],
}


class FlashcodeDecoder:
    """
    Decodes Motorola ASTRO 25 flashcode strings into human-readable feature lists.
    """
    @classmethod
    def clean_flashcode(cls, raw: str) -> str:
        """Strip hyphens, spaces, and checksum."""
        clean = raw.strip().upper()
        # Format usually: 123456-123456-C or 123456123456
        parts = clean.split("-")
        if len(parts) >= 2:
            return parts[0] + parts[1]
        return clean[:12]

    @classmethod
    def decode(cls, flashcode_str: str) -> List[FlashcodeFeature]:
        cleaned = cls.clean_flashcode(flashcode_str)
        if len(cleaned) < 12:
            raise ValueError(f"Invalid flashcode length '{flashcode_str}'. Expected 12 hexadecimal characters.")

        enabled_features = []
        for i, char in enumerate(cleaned[:12]):
            try:
                nibble = int(char, 16)
            except ValueError:
                raise ValueError(f"Invalid hexadecimal character '{char}' in flashcode.")

            for bit in [8, 4, 2, 1]:
                if nibble & bit:
                    key = (i, bit)
                    if key in FLASHCODE_MATRIX:
                        enabled_features.append(FLASHCODE_MATRIX[key])
                    else:
                        enabled_features.append(
                            FlashcodeFeature(f"OPT_{i}_{bit}", f"Option Nibble {i} Bit {bit}", "Proprietary option")
                        )

        return enabled_features
