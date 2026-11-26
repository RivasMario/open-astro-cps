use anyhow::{bail, Result};

pub fn extract_serial_ascii(reply_body: &[u8]) -> Result<String> {
    let payload = if reply_body.len() > 12 {
        &reply_body[12..]
    } else {
        reply_body
    };

    let mut serial = String::new();
    for &byte in payload {
        if byte.is_ascii_alphanumeric() {
            serial.push(byte as char);
        }
    }

    if serial.is_empty() {
        bail!("No printable ASCII alphanumeric characters found in the reply body.");
    }

    Ok(serial)
}

pub fn verify_expected_serial(actual: &str, expected: &str) -> Result<()> {
    if expected.is_empty() {
        bail!("Expected serial cannot be empty.");
    }

    let trimmed_actual = actual.trim().to_ascii_lowercase();
    let trimmed_expected = expected.trim().to_ascii_lowercase();

    if trimmed_actual.contains(&trimmed_expected) || trimmed_actual == trimmed_expected {
        Ok(())
    } else {
        bail!("Serial mismatch: actual={}, expected={}", actual, expected);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_serial_ascii() {
        let reply_body = b"0123456789AB205CFR2930";
        assert_eq!(
            extract_serial_ascii(reply_body).unwrap(),
            "205CFR2930"
        );

        let short_reply_body = b"205CFR2930";
        assert_eq!(
            extract_serial_ascii(short_reply_body).unwrap(),
            "205CFR2930"
        );

        let no_ascii_reply_body = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x00\xff";
        assert!(extract_serial_ascii(no_ascii_reply_body).is_err());
    }

    #[test]
    fn test_verify_expected_serial() {
        assert!(verify_expected_serial("205CFR2930", "205CFR2930").is_ok());
        assert!(verify_expected_serial("205CFR2930", "205cfr2930").is_ok());
        assert!(verify_expected_serial("205CFR2930", "205").is_ok());
        assert!(verify_expected_serial("205CFR2930", "206CFR2930").is_err());
        assert!(verify_expected_serial("205CFR2930", "").is_err());
    }
}
