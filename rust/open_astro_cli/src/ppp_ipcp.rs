use anyhow::{anyhow, Result};

pub const PROTO_LCP: u16 = 0xC021;
pub const PROTO_IPCP: u16 = 0x8021;
pub const PROTO_IPV4: u16 = 0x0021;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PppPacket {
    pub protocol: u16,
    pub payload: Vec<u8>,
}

pub fn encode_ppp(protocol: u16, payload: &[u8]) -> Vec<u8> {
    let mut packet = vec![0xFF, 0x03];
    packet.extend_from_slice(&protocol.to_be_bytes());
    packet.extend_from_slice(payload);
    packet
}

pub fn decode_ppp(raw: &[u8]) -> Result<PppPacket> {
    if raw.len() < 4 {
        return Err(anyhow!("Packet too short"));
    }

    let (address_control, protocol, payload) = if raw.starts_with(&[0xFF, 0x03]) {
        (&raw[0..2], &raw[2..4], &raw[4..])
    } else {
        (&raw[0..0], &raw[0..2], &raw[2..])
    };

    if address_control != b"\xFF\x03" && !address_control.is_empty() {
        return Err(anyhow!("Invalid address/control field"));
    }

    let protocol = u16::from_be_bytes([protocol[0], protocol[1]]);
    Ok(PppPacket {
        protocol,
        payload: payload.to_vec(),
    })
}

pub fn build_ipcp_conf_req(id: u8, local_ip: [u8; 4]) -> Vec<u8> {
    let mut payload = vec![1, id, 10, 3, 6];
    payload.extend_from_slice(&local_ip);
    encode_ppp(PROTO_IPCP, &payload)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_decode_ppp() {
        let protocol = PROTO_LCP;
        let payload = vec![1, 2, 3, 4];
        let encoded = encode_ppp(protocol, &payload);
        let decoded = decode_ppp(&encoded).unwrap();
        assert_eq!(decoded.protocol, protocol);
        assert_eq!(decoded.payload, payload);
    }

    #[test]
    fn test_build_ipcp_conf_req() {
        let id = 1;
        let local_ip = [192, 168, 128, 2];
        let encoded = build_ipcp_conf_req(id, local_ip);
        let decoded = decode_ppp(&encoded).unwrap();
        assert_eq!(decoded.protocol, PROTO_IPCP);
        assert_eq!(decoded.payload, vec![1, id, 10, 3, 6, 192, 168, 128, 2]);
    }
}
