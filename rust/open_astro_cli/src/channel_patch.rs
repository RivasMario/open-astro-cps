use anyhow::{bail, Result};

pub fn parse_adp_key(key_hex: &str) -> Result<[u8; 5]> {
    let key_hex = key_hex.trim().strip_prefix("0x").unwrap_or(key_hex);
    if key_hex.len() != 10 {
        bail!("Key must be exactly 10 hex characters (5 bytes)");
    }
    let mut key = [0u8; 5];
    for (i, chunk) in key_hex.as_bytes().chunks(2).enumerate() {
        key[i] = u8::from_str_radix(std::str::from_utf8(chunk).unwrap(), 16)?;
    }
    Ok(key)
}

pub fn patch_channel_name(table: &mut [u8], slot: usize, stride: usize, name: &str) -> Result<()> {
    if stride == 0 {
        bail!("Stride must be greater than 0");
    }
    let start = slot * stride;
    let end = (slot + 1) * stride;
    if end > table.len() {
        bail!("Slot out of bounds");
    }
    let bytes = name.as_bytes();
    let len = bytes.len().min(stride);
    table[start..start + len].copy_from_slice(&bytes[..len]);
    if len < stride {
        table[start + len..end].fill(b' ');
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_adp_key_valid() {
        assert_eq!(parse_adp_key("0123456789").unwrap(), [0x01, 0x23, 0x45, 0x67, 0x89]);
        assert_eq!(parse_adp_key("1234567890").unwrap(), [0x12, 0x34, 0x56, 0x78, 0x90]);
        assert_eq!(parse_adp_key("0x0123456789").unwrap(), [0x01, 0x23, 0x45, 0x67, 0x89]);
    }

    #[test]
    fn test_parse_adp_key_invalid() {
        assert!(parse_adp_key("012345678").is_err());
        assert!(parse_adp_key("01234567890").is_err());
        assert!(parse_adp_key("0x123456789G").is_err());
    }

    #[test]
    fn test_patch_channel_name_valid() {
        let mut table = vec![0u8; 20];
        patch_channel_name(&mut table, 0, 10, "OPEN ASTRO").unwrap();
        assert_eq!(&table[0..10], b"OPEN ASTRO");
        assert_eq!(&table[10..20], &[0u8; 10]);

        patch_channel_name(&mut table, 1, 10, "HELLO").unwrap();
        assert_eq!(&table[10..20], b"HELLO     ");
    }

    #[test]
    fn test_patch_channel_name_invalid() {
        let mut table = vec![0u8; 20];
        assert!(patch_channel_name(&mut table, 2, 10, "TOO LONG NAME").is_err());
        assert!(patch_channel_name(&mut table, 0, 0, "NAME").is_err());
    }
}
