use anyhow::{anyhow, Result};
use std::io::{Read, Write};
use std::time::Duration;

use crate::hdlc::{hdlc_decode, hdlc_encode, FLAG};
use crate::ppp_ipcp::{build_ipcp_conf_req, decode_ppp, encode_ppp, PppPacket, PROTO_IPV4, PROTO_LCP};

pub const DEFAULT_BAUD: u32 = 115_200;

/// List all serial ports visible to the OS (COMx on Windows, /dev/ttyACM* on Linux).
pub fn list_serial_ports() -> Result<Vec<String>> {
    let ports = serialport::available_ports()?;
    Ok(ports.into_iter().map(|p| p.port_name).collect())
}

/// Open a serial port configured for ASTRO 25 8N1 CDC-ACM / serial transport.
pub fn open_astro_serial(port_name: &str, baud: u32, timeout_ms: u64) -> Result<Box<dyn serialport::SerialPort>> {
    let port = serialport::new(port_name, baud)
        .timeout(Duration::from_millis(timeout_ms))
        .open()?;
    Ok(port)
}

/// Build an LCP Configure-Request (id=1, async-map=0).
pub fn build_lcp_conf_req(id: u8) -> Vec<u8> {
    // Code=1 (Conf-Req), ID, Len=10, Opt 2 (ACCM): type=2, len=6, map=0x00000000
    encode_ppp(PROTO_LCP, &[0x01, id, 0x00, 0x0A, 0x02, 0x06, 0x00, 0x00, 0x00, 0x00])
}

/// Wrap a raw IPv4 packet inside PPP + async HDLC.
pub fn frame_ipv4_hdlc(ipv4_pkt: &[u8]) -> Vec<u8> {
    let ppp = encode_ppp(PROTO_IPV4, ipv4_pkt);
    hdlc_encode(&ppp)
}

/// Perform the Motorola USNET `"CLIENT"` -> `"CLIENTSERVER"` chat handshake on a serial port,
/// then send an initial LCP Configure-Request and IPCP Configure-Request (192.168.128.2).
pub fn probe_ppp_serial(port_name: &str, baud: u32) -> Result<Vec<PppPacket>> {
    let mut port = open_astro_serial(port_name, baud, 1500)?;
    port.write_all(b"CLIENT")?;
    port.flush()?;

    let mut banner = [0u8; 64];
    let n = port.read(&mut banner).unwrap_or(0);
    let banner_str = String::from_utf8_lossy(&banner[..n]);
    if !banner_str.contains("CLIENTSERVER") {
        return Err(anyhow!("Expected CLIENTSERVER banner, got: {:?}", banner_str));
    }

    let lcp = hdlc_encode(&build_lcp_conf_req(1));
    port.write_all(&lcp)?;
    let ipcp = hdlc_encode(&build_ipcp_conf_req(1, [192, 168, 128, 2]));
    port.write_all(&ipcp)?;
    port.flush()?;

    let mut raw = vec![0u8; 512];
    let rn = port.read(&mut raw).unwrap_or(0);
    let mut packets = Vec::new();
    let mut start = None;
    for (idx, &b) in raw[..rn].iter().enumerate() {
        if b == FLAG {
            if let Some(s) = start {
                if idx > s + 1 {
                    if let Ok(decoded) = hdlc_decode(&raw[s..=idx]) {
                        if let Ok(pkt) = decode_ppp(&decoded) {
                            packets.push(pkt);
                        }
                    }
                }
            }
            start = Some(idx);
        }
    }
    Ok(packets)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lcp_and_ipv4_framing() {
        let lcp = build_lcp_conf_req(1);
        let pkt = decode_ppp(&lcp).unwrap();
        assert_eq!(pkt.protocol, PROTO_LCP);
        assert_eq!(pkt.payload[0], 0x01);

        let hdlc = frame_ipv4_hdlc(&[0x45, 0x00, 0x00, 0x14]);
        let unframed = hdlc_decode(&hdlc).unwrap();
        let ip_pkt = decode_ppp(&unframed).unwrap();
        assert_eq!(ip_pkt.protocol, PROTO_IPV4);
        assert_eq!(ip_pkt.payload, vec![0x45, 0x00, 0x00, 0x14]);
    }
}
