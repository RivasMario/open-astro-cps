# RCMP wire protocol — ground truth from live CPS captures (2026-10-23)

Decoded from real Motorola CPS <-> XTS 2500 (`407CHT0214`) USB captures, not
from reasoning. Captures and tooling live in `captures/` and `tools/`:

- `tools/capture_cps_write.ps1` — USBPcap whole-bus capture (needs admin).
- `tools/usbpcap_read.py` — native USBPcap pcap parser. **Required** because the
  radio re-enumerates to a new USB address when a WRITE reboots it into
  programming mode, and tshark's `usb.capdata` is empty for a device whose
  descriptors it never saw. The native reader uses the USBPcap `headerLen`
  field to find each bulk payload regardless.
- `tools/decode_usb_ppp.py` — PPP/HDLC unframing, Van Jacobson decompression,
  RCMP record extraction.

Source captures:
- `cps_20261023_082619.pcap` — codeplug Read.
- `cps_20261023_083355.pcap` — tuner Read.
- `cps_20261023_084833.pcap` — differential Write (TAC 16 renamed then restored);
  the write session is USB device 39.

## Transport stack

1. **Link:** Windows RAS/dial-up PPP over the radio's USB CDC-ACM serial. The
   dial handshake is the literal text `CLIENT` (host) -> `CLIENTSERVER` (radio),
   not AT commands.
2. **PPP:** standard LCP then IPCP. IPCP negotiates **Van Jacobson TCP/IP header
   compression**, so bulk frames use PPP protocol `0x002d` (compressed) and
   `0x002f` (uncompressed). These MUST be VJ-decompressed to recover the TCP
   payload. Protocol-Field-Compression is on (IP = single byte `0x21`).
3. **IP/TCP:** host `192.168.128.2`, radio `192.168.128.1`. The RCMP session is
   TCP **host:8001 -> radio:8002**.

## RCMP record framing

A record is `00 <len:1> <payload[len]>`. The payload begins with a 2-byte
opcode. Responses echo the request opcode with the top bit of the first byte
set (`01xx` request -> `81xx` response).

| Opcode | Direction | Meaning |
|--------|-----------|---------|
| `01 00` | host->radio | READ object block |
| `01 01` | host->radio | WRITE object block |
| `01 03` | host->radio | program / erase-prepare (precedes a write burst) |
| `01 06` | host->radio | session open (first record of a session) |
| `81 00` | radio->host | read response / ack |
| `81 01` | radio->host | write ack |
| `81 06` | radio->host | session-open ack |

### READ request
`01 00 <part:1> <obj:2> <inst:2> <readlen:2> 00 00`
- `part` = partition selector (see below).
- `obj` = object id; these match the `.cpg` OLE stream tags (`0x0fff`, `0x0ffd`,
  `0x0ffc`, `0x0ff8`, `0x0fb0`, ...).
- Codeplug reads used `readlen` `0x0370` (880 B); tuner reads `0x03e8` (1000 B).

### WRITE record (VERIFIED byte-exact)
`01 01 <part:1> <obj:2> <inst:2> <len:2> 00 00 <len:2> <payload[len-2]> <crc:2>`
- `len` counts the payload PLUS the 2-byte CRC (`len == payload_len + 2`); the
  13-byte header repeats `len` twice around a `00 00` field.
- `crc` = CRC-16-CCITT, poly 0x1021, **init 0x0000**, non-reflected, big-endian,
  over the payload only. This is the same CRC the offline `.cpg` reader uses.
- `rcmp.build_write(part, obj, payload, inst)` reproduces **all 147** write
  records in the captures byte-for-byte (`tests/test_rcmp.py`), including the
  `0x0fff` channel-name blocks (`CHAN 2` vs the edited `CHAN 2X`), freq blocks,
  and the partition-0x81 encrypted streams.
- Observed partitions written: `0x80` (plaintext codeplug objects) and `0x81`
  (RC4-encrypted streams). Never `0x82` (tuning).

### Write session flow (captured)
`session 0106` -> full codeplug READ (`0100` x N) -> `0102` -> program/erase
PREPARE (`0103` x2: `0103 80 0002 01f4`, `0103 80 0e0b 0fff`) -> WRITE burst
(`0101` x N) -> (commit/finalize: still being confirmed). The full VJ-compressed
write session reassembles into cleanly framed records via the exact RFC 1144
decompressor in `tools/decode_usb_ppp.py`.

## Partition selector (high-level memory map)

The `part` byte selects the radio memory region:

| `part` | Region |
|--------|--------|
| `0x80` | codeplug (all codeplug read/write used this) |
| `0x81` | (seen in codeplug read; unidentified) |
| `0x82` | tuning / soft-pots (the tuner Read used `0x82` objects) |
| `0x85` | (seen in codeplug read; unidentified) |

## Status for the writer

This supplies exactly what `src/open_astro/protocol/flasher.py` flagged as
missing: the real opcode -> bytes mapping (`01 01` write, `01 03` prepare), the
partition map, and that objects/CRC are the same model the offline reader
already handles. Remaining before unlatching `allow_unverified_protocol`:
confirm the `01 03` prepare/commit sequence and the exact write record
sub-framing (the `<inst>`/length repetition and any commit record) against a
second capture, and reproduce the CRC-16 over a write payload.
