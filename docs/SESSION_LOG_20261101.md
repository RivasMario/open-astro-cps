# Session Log — 2026-11-01

## Radio 4 (721CLZ0655, XTS 5000) — Depot zone-name fix + Depot flashing-path discovery

### 1. Depot "unable to determine zone channel assignment" — root cause + fix (VERIFIED ON HW)
- Depot refused to read Radio 4 with "unable to determine zone channel assignment."
- Root cause: the master codeplug's `0x000D` zone-name list held a **duplicate zone name** —
  `ZE` twice (raw `5a45` at ISH entries 5 and 6), skipping `ZF`: `ZA ZB ZC ZD ZE ZE ZG ...`.
  Two zones named `ZE` → Depot cannot build a unique Zone/Channel Assignment.
  (Confirmed against raw `0x000D` payload; our decoder was reading it correctly.)
- PatPort.exe string evidence: `"Zone Channel Assignment"`, `"save INVALID Talkgroup in
  Zone/Channel Assignment. The Talkgroup was set..."`, `"...Encountered in Channel Assignment Table"`.
- Fix: `backups/721CLZ0655_OptionA_ADP_zfix.cpg` — renamed the 6th zone `ZE`→`ZF`
  (`CpgWriter.patch_zone_names`, `scratch/fix_zone_zf.py`). Only `0x000D` changed; every other
  `0x80`/`0x81` object byte-identical (ADP secure subsystem untouched).
- Flashed `0x80`-only with `tools/write_codeplug_full.py` (458 writes + `0106 01` acked,
  identity-gated). Power-cycle: **Depot now reads the radio clean.** Committed `c4a1ade`.
- Live read after fix: zones carry unique names (`ZF` present), 194 channels; ADP secure
  subsystem present (`0x0034` master-enable, `0x0037/0x0038` CKR, `0x005D` key table Key 1
  `A1B2C3D4E5`); flashcode `0x81:1006 = 400008-002000-0` (base — Q667 still NOT entitled).
  (Our `CpgDecoder` collapses the full zone list to 13 via a duplicate-channel-table dedup
  heuristic; Depot, the real validator, sees all zones. Decoder dedup is a known limitation.)

### 2. KEY FINDING — Depot does NOT flash over RCMP-over-PPP
Analyzed the 2026-10-24 Depot captures (the "we did it once" flashcode/ADP writes):
`captures/depot_write_20261024_215836.pcap`, `captures/depot_adp_20261024_220429.pcap`,
`captures/depot_flashcode_20261024_214545.pcap`.

- CPS + our tools use **device 5** = RCMP-over-PPP (`0106/0102/0103/0107 8000/0101/0106 01`).
  The Depot captures have **no device 5 at all.**
- Depot programs on **device 13** (OUT, 195–391 KB) paired with **device 35** (IN responses) —
  a separate USB programming interface the radio enumerates for Depot.
- Device-13 bytes:
  * Do NOT decode as RCMP (`rcmp_replay_write.extract_out_records(pcap, 13)` → 0 records).
  * Do NOT parse as PPP (`decode_usb_ppp.parse_ppp_frames` yields noise "protocols"; the
    `0x7e` bytes are incidental, not HDLC flags).
  * Contain NO plaintext — `400008`, `006000`, `002000`, `721CLZ0655`, `H18UCF` all absent →
    scrambled/compressed/encoded.
  * `depot_flashcode_20261024_214545.pcap` device 6 is raw bulk (`7e_out=0`, IN=0) — not useful.

**CORRECTED understanding (do not over-read as "foreign bulk protocol"):**
`ByteData10.dll` imports reveal the transport engine — **`RadioCustStack10.dll`** (122 KB,
same `NetworkRadioProgrammer/System32` folder), exporting `CUSNETppp::PPPConnect/Disconnect/
GetRemoteIPaddr` and `CUSNETdpi::Nopen/Nread/Nwrite/Nclose`, plus WS2_32 + serial
(`SetCommState`/`ReadFile`/`WriteFile`). "VJ" (Van Jacobson) strings present.

So device 13 is **Depot's OWN PPP + TCP stack over the serial/USB port**, almost certainly the
**same RCMP**, just wrapped in Depot's custom async-HDLC PPP framing with VJ (and possibly CCP)
compression. That is why it did not unframe with our standard tooling:
- `extract_out_records`/`decode_usb_ppp` are tuned to the CPS **device 5** Windows-RAS PPP; they
  return 0 for device 13.
- `parse_ppp_frames` on the device-13 bytes yields noise "protocols" because the `0x7e`-delimited
  chunks use a different ACCM / are VJ-compressed, not because the payload is non-PPP.
- tshark `usb.capdata` is empty for device 13 (native `usbpcap_read` has the bytes: 102×1920-byte
  transfers for `depot_adp`, 204×1920 for `depot_write`; entropy ~7.6; no plaintext — consistent
  with VJ/compressed PPP, not an alien format).

The `0x0107` UnlockSecurity may well be inside these frames — we just can't see it until the
custom-PPP framing + VJ are undone. Plain RCMP `0x81` writes still don't persist without the
proper unlock (matches `docs/how_motorola_writes_to_eeprom_and_partitions.md` and R20261027/28);
that is why `flash_radio4_adp.py --no-unlock` reverted `0x81:1006` on power-cycle.

### 3. Next — unframe Depot's custom-PPP (now top priority)
Goal: decode device 13 into RCMP so we can see Depot's flashcode-write sequence (incl. any
`0x0107`) and replicate a persistent flashcode change. Fronts:
1. **RE `RadioCustStack10.dll`** (`NetworkRadioProgrammer/System32/RadioCustStack10.dll`, 122 KB,
   COM in-proc server). Recover `CUSNETppp` async-HDLC framing (ACCM / escape map) and the VJ
   (and any CCP) compression, so the device-13 byte stream can be unframed to RCMP. This is the
   unblock. `ByteData10.dll` (131 KB) wraps it (`CUSNETdpi::Nread/Nwrite`); `NextGen10.dll`
   (240 KB) holds the `0x0107` LFSR scrambler (already solved, `unlock.py`).
2. **Capture bytes:** once unframed, diff `depot_adp` (ADP-only) vs `depot_write` (full) to
   isolate the flashcode-change records; device 35 IN is low-entropy status (`02 00 00 00 00 01`),
   not a crypto challenge.
NOTE: all three transport DLLs are small (122–240 KB) — REA handles them fine, unlike 24 MB
`PatPort.exe` (times out at the 330 s Ghidra import deadline). Copy to local NTFS before opening
(G: Drive mount is not NTFS; REA rejects it).

NOTE: REA on 24 MB `PatPort.exe` times out at the 330 s Ghidra import deadline; the transport
DLLs are smaller — try them first, and/or raise `ghidra.startup_timeout_ms`.

### 4. RadioCustStack10.dll RE — transport fully identified (2026-11-01)
REA (Ghidra 12.1.4) on `RadioCustStack10.dll` (SHA256 `58539e91beba47780a01db38a95535c16cdd4e7b005b4146011836c8a8a6c0c4`,
122880 bytes, PE x86, 382 procs, 236 strings). Registered it in `re_sources.json` as
`radiocuststack10` (NetworkRadioProgrammer/System32/). Copied to local NTFS scratch before opening.

**The transport is the US Software "USNET" embedded TCP/IP stack**, wrapped by Motorola as
`RadioCustStack` (version resource: CompanyName "Motorola", "Copyright 2003-2005",
ProductName "RadioCustomStack"). Evidence strings: `usnet`, `I8250` (16550 UART driver),
`IRNO=3 PORT=0x2f8 CLOCK=115200 BAUD=9600`, `Ethernet`, and imports of `CCommPort`
(`Open`/`Read`/`Write`/`SetComm`) from `RadioSerial10.dll`.

**Link bring-up (from `PPPConnect@0x1000ee10`):**
init USNET -> `CCommPort::Open` -> `PPPSetFlowControl` -> `PPPHandshake` -> `FUN_10001310`
(spawns PPP I/O pump thread at `0x10001420`) -> register socket.

**`PPPHandshake@0x1000ef60` is a plaintext ASCII chat, NOT RFC-PPP/LCP:** it writes
`"CLIENT"` (6 bytes, `s_CLIENT_10018174`) to the comm port, reads back, accumulates up to 12
bytes, and compares the result to `"CLIENTSERVER"` (`s_CLIENTSERVER_10018164`); retries up to 5x.
Related chat strings: `"F21E2BCLIENTSERVER\r"`, `"BCLIENT\r"`, `"BNone\r"`, `"BATA\r"` (modem
`ATA` answer), `"CONNECT"`, `"Kdial-in"/"Kdial-out"/"Kdial-dwn"`. So the radio link is
chat-script + USNET PPP, not Windows RAS PPP.

**Device-13 framing confirmed async-HDLC (RFC1662):** `tools/usbpcap_read.py` on the two write
captures shows `0x7e` suppressed to ~1/2 the random byte rate (depot_adp dev13 332/195840;
depot_write dev13 753/391680; random would be 765 / 1530). Byte-stuffing is active -> the `0x7e`
are genuine frame flags. depot_flashcode has NO device 13 (only dev 6 + 12); depot_adp/write add
device 13 (OUT, HDLC) and depot_write adds device 35 (IN responses, 1872 B). Device 6 (22-44 KB
OUT, **zero `0x7e`**) is a separate non-HDLC endpoint in all three ops. None of the captures
contain the `CLIENT` plaintext -> all three began AFTER link-up (handshake not recorded).

**STRATEGIC REFRAME — transport is not the flashcode secret.** USNET PPP and our Windows-RAS PPP
both deliver identical RCMP to the radio at `192.168.128.1:8002`; the radio side is the same.
Depot's flashcode persistence comes from the RCMP *application* sequence (the `0x0107`
UnlockSecurity handshake + `0x81` write), not from the USNET link layer. Finishing a USNET
HDLC+VJ decoder to read these pcaps is lower-value (and the pcaps lack the handshake and the
dev-13 IN side) than reversing the `0x0107` unlock state machine in `NextGen10.dll` (240 KB;
already yielded the LFSR scrambler -> `unlock.py`; `unlock_session.py` `WIRE_PROFILE_CONFIRMED=False`
is the open gap). NEXT: RE NextGen10's `0x0107` session sequencing, not the USNET VJ decoder.
(VJ compression: USNET supports it, but no `VJ` literal was observed in THIS DLL's string
inventory this pass — do not overclaim; device-13 entropy ~7.6 is consistent with either VJ/CCP
or the codeplug's own RC4.)

### 5. NextGen10.dll flashing/unlock deep dive (2026-11-01)
Full recursive RE of the flash path (REA/Ghidra 12.1.4). `NextGen10.dll` SHA256
`99fa3efbf1b7aa58722558841336c68035b9c4d562bf656f8f180d4f60348746`, 245760 bytes, 1814 procs.
Authoritative write-up appended to `docs/re/RE_0107_UNLOCKSECURITY.md` ("Third re-confirmation +
full flash-path map"). Summary:
- LFSR unlock scrambler `FUN_1000fd89` (seed `0x51E88D21`, tap bit 9, 32-byte block) and the
  `CRcmpBundler::UnlockSecurity` sequence `FUN_1000cce7` (build `+0x60` -> `FUN_1000fd89` -> send
  `+0x5c` -> commit `+0xb0`; errors `0x97/0x98/0x99`) re-confirmed verbatim -- 3rd independent pass.
  Matches `src/open_astro/protocol/unlock.py` exactly. Second variant `FUN_100133df` reads back
  `this+0x28..0x2a` after unlock.
- RCMP wire: `CRcmpProtocol::BundleTCP` (`FUN_100187b6`) = 2-byte BE length prefix;
  `CRcmpProtocol::SendRequest` (`FUN_10018123`) = `01 01` records, progress counter +=
  `payload[7]<<8|payload[8]`, <=`0x410` chunks, transport modes `{4,8,9,10,0xc,0xd}` use TCP framing
  (`0xd`=OTAP).
- `CRcmpBundler::LoadServer` (`FUN_1000b2ad`) `CoCreateInstance`s the RCMP-core COM servers ->
  **opcode bytes live in a separate COM DLL; static call graph ends at this COM boundary.**
- `ReadWriteRadioSerialNumber` (`FUN_1000ace8`): serial/model/flashcode = ISH `0x81` items via a
  shared single-instance R/W primitive (`FUN_1000b8b5`). `EnterWriteMode` (`FUN_10016776`) = OTAP
  entry (reply[2]=status; "OTAP Enabled"/"Busy"/"Not Responding").
- Capture check: NO held capture has a decodable `0107` -- `cps_20261023_*` OUT = `0106/0103/0100`
  only (read sessions); Depot caps = device-13 USNET. GAP = the unlock wire bytes
  (`WIRE_PROFILE_CONFIRMED=False`). NEXT: capture a live CPS `0x81` write over device 5, decode with
  `tools/decode_usb_ppp.py`, lift the `0107` request + seed + response. Do NOT transmit a guessed
  unlock frame.
