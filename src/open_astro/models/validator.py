"""
Codeplug Safety & Compliance Validator for OpenAstro CPS.
Prevents accidental RF interference on emergency services and verifies hardware constraints.
"""
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from .codeplug import RadioCodeplug, Zone, Channel, EncryptionKey

@dataclass
class ValidationIssue:
    severity: str  # "ERROR", "WARNING", "INFO"
    location: str  # e.g., "Zone 1, Ch 2"
    message: str

class CodeplugValidator:
    STANDARD_PL_TONES = {
        67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
        94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
        131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 167.9, 173.8,
        179.9, 186.2, 192.8, 203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6,
        241.8, 250.3, 254.1
    }

    BAND_LIMITS = {
        "700/800": (764.0, 870.0),
        "800": (806.0, 870.0),
        "uhf": (380.0, 520.0),
        "vhf": (136.0, 174.0)
    }

    @classmethod
    def validate(cls, codeplug: RadioCodeplug) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1. Radio identity checks
        if not codeplug.radio_model:
            issues.append(ValidationIssue("ERROR", "Radio Info", "Radio model must be specified."))
        if not codeplug.bandsplit:
            issues.append(ValidationIssue("WARNING", "Radio Info", "Bandsplit is missing or undefined."))

        # Determine band limits
        band_min, band_max = 0.0, 1000.0
        bandsplit_lower = (codeplug.bandsplit or "").lower()
        for key, limits in cls.BAND_LIMITS.items():
            if key in bandsplit_lower:
                band_min, band_max = limits
                break

        # Collect defined key IDs
        defined_keys = {k.key_id: k for k in codeplug.encryption_keys}

        # 2. Zone & Channel validation
        if not codeplug.zones:
            issues.append(ValidationIssue("ERROR", "Codeplug", "Codeplug contains zero zones."))

        for z in codeplug.zones:
            loc_z = f"Zone {z.zone_number} ({z.name})"
            if len(z.name) > 16:
                issues.append(ValidationIssue("WARNING", loc_z, f"Zone name exceeds 16 chars ({len(z.name)} chars). May truncate on radio LCD."))
            if not z.channels:
                issues.append(ValidationIssue("WARNING", loc_z, "Zone has no channels defined."))

            for ch in z.channels:
                loc_ch = f"Zone {z.zone_number}, Ch {ch.channel_number} ({ch.name})"

                # Channel Name length
                if len(ch.name) > 14:
                    issues.append(ValidationIssue("WARNING", loc_ch, f"Channel name exceeds 14 chars ({len(ch.name)} chars). May truncate on XTS display."))

                # Frequency range
                if ch.rx_frequency < band_min or ch.rx_frequency > band_max:
                    issues.append(ValidationIssue("ERROR", loc_ch, f"Rx frequency {ch.rx_frequency:.5f} MHz is outside bandsplit limits ({band_min}-{band_max} MHz)."))
                if ch.tx_frequency < band_min or ch.tx_frequency > band_max:
                    issues.append(ValidationIssue("ERROR", loc_ch, f"Tx frequency {ch.tx_frequency:.5f} MHz is outside bandsplit limits ({band_min}-{band_max} MHz)."))

                # The Golden Rule: Public safety frequencies (851-869 MHz) with names containing CTRL/PSERN/DISP/POLICE/FIRE must be RX-ONLY
                is_ps_label = any(kw in ch.name.upper() for kw in ["CTRL", "PSERN", "DISP", "POLICE", "FIRE", "EMS", "STATE PATROL", "WSP"])
                if is_ps_label and not ch.rx_only:
                    issues.append(ValidationIssue(
                        "ERROR",
                        loc_ch,
                        "CRITICAL SAFETY VIOLATION: Public safety / trunked control channel does NOT have rx_only=true! Pressing PTT could cause unlawful emergency interference."
                    ))

                # Encryption consistency
                if ch.secure_strapping == "Secure":
                    if ch.key_id is None:
                        issues.append(ValidationIssue("ERROR", loc_ch, "Channel is set to Secure but key_id is not specified."))
                    elif ch.key_id not in defined_keys:
                        issues.append(ValidationIssue("ERROR", loc_ch, f"Referenced Key ID {ch.key_id} is not defined in codeplug encryption_keys table."))

                # Voice type and tones / NAC
                if ch.voice_type == "Analog":
                    if ch.rx_pl_tone and ch.rx_pl_tone not in cls.STANDARD_PL_TONES:
                        issues.append(ValidationIssue("WARNING", loc_ch, f"Rx CTCSS tone {ch.rx_pl_tone} Hz is not a standard EIA tone."))
                    if ch.tx_pl_tone and ch.tx_pl_tone not in cls.STANDARD_PL_TONES:
                        issues.append(ValidationIssue("WARNING", loc_ch, f"Tx CTCSS tone {ch.tx_pl_tone} Hz is not a standard EIA tone."))
                elif ch.voice_type == "ASTRO P25":
                    # NAC checks
                    for nac_val, nac_lbl in [(ch.rx_nac, "Rx NAC"), (ch.tx_nac, "Tx NAC")]:
                        if nac_val:
                            clean_nac = nac_val.replace("$", "").replace("0x", "").strip()
                            if not re.fullmatch(r"[0-9A-Fa-f]{3}", clean_nac):
                                issues.append(ValidationIssue("ERROR", loc_ch, f"{nac_lbl} '{nac_val}' must be a valid 3-digit hex NAC (e.g. $293)."))

        return issues
