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
}
