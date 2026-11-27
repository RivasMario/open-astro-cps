use anyhow::{anyhow, Result};

pub const FLAG: u8 = 0x7E;
pub const ESCAPE: u8 = 0x7D;

pub fn hdlc_encode(payload: &[u8]) -> Vec<u8> {
    let mut encoded = vec![FLAG];
    for &byte in payload {
        match byte {
            FLAG | ESCAPE | 0x00..=0x1F => {
                encoded.push(ESCAPE);
                encoded.push(byte ^ 0x20);
            }
            _ => encoded.push(byte),
        }
    }
    encoded.push(FLAG);
    encoded
}

pub fn hdlc_decode(frame: &[u8]) -> Result<Vec<u8>> {
    if frame.len() < 2 || frame[0] != FLAG || frame[frame.len() - 1] != FLAG {
        return Err(anyhow!("Invalid HDLC frame"));
    }

    let mut decoded = Vec::new();
    let mut escape = false;
    for &byte in &frame[1..frame.len() - 1] {
        if escape {
            if byte < 0x20 || byte > 0x9F {
                return Err(anyhow!("Invalid escape sequence"));
            }
            decoded.push(byte ^ 0x20);
            escape = false;
        } else if byte == ESCAPE {
            escape = true;
        } else {
            decoded.push(byte);
        }
    }

    if escape {
        return Err(anyhow!("Truncated escape sequence"));
    }

    if decoded.is_empty() {
        return Err(anyhow!("Empty HDLC frame"));
    }

    Ok(decoded)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_round_trip() {
        let test_cases = vec![
            vec![0x7E, 0x7D, 0x00, 0x1F, 0x80],
            vec![0x00, 0x1F, 0x7E, 0x7D, 0x80],
            vec![0x7E, 0x7E, 0x7E],
            vec![0x00, 0x1F, 0x80],
        ];

        for test_case in test_cases {
            let encoded = hdlc_encode(&test_case);
            let decoded = hdlc_decode(&encoded).unwrap();
            assert_eq!(decoded, test_case);
        }
    }

    #[test]
    fn test_invalid_frame() {
        assert!(hdlc_decode(&[0x7E]).is_err());
        assert!(hdlc_decode(&[0x7E, 0x7E]).is_err());
        assert!(hdlc_decode(&[0x7E, 0x7D, 0x7E]).is_err());
        assert!(hdlc_decode(&[0x7E, 0x7D, 0x7D]).is_err());
    }

    #[test]
    fn test_truncated_escape() {
        assert!(hdlc_decode(&[0x7E, 0x7D, 0x7E]).is_err());
    }
}
