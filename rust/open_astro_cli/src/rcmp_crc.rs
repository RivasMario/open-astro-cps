use anyhow::{bail, Result};

pub fn crc16_ccitt(data: &[u8]) -> u16 {
    let mut crc: u16 = 0x0000;
    for &byte in data {
        crc ^= (byte as u16) << 8;
        for _ in 0..8 {
            if crc & 0x8000 != 0 {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    crc
}

pub fn frame_with_crc(payload_no_crc: &[u8]) -> Vec<u8> {
    let length = (payload_no_crc.len() + 2) as u16;
    let mut framed = vec![(length >> 8) as u8, length as u8];
    framed.extend_from_slice(payload_no_crc);
    let crc = crc16_ccitt(&framed[2..]);
    framed.push((crc >> 8) as u8);
    framed.push(crc as u8);
    framed
}

pub fn verify_and_strip_crc(body: &[u8]) -> Result<&[u8]> {
    if body.len() < 2 {
        bail!("Body too short to contain CRC");
    }
    let calculated_crc = crc16_ccitt(&body[..body.len() - 2]);
    let received_crc = (body[body.len() - 2] as u16) << 8 | body[body.len() - 1] as u16;
    if calculated_crc != received_crc {
        bail!("CRC mismatch");
    }
    Ok(&body[..body.len() - 2])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frame_and_verify() {
        let payload = b"\x01\x06\x00";
        let framed = frame_with_crc(payload);
        assert_eq!(framed[0..2], [0x00, 0x05]);
        let stripped = verify_and_strip_crc(&framed[2..]).unwrap();
        assert_eq!(stripped, payload);
    }

    #[test]
    fn test_corrupted_frame() {
        let payload = b"\x01\x06\x00";
        let mut framed = frame_with_crc(payload);
        framed[4] ^= 0xFF; // Corrupt one byte
        assert!(verify_and_strip_crc(&framed[2..]).is_err());
    }
}
