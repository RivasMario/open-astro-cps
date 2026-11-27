use anyhow::{anyhow, Result};
use std::io::{Read, Write};
use std::time::Duration;

use crate::hdlc::{hdlc_decode, hdlc_encode, FLAG};
use crate::ppp_ipcp::{build_ipcp_conf_req, decode_ppp, encode_ppp, PppPacket, PROTO_IPV4, PROTO_LCP};

pub const DEFAULT_BAUD: u32 = 115_200;
pub const LOCAL_IP: [u8; 4] = [192, 168, 128, 2];
pub const RADIO_IP: [u8; 4] = [192, 168, 128, 1];
pub const DEFAULT_MSS: usize = 512;
pub const DEFAULT_WINDOW: u16 = 2048;

/// RFC 1662 PPP FCS-16 (poly 0x8408, init 0xFFFF, final XOR 0xFFFF).
pub fn fcs16(data: &[u8]) -> u16 {
    let mut crc: u16 = 0xFFFF;
    for &b in data {
        crc ^= b as u16;
        for _ in 0..8 {
            crc = if crc & 1 != 0 { (crc >> 1) ^ 0x8408 } else { crc >> 1 };
        }
    }
    crc ^ 0xFFFF
}

/// Frame a PPP packet with RFC 1662 FCS-16 (little-endian) + async HDLC stuffing.
pub fn frame_ppp_fcs(protocol: u16, payload: &[u8]) -> Vec<u8> {
    let mut ppp = encode_ppp(protocol, payload);
    let fcs = fcs16(&ppp);
    ppp.push((fcs & 0xFF) as u8);
    ppp.push((fcs >> 8) as u8);
    hdlc_encode(&ppp)
}

/// Decode an async HDLC frame, verify and strip RFC 1662 FCS-16, and parse PPP.
pub fn unframe_ppp_fcs(frame: &[u8]) -> Result<PppPacket> {
    let raw = hdlc_decode(frame)?;
    if raw.len() < 6 {
        return Err(anyhow!("PPP+FCS frame too short ({} bytes)", raw.len()));
    }
    let body = &raw[..raw.len() - 2];
    let got_fcs = u16::from_le_bytes([raw[raw.len() - 2], raw[raw.len() - 1]]);
    let want_fcs = fcs16(body);
    if got_fcs != want_fcs {
        return Err(anyhow!("PPP FCS mismatch: got 0x{:04X}, want 0x{:04X}", got_fcs, want_fcs));
    }
    decode_ppp(body)
}

fn inet_checksum(data: &[u8]) -> u16 {
    let mut sum: u32 = 0;
    let mut i = 0;
    while i + 1 < data.len() {
        sum += u16::from_be_bytes([data[i], data[i + 1]]) as u32;
        i += 2;
    }
    if i < data.len() {
        sum += (data[i] as u32) << 8;
    }
    while (sum >> 16) != 0 {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    !(sum as u16)
}

/// Build a minimal IPv4 + TCP segment (20B IP + 20B TCP + payload) for userspace PPP.
pub fn build_ipv4_tcp_segment(
    src_ip: [u8; 4],
    dst_ip: [u8; 4],
    src_port: u16,
    dst_port: u16,
    seq: u32,
    ack: u32,
    flags: u8,
    window: u16,
    payload: &[u8],
) -> Vec<u8> {
    let tcp_len = 20 + payload.len();
    let total_len = (20 + tcp_len) as u16;
    let mut pkt = vec![0u8; total_len as usize];

    // IPv4 header
    pkt[0] = 0x45;
    pkt[2..4].copy_from_slice(&total_len.to_be_bytes());
    pkt[8] = 64; // TTL
    pkt[9] = 6;  // TCP
    pkt[12..16].copy_from_slice(&src_ip);
    pkt[16..20].copy_from_slice(&dst_ip);
    let ip_csum = inet_checksum(&pkt[0..20]);
    pkt[10..12].copy_from_slice(&ip_csum.to_be_bytes());

    // TCP header
    let tcp = &mut pkt[20..];
    tcp[0..2].copy_from_slice(&src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&dst_port.to_be_bytes());
    tcp[4..8].copy_from_slice(&seq.to_be_bytes());
    tcp[8..12].copy_from_slice(&ack.to_be_bytes());
    tcp[12] = 0x50; // data offset = 5 (20 bytes)
    tcp[13] = flags;
    tcp[14..16].copy_from_slice(&window.to_be_bytes());
    tcp[20..].copy_from_slice(payload);

    // TCP pseudo-header checksum
    let mut pseudo = Vec::with_capacity(12 + tcp_len);
    pseudo.extend_from_slice(&src_ip);
    pseudo.extend_from_slice(&dst_ip);
    pseudo.push(0);
    pseudo.push(6);
    pseudo.extend_from_slice(&(tcp_len as u16).to_be_bytes());
    pseudo.extend_from_slice(tcp);
    let tcp_csum = inet_checksum(&pseudo);
    pkt[20 + 16..20 + 18].copy_from_slice(&tcp_csum.to_be_bytes());
    pkt
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsedTcpSegment {
    pub src_port: u16,
    pub dst_port: u16,
    pub seq: u32,
    pub ack: u32,
    pub flags: u8,
    pub window: u16,
    pub payload: Vec<u8>,
}

/// Parse an IPv4 + TCP segment received over PPP (proto 0x0021).
pub fn parse_ipv4_tcp_segment(pkt: &[u8]) -> Result<ParsedTcpSegment> {
    if pkt.len() < 40 || (pkt[0] >> 4) != 4 || pkt[9] != 6 {
        return Err(anyhow!("Not an IPv4/TCP packet"));
    }
    let ihl = ((pkt[0] & 0x0F) as usize) * 4;
    if pkt.len() < ihl + 20 {
        return Err(anyhow!("Truncated IPv4/TCP header"));
    }
    let tcp = &pkt[ihl..];
    let data_off = ((tcp[12] >> 4) as usize) * 4;
    if tcp.len() < data_off {
        return Err(anyhow!("Truncated TCP options"));
    }
    Ok(ParsedTcpSegment {
        src_port: u16::from_be_bytes([tcp[0], tcp[1]]),
        dst_port: u16::from_be_bytes([tcp[2], tcp[3]]),
        seq: u32::from_be_bytes([tcp[4], tcp[5], tcp[6], tcp[7]]),
        ack: u32::from_be_bytes([tcp[8], tcp[9], tcp[10], tcp[11]]),
        flags: tcp[13],
        window: u16::from_be_bytes([tcp[14], tcp[15]]),
        payload: tcp[data_off..].to_vec(),
    })
}

/// Stateful userspace TCP-over-PPP session (host 192.168.128.2:8001 <-> radio 192.168.128.1:8002).
pub struct PppTcpSession {
    pub local_port: u16,
    pub remote_port: u16,
    pub seq: u32,
    pub ack: u32,
    pub peer_window: u16,
}

impl PppTcpSession {
    pub fn new(local_port: u16, remote_port: u16, initial_seq: u32) -> Self {
        Self {
            local_port,
            remote_port,
            seq: initial_seq,
            ack: 0,
            peer_window: DEFAULT_WINDOW,
        }
    }

    /// Build initial TCP SYN framed in PPP+FCS+HDLC.
    pub fn build_syn_hdlc(&mut self) -> Vec<u8> {
        let seg = build_ipv4_tcp_segment(
            LOCAL_IP, RADIO_IP, self.local_port, self.remote_port,
            self.seq, 0, 0x02, DEFAULT_WINDOW, &[],
        );
        self.seq = self.seq.wrapping_add(1);
        frame_ipv4_hdlc(&seg)
    }

    /// Chunk an outbound RCMP payload into MSS-bounded (<= 512B) PSH+ACK HDLC frames.
    pub fn encode_data_frames(&mut self, data: &[u8]) -> Vec<Vec<u8>> {
        let mut frames = Vec::new();
        for chunk in data.chunks(DEFAULT_MSS) {
            let seg = build_ipv4_tcp_segment(
                LOCAL_IP, RADIO_IP, self.local_port, self.remote_port,
                self.seq, self.ack, 0x18, DEFAULT_WINDOW, chunk,
            );
            self.seq = self.seq.wrapping_add(chunk.len() as u32);
            frames.push(frame_ipv4_hdlc(&seg));
        }
        frames
    }
}

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
    encode_ppp(PROTO_LCP, &[0x01, id, 0x00, 0x0A, 0x02, 0x06, 0x00, 0x00, 0x00, 0x00])
}

/// Wrap a raw IPv4 packet inside PPP + FCS-16 + async HDLC.
pub fn frame_ipv4_hdlc(ipv4_pkt: &[u8]) -> Vec<u8> {
    frame_ppp_fcs(PROTO_IPV4, ipv4_pkt)
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

    let lcp = frame_ppp_fcs(PROTO_LCP, &build_lcp_conf_req(1)[4..]);
    port.write_all(&lcp)?;
    let ipcp_raw = build_ipcp_conf_req(1, LOCAL_IP);
    let ipcp = frame_ppp_fcs(crate::ppp_ipcp::PROTO_IPCP, &ipcp_raw[4..]);
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
                    if let Ok(pkt) = unframe_ppp_fcs(&raw[s..=idx]) {
                        packets.push(pkt);
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
    fn test_fcs16_and_ipv4_tcp_framing() {
        let seg = build_ipv4_tcp_segment(LOCAL_IP, RADIO_IP, 8001, 8002, 1, 0, 0x02, DEFAULT_WINDOW, b"");
        assert_eq!(seg.len(), 40);
        assert_eq!(inet_checksum(&seg[0..20]), 0);

        let hdlc = frame_ipv4_hdlc(&seg);
        let pkt = unframe_ppp_fcs(&hdlc).unwrap();
        assert_eq!(pkt.protocol, PROTO_IPV4);
        assert_eq!(pkt.payload, seg);
    }

    #[test]
    fn test_fcs_corruption_rejected() {
        let mut hdlc = frame_ipv4_hdlc(b"\x45\x00\x00\x14");
        let mid = hdlc.len() / 2;
        hdlc[mid] ^= 0xFF;
        assert!(unframe_ppp_fcs(&hdlc).is_err());
    }

    #[test]
    fn test_ppp_tcp_session_syn_and_chunking() {
        let mut sess = PppTcpSession::new(8001, 8002, 1000);
        let syn_hdlc = sess.build_syn_hdlc();
        let ppp = unframe_ppp_fcs(&syn_hdlc).unwrap();
        let parsed = parse_ipv4_tcp_segment(&ppp.payload).unwrap();
        assert_eq!(parsed.src_port, 8001);
        assert_eq!(parsed.dst_port, 8002);
        assert_eq!(parsed.flags, 0x02);
        assert_eq!(sess.seq, 1001);

        let big_payload = vec![0xABu8; 1100];
        let frames = sess.encode_data_frames(&big_payload);
        assert_eq!(frames.len(), 3); // 512 + 512 + 76
        assert_eq!(sess.seq, 1001 + 1100);
    }
}
