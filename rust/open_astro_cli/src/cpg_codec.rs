// src/cpg_codec.rs

pub const LEGACY_CPG_KEY: &[u8] = b"A8Z6J9QP5";

pub fn rc4_crypt(key: &[u8], data: &[u8]) -> Vec<u8> {
    let mut s: [u8; 256] = std::array::from_fn(|i| i as u8);
    let mut j = 0;

    // Key Scheduling Algorithm (KSA)
    for i in 0..256 {
        j = (j + s[i] as usize + key[i % key.len()] as usize) % 256;
        s.swap(i, j);
    }

    // Pseudo-random generation algorithm (PRGA)
    let mut i = 0;
    j = 0;
    let mut result = Vec::with_capacity(data.len());

    for &byte in data {
        i = (i + 1) % 256;
        j = (j + s[i] as usize) % 256;
        s.swap(i, j);
        let k = s[(s[i] as usize + s[j] as usize) % 256];
        result.push(byte ^ k);
    }

    result
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CpgDirEntry {
    pub item_id: u16,
    pub instance: u16,
    pub partition: u8,
    pub stream_crc: u16,
    pub stream_num: u16,
}

pub fn parse_cpg_directory(strm0_decrypted: &[u8]) -> anyhow::Result<Vec<CpgDirEntry>> {
    if strm0_decrypted.len() < 2 || (strm0_decrypted.len() - 2) % 10 != 0 {
        return Err(anyhow::anyhow!("Invalid directory length"));
    }

    let mut entries = Vec::new();
    let num_entries = (strm0_decrypted.len() - 2) / 10;

    for i in 0..num_entries {
        let offset = i * 10;
        entries.push(CpgDirEntry {
            item_id: u16::from_be_bytes([strm0_decrypted[offset], strm0_decrypted[offset + 1]]),
            instance: u16::from_be_bytes([strm0_decrypted[offset + 2], strm0_decrypted[offset + 3]]),
            partition: strm0_decrypted[offset + 4],
            stream_crc: u16::from_be_bytes([strm0_decrypted[offset + 5], strm0_decrypted[offset + 6]]),
            stream_num: u16::from_be_bytes([strm0_decrypted[offset + 7], strm0_decrypted[offset + 8]]),
        });
    }

    Ok(entries)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rc4_crypt() {
        let key = LEGACY_CPG_KEY;
        let data = b"ASTRO25";
        let encrypted = rc4_crypt(key, data);
        let decrypted = rc4_crypt(key, &encrypted);
        assert_eq!(decrypted, data);
    }

    #[test]
    fn test_parse_cpg_directory() {
        let valid_data = [
            0x00, 0x01, 0x00, 0x02, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ];
        let invalid_data = [0x00, 0x01, 0x00, 0x02, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00];

        assert!(parse_cpg_directory(&valid_data).is_ok());
        assert!(parse_cpg_directory(&invalid_data).is_err());
    }
}
