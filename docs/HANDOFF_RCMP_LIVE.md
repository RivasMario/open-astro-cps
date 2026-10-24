# Handoff — live RCMP read/write (as of 2026-10-23)

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
    passes, `--serial` writes stay BLOCKED by the replay tool. Reads over
    `--serial` are unaffected and already trusted.
- **OS TCP via RAS/pppd** (`--socket`): a real OS socket over the Windows RAS
  dial-up (`OpenAstroRadio`) or Linux pppd. Robust. This is how the 205CFR2930
  recovery succeeded end-to-end. Remains the sanctioned write path **until** the
  hardened `--serial` path is cleared on hardware — the whole point of the
  hardening is to retire this RAS dial-up dance.

### Clearing `--serial` for writes (on-hardware, one time)

Goal: stop needing the RAS dial-up entry. When next at a radio:
1. Verified `.cpg` backup of the target present in `backups/` (205CFR2930 is the
   designated write-test radio; writing its own normal data is recoverable).
2. Dry-run the replay over `--serial` (no `--confirm`) to confirm records decode.
3. Lift the block: in `tools/rcmp_replay_write.py` the refusal at the
   `args.confirm and args.serial and not args.socket` check (~line 162) is what
   forbids serial writes; the transmit path (~line 177) must build
   `RcmpWriteClient(PppTcpConn(args.serial, dport=args.port), allow_write=True)`
   instead of the OS socket. Gate this behind an explicit `--serial-write` opt-in
   the first time.
4. Write 205CFR2930's own normal codeplug over `--serial --confirm`, power-cycle,
   confirm no `FAIL`, read-back diff. Soft-pots (0x82) stay refused throughout.
5. Only after a clean pass: make `--serial` the default write transport and
   delete the RAS setup from this doc.

RAS setup (Windows): create a dial-up entry named `OpenAstroRadio` over the
"Motorola 1500 and 2500 Series Radio" modem (phone `0`, no creds), and UNTICK
"use default gateway on remote network" (IPv4 > Advanced) so internet survives.
`tools/ppp_up.ps1` dials it; `tools/ppp_down.ps1` hangs up. The entry can vanish
and need recreating. CPS must be closed (holds COM7). The radio drops PPP after
each session — reset/re-dial between sessions.

## Wire protocol (summary; full detail in RCMP_WIRE_PROTOCOL.md)

- Link: RAS PPP, IPCP negotiates Van Jacobson compression (we decline it in our
  userspace path). `tools/decode_usb_ppp.py` has an EXACT RFC 1144 VJ decoder
  (key: low nibble 0x0b/0x0f are reserved SPECIAL_I/D, no delta bytes).
- `tools/usbpcap_read.py`: native USBPcap parser (tshark's usb.capdata is empty
  for a device that enumerates mid-capture — the radio re-enumerates on write).
- RCMP over TCP host:8001 -> radio:8002. Record = `<len:u16><payload>`.
- Opcodes: 0100 read, 0101 write, 0103 prepare, 0106 session (00 open/01 commit);
  response = request | 0x8000.
- READ req: `0100 <part> <obj:2> <inst:2> <len:2> 0000`. Read-ack body = 12-byte
  echoed header + object payload + 2-byte CRC; strip both.
- WRITE rec: `0101 <part> <obj:2> <inst:2> <len:2> 0000 <len:2> <payload> <crc:2>`,
  len == payload+2, crc = CRC-16-CCITT poly 0x1021 init 0x0000 big-endian over
  payload. `rcmp.build_write` reproduces all 147 captured writes byte-exact.
- Write session flow: 0106 open -> 0100 reads -> 0102 -> 0103 prepare x2 ->
  0101 writes -> 0106 01 commit. Partitions: 0x80 plaintext codeplug objects,
  0x81 RC4-encrypted streams. NEVER write 0x82 (tuning/soft-pots) — unrecoverable.

## The write incident (learn from it)

First live write used `--serial` (userspace PPP). It desynced, the radio reset
mid-write, left the codeplug inconsistent (radio showed `FAIL 01/02`) and CPS
then refused to write it ("advanced keys" — the corrupted flashcode showed
advanced features). Recovery: a full write over `--socket` (OS TCP) of the
normal codeplug completed the write + commit and cleared the FAIL. Soft-pots
were never touched (writer refuses 0x82), so it stayed recoverable.
Takeaways: writes go over `--socket` only; writing identical/normal data is
recoverable; the radio's own self-test (display) is the truth, not a partial
read-back.

## Safe write procedure

1. Have a verified `.cpg` backup of the target radio.
2. Bring up RAS (`ppp_up.ps1`), confirm `192.168.128.1` reachable.
3. `python tools/rcmp_replay_write.py <capture.pcap> --device <N> --socket
   --confirm --expect-serial <SERIAL>` (add `--edit PART:OBJ:INST:HEX` to change
   objects). Dry run (omit --confirm) validates first.
4. `ppp_down.ps1`, power-cycle radio, confirm no FAIL, read-back verify.

### Partition allowlist (data-backed, no magic number)

The safe-write guard is no longer just "refuse 0x82". `schema/partition_map.json`
(generated by `tools/derive_partition_map.py` from CPS's own addressing in the
capture sessions) is the authoritative allowlist: CPS reads the codeplug across
partitions 0x80 (objs 10..4095), 0x81 (4100..4102) and 0x85 (4798..4799), and
only ever touches 0x82 (tuning/soft-pots, obj 4217) in a SEPARATE tuner session.
So soft-pots live under a partition the codeplug write never addresses.
`protocol/write_session.PartitionPolicy` loads this and refuses any write to a
non-writable partition (0x82), an unobserved partition, or an object id outside
CPS's observed range for its partition; it degrades to the default allowed set
(still refusing 0x82) if the map file is missing. Regenerate the map when new
captures are added. (The DLL-schema route -- cgIsh10c.dll in the InstallShield
.cab -- stays blocked on the work machine: no unshield there; it only extracts
on Fedora. The capture-derived map is authoritative enough for the write guard.)

UPDATE 2026-10-23: DLL route done (cab unpacked with unshield on Fedora WSL).
PatPort.exe declares exactly 0x80 ReadWrite, 0x81 ReadWriteLocked, 0x85
ReadWriteLocked via `AddPartition`; 0x82 is not in the codeplug layout; block
counts per partition equal the capture's object counts. `schema/patport_layout.json`
(from `tools/patport_partition_layout.py`) is now a second, independent gate in
`PartitionPolicy`, which also exposes `requires_unlock()` for locked partitions.
Block type→item id mapping SOLVED (schema/block_type_map.json, all 169 blocks, exact vs capture),
and the .cpg Strm_0 directory decoded (gives each object's partition, so `from_cpg` needs no
capture). Details: docs/CPS_ISH_SCHEMA.md. Next: per-block field layouts for the decoder.

## Open work (for the next AI)

1. **Full `.cpg` -> write-session assembler.** PARTIALLY DONE 2026-10-23.
   `protocol/write_session.py` (`CpgWriteAssembler`) now builds the ordered 0101
   write records from a source `.cpg`: each `.cpg` stream is self-describing
   (`<tag><inst><len><payload><crc>`, tag == RCMP object id, cross-checked vs the
   live read capture), and `rcmp.build_write` reproduces every object's CRC
   byte-exact. Proven OFFLINE against all 3 backups (`tests/test_write_session.py`,
   the CRC oracle needs no capture). Partition per object comes from
   `part_map_from_capture()` (reads carry the same addressing as writes); 0x82 is
   refused and only an allowed-parts set is emitted. `parsers/cpg_parser.py` got
   an `objects()` accessor for the full decoded objects.
   STILL OPEN: the session FRAMING around the writes — the 0103 prepare records
   (and 0104/0107) whose `0e0b`/`01f4` fields can't be derived without a captured
   write session. `build_session` takes those verbatim and refuses to synthesize
   them (pass `allow_without_prepare=True` for offline assembly only). Finish when
   the write pcap (home PC) is available: supply real prepare records, then
   rebuild a captured session byte-exact from its own `.cpg` source.
2. **Read-modify-write without a reference capture**: use `rcmp-dump` to read the
   live objects, edit, and write back — removes the pcap dependency. The emitter
   half is done (CpgWriteAssembler / WriteObject); still needs the live read +
   the prepare framing from #1.
3. **DPL octal mapping** (cpg_decode DPL_CODES unverified), per-channel modulation
   of CSQ channels, trunked talkgroup linkage, scan-list membership.
4. **UHF/other-band** `.cpg` decode coverage (only VHF/700-800 samples seen).
5. ~~Harden `ppp_link` TCP (windowing/retransmit) for a serial-only write
   path.~~ DONE 2026-10-23 (offline-proven; see Transport section). Remaining:
   the one-time on-hardware validation to clear `--serial` writes and retire the
   RAS dial-up.

## Radios (test fleet)

- 407CHT0214 — Chris's, VHF, 48 ch.
- 205CFR2930 — Mario's "Facebook" radio, 700/800, 2 ch. Used for write testing;
  corrupted then recovered 2026-10-23.
- 205CMB2249 — Mario's, 700/800, Kent PD/King County, 147 ch.
All drop PPP after each session. Backups in `backups/`. Never write partition
0x82 on any of them.

## Status at end of 2026-10-23 session

Done and verified this session (see commits ab62655..c8ecb31):
- Hardened userspace TCP for `--serial` (offline-proven; one on-radio write test
  still needed before it replaces the RAS/`--socket` path).
- `.cpg` -> write records (CpgWriteAssembler), partitions from the `.cpg`
  Strm_0 directory, CPS-derived partition policy enforced in assembler and live
  write client.
- CPS schema: partitions/access rights, all 169 block type -> item id mappings,
  write path architecture, partial field layouts (docs/CPS_ISH_SCHEMA.md).
- Fabricated docs flagged (A25*.dll architecture).

Not built in this session: a `write`/`verify` CLI command and a channel editor.
Pending data: the CPS write-session pcap (home PC; `captures/*.pcap` is
gitignored -- use `git add -f`).
