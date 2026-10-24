# Handoff — live RCMP read/write (as of 2026-10-23 evening update)

State of the `feat/rcmp-live-read` branch. Read docs/RCMP_WIRE_PROTOCOL.md first
for the wire format; this file is the current status, how-to, and open work.

## What works (verified)

- **Offline `.cpg` decode** (`src/open_astro/parsers/cpg_decode.py`): all zones/
  channels, frequencies, CTCSS tones, real bandsplit from the model letter.
  Validated against NIFOG national frequencies.
- **Offline `.tun` decode** (`tools/tun_decode.py`): soft-pot cal points.
- **Live READ** over RCMP: `RcmpReadClient` (`protocol/rcmp_transport.py`) +
  `rcmp.py` codec. `python -m open_astro.cli rcmp-dump --serial COM7 -o out.json`
  reads the whole codeplug and decodes it; verified byte-equal to the offline
  backup on all three radios (407CHT0214, 205CFR2930, 205CMB2249).
- **Live WRITE** over RCMP: `RcmpWriteClient` (`protocol/rcmp_write.py`) +
  `tools/rcmp_replay_write.py`. Proven: wrote a full codeplug to 205CFR2930
  (183 records, commit, read-back matched). `--edit PART:OBJ:INST:HEX` rebuilds
  one object's write record byte-exact (verified == CPS's own edited write).
- **Channel Patcher & CLI Editor** (`parsers/channel_patch.py` + `open_astro.cli channel-edit`):
  programmatically patches channel name, RX/TX frequencies, CTCSS tones, DPL codes,
  and simplex flags in codeplug objects, generating ready-to-run `--edit` flags for
  `rcmp_replay_write.py`.
- **0103 Prepare Opcode Solved** (`rcmp.build_prepare` + `write_session.py`):
  mapped to `IRcmpBundler::DelIshTypes(nStart, nEnd, nPartitionNum)`:
  `01 03 <part:u8> <start:u16_be> <end:u16_be>`. `CpgWriteAssembler.default_prepare_records()`
  can now synthesize the exact erase framing seen in CPS captures.

## Transport — CRITICAL

Two PPP transports exist:
- **Userspace PPP** (`protocol/ppp_link.py`, `--serial COMx`): our own CLIENT/
  LCP/IPCP/TCP over the serial port. Fine for READS.
  - **2026-10-23: the TCP layer was HARDENED** — outbound data is now ACK-tracked
    and retransmitted on an RTO timeout (bounded retries → clean `PppError`, no
    silent desync), and bytes-in-flight are capped by a send window and the
    radio's advertised receive window, so a write burst can no longer overrun the
    radio (the exact failure that corrupted a codeplug before). Duplicate inbound
    segments are re-ACKed. API (`sendall`/`recv`/`close`) unchanged.
  - Proven OFFLINE only: `tests/test_ppp_link_tcp.py` drives the client against a
    mock radio (fake serial + PPP/IP/TCP peer) with fault injection — recovers
    from dropped data segments and withheld ACKs, delivers every byte exactly
    once, never exceeds the peer window, and raises on a dead radio. 6/6 green.
  - **NOT yet validated on a real radio.** Until the on-hardware check below
    passes, `--serial` writes stay BLOCKED by the replay tool unless `--serial-write`
    is explicitly supplied. Reads over `--serial` are unaffected and already trusted.
- **OS TCP via RAS/pppd** (`--socket`): a real OS socket over the Windows RAS
  dial-up (`OpenAstroRadio`) or Linux pppd. Robust. This is how the 205CFR2930
  recovery succeeded end-to-end. Remains the sanctioned write path **until** the
  hardened `--serial` path is cleared on hardware — the whole point of the
  hardening is to retire this RAS dial-up dance.

### Clearing `--serial` for writes (on-hardware, one time)

Goal: stop needing the RAS dial-up entry. When next at a radio (home setup):
1. Verified `.cpg` backup of the target present in `backups/` (205CFR2930 is the
   designated write-test radio; writing its own normal data is recoverable).
2. Dry-run the replay over `--serial` (no `--confirm`) to confirm records decode.
3. Transmit using the gated opt-in:
   `python tools/rcmp_replay_write.py <capture.pcap> --serial COM7 --serial-write --confirm --expect-serial 205CFR2930`
4. Confirm no `FAIL` on radio display, power-cycle radio, read-back diff.
   Soft-pots (0x82) stay refused throughout.
5. Only after a clean pass: make `--serial` the default write transport and
   retire the RAS setup.

RAS setup (Windows): create a dial-up entry named `OpenAstroRadio` over the
"Motorola 1500 and 2500 Series Radio" modem (phone `0`, no creds), and UNTICK
"use default gateway on remote network" (IPv4 > Advanced) so internet survives.
`tools/ppp_up.ps1` dials it; `tools/ppp_down.ps1` hangs up. The entry can vanish
and need recreating. CPS must be closed (holds COM7). The radio drops PPP after
each session — reset/re-dial between sessions.

## Wire protocol (summary; full detail in RCMP_WIRE_PROTOCOL.md)

- Link: RAS PPP, IPCP negotiates Van Jacobson compression (we decline it in our
  userspace path). `tools/decode_usb_ppp.py` has an EXACT RFC 1144 VJ decoder.
- RCMP over TCP host:8001 -> radio:8002. Record = `<len:u16><payload>`.
- Opcodes: 0100 read, 0101 write, 0103 prepare (DelIshTypes), 0106 session (00 open/01 commit);
  response = request | 0x8000.
- READ req: `0100 <part> <obj:2> <inst:2> <len:2> 0000`. Read-ack body = 12-byte
  echoed header + object payload + 2-byte CRC; strip both.
- WRITE rec: `0101 <part> <obj:2> <inst:2> <len:2> 0000 <len:2> <payload> <crc:2>`,
  len == payload+2, crc = CRC-16-CCITT poly 0x1021 init 0x0000 big-endian over
  payload. `rcmp.build_write` reproduces all 147 captured writes byte-exact.
- PREPARE rec (DelIshTypes): `0103 <part:1> <start:2> <end:2>`.
  - `0103 80 0002 01f4`: partition 0x80, types 2..500
  - `0103 80 0e0b 0fff`: partition 0x80, items 3595..4095
- Write session flow: 0106 open -> 0100 reads -> 0102 -> 0103 prepare x2 ->
  0101 writes -> 0106 01 commit. Partitions: 0x80 plaintext codeplug objects,
  0x81 RC4-encrypted streams. NEVER write 0x82 (tuning/soft-pots) — unrecoverable.

## The write incident (learn from it)

First live write used `--serial` with early unhardened userspace PPP. It desynced,
the radio reset mid-write, left the codeplug inconsistent (radio showed `FAIL 01/02`)
and CPS then refused to write it ("advanced keys"). Recovery: a full write over
`--socket` (OS TCP) of the normal codeplug completed the write + commit and cleared
the FAIL. Soft-pots were never touched (writer refuses 0x82), so it stayed recoverable.
Takeaways: writes go over `--socket` or hardened `--serial-write` only; writing
identical/normal data is recoverable; the radio's own self-test (display) is the truth.

## Safe write procedure

1. Have a verified `.cpg` backup of the target radio.
2. If using RAS: bring up RAS (`ppp_up.ps1`), confirm `192.168.128.1` reachable.
3. `python tools/rcmp_replay_write.py <capture.pcap> --device <N> --socket
   --confirm --expect-serial <SERIAL>` (add `--edit PART:OBJ:INST:HEX` to change objects).
4. Power-cycle radio, confirm no FAIL, read-back verify.

### Partition allowlist (data-backed)

`schema/partition_map.json` and `schema/patport_layout.json` are enforced:
- Partition 0x80: ReadWrite (codeplug)
- Partition 0x81: ReadWriteLocked (RC4 encrypted stream)
- Partition 0x85: ReadWriteLocked
- Partition 0x82: tuning/soft-pots — strictly blocked.
`PartitionPolicy` rejects any write outside observed CPS ranges or targeting 0x82.

## Read-Modify-Write Workflow (CLI)

1. **Dump live codeplug:**
   `python -m open_astro.cli rcmp-dump --serial COM7 -o radio_dump.json`
2. **Edit channel:**
   `python -m open_astro.cli channel-edit backups/205CFR2930.cpg --zone 1 --channel 1 --name "CALL 1" --rx-freq 851.0125 --tx-freq 806.0125`
   This outputs the exact `--edit` flags:
   `--edit 80:0ffd:0:<hex>`
   `--edit 80:0fff:0:<hex>`
3. **Replay write with edits:**
   `python tools/rcmp_replay_write.py <capture.pcap> --socket --confirm --expect-serial 205CFR2930 --edit 80:0ffd:0:<hex> --edit 80:0fff:0:<hex>`

## Next Steps at Home (Hardware Available)

1. **Clear `--serial-write` on hardware:**
   Test writing `205CFR2930` with `--serial COM7 --serial-write --confirm --expect-serial 205CFR2930`.
   Once proven on radio, remove the `--serial-write` restriction.
2. **Verify synthesized prepare framing on hardware:**
   Test `CpgWriteAssembler.build_session(synthesize_prepare=True)` on the radio without needing a pcap.
3. **Commit the capture pcap:**
   From home machine: `git add -f captures/<write_session>.pcap` and commit.
4. **Field coverage expansion:**
   Trunked talkgroup ID linkage to conventional zone scan/monitor list.
