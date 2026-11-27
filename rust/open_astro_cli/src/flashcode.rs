use anyhow::{anyhow, Result};
use std::char;

pub fn luhn_check_digit(nibbles_12: &str) -> Result<char> {
    let cleaned = nibbles_12.replace(|c: char| !c.is_alphanumeric(), "").to_uppercase();
    if cleaned.len() != 12 || !cleaned.chars().all(|c| c.is_digit(16)) {
        return Err(anyhow!("Input must be exactly 12 hex characters"));
    }

    let mut sum = 0;
    for (i, c) in cleaned.chars().enumerate() {
        let val = c.to_digit(16).unwrap() as u8;
        let mut doubled = if i % 2 == 0 {
            val * 2
        } else {
            val
        };

        if doubled >= 10 {
            doubled = (doubled / 10) + (doubled % 10);
        }

        sum += doubled as u32;
    }

    let check_digit = (10 - (sum % 10)) % 10;
    Ok(std::char::from_digit(check_digit, 10).unwrap())
}

pub fn format_flashcode(nibbles_12: &str) -> Result<String> {
    let cleaned = nibbles_12.replace(|c: char| !c.is_alphanumeric(), "").to_uppercase();
    if cleaned.len() != 12 || !cleaned.chars().all(|c| c.is_digit(16)) {
        return Err(anyhow!("Input must be exactly 12 hex characters"));
    }

    let check_digit = luhn_check_digit(&cleaned)?;
    Ok(format!("{}-{}-{}", &cleaned[0..6], &cleaned[6..12], check_digit))
}

pub fn set_feature_bit(nibbles_12: &str, nibble_idx: usize, bit_mask: u8, enabled: bool) -> Result<String> {
    let cleaned = nibbles_12.replace(|c: char| !c.is_alphanumeric(), "").to_uppercase();
    if cleaned.len() != 12 || !cleaned.chars().all(|c| c.is_digit(16)) {
        return Err(anyhow!("Input must be exactly 12 hex characters"));
    }

    if nibble_idx >= 12 {
        return Err(anyhow!("Nibble index must be between 0 and 11"));
    }

    let mut bytes: Vec<u8> = cleaned.chars().map(|c| c.to_digit(16).unwrap() as u8).collect();
    let bit_value = if enabled { bit_mask } else { 0 };
    bytes[nibble_idx] = (bytes[nibble_idx] & !bit_mask) | bit_value;

    Ok(bytes.iter().map(|b| format!("{:X}", b & 0x0F)).collect())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RadioFamily {
    Portable,
    Mobile,
    Unknown,
}

impl std::fmt::Display for RadioFamily {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RadioFamily::Portable => write!(f, "Portable (XTS / PRC-153 · Q/H Options)"),
            RadioFamily::Mobile => write!(f, "Mobile (XTL / PM · G* Options)"),
            RadioFamily::Unknown => write!(f, "Unknown"),
        }
    }
}

/// Detect Portable (`XTS`/`PRC-153`/`H##`) vs Mobile (`XTL`/`PM 1500`/`M##`) from model string.
/// Note: checks Portable tokens before `M##` so `"Motorola XTS 5000"` never false-positives as Mobile.
pub fn detect_family_from_model(model: &str) -> RadioFamily {
    let m = model.trim().to_ascii_uppercase();
    if m.contains("XTS") || m.contains("PRC") || m.contains("MT 1500") || m.contains("PR 1500") {
        return RadioFamily::Portable;
    }
    if m.contains("XTL") || m.contains("PM 1500") {
        return RadioFamily::Mobile;
    }
    let bytes = m.as_bytes();
    if bytes.len() >= 3 && bytes[1].is_ascii_digit() && bytes[2].is_ascii_digit() {
        if bytes[0] == b'H' {
            return RadioFamily::Portable;
        }
        if bytes[0] == b'M' {
            return RadioFamily::Mobile;
        }
    }
    RadioFamily::Unknown
}

/// Block cross-flashing Portable <-> Mobile codeplugs onto mismatched radio hardware.
pub fn guard_family_match(radio_model: &str, codeplug_model: &str) -> Result<RadioFamily> {
    let rf = detect_family_from_model(radio_model);
    let cf = detect_family_from_model(codeplug_model);
    if rf != RadioFamily::Unknown && cf != RadioFamily::Unknown && rf != cf {
        return Err(anyhow!(
            "Cross-flash blocked: connected radio is {} ('{}'), but codeplug is {} ('{}')",
            rf, radio_model, cf, codeplug_model
        ));
    }
    Ok(if rf != RadioFamily::Unknown { rf } else { cf })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_flashcode() {
        assert_eq!(format_flashcode("000008002410").unwrap(), "000008-002410-2");
        assert_eq!(format_flashcode("FBFFFFB7F3FF").unwrap(), "FBFFFF-B7F3FF-1");
    }

    #[test]
    fn test_set_feature_bit() {
        let updated = set_feature_bit("000008002410", 8, 0x04, true).unwrap();
        assert_eq!(updated, "000008006410");
        assert_eq!(format_flashcode(&updated).unwrap(), "000008-006410-3");
    }

    #[test]
    fn test_detect_and_guard_radio_family() {
        assert_eq!(detect_family_from_model("Motorola XTS 5000 Model III"), RadioFamily::Portable);
        assert_eq!(detect_family_from_model("H46UCF9PW6BN"), RadioFamily::Portable);
        assert_eq!(detect_family_from_model("XTL 5000 O5"), RadioFamily::Mobile);
        assert_eq!(detect_family_from_model("M20URS9PW1AN"), RadioFamily::Mobile);
        assert!(guard_family_match("Motorola XTS 5000 Model III", "H46UCF9PW6BN").is_ok());
        assert!(guard_family_match("Motorola XTS 5000 Model III", "XTL 5000").is_err());
    }
}
