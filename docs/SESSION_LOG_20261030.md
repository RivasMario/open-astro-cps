# Session Log — 2026-10-30 (Windows 11 workstation, Claude Code + Claude-in-Chrome)

Continues `docs/SESSION_LOG_20261029.md`. Goal: have genuine ASTRO 25 Portable CPS
R20.01.00 (on the WinXP VM) drive `tools/virtual_radio.py` over the serial/PPP bridge,
to record how real CPS talks to the radio EEPROM (read/write framing, object layout,
the `0x0107` unlock) and harden the clean-room open-astro implementation against it.

Rig unchanged from 2026-10-29: Proxmox LXC 120 `cps-capture`, dockur WinXP guest COM2 ->
QEMU `-chardev socket` -> socat PTY `/tmp/radiotty` -> `virtual_radio.py --ppp-serial`.
Driven through the noVNC viewer at `http://localhost:8006/` (SSH tunnel) with Claude-in-Chrome.

## Breakthroughs

### 1. Serial RIB AT handshake emulated (mixed-mode + modem wall cleared earlier; this is the dial)
Genuine CPS probes the radio over the serial RIB as a Hayes-style modem **and then dials**:
`AT` / `ATI1` / `ATI2` / `ATI3` / `ATI4` / `AT&V`, then `AT#DATLCL=1`, `AT+IPR=115200`, then
the Windows direct-connection `CLIENT` probe. The replies must match a live-hardware capture
(`captures/at_*.log`): `AT&V` returns a config block carrying `RADIO:`, `MODEL:`, `SERIAL:`,
`WV304:192.168.128.1`, and `ATI2`/`ATI3` return the Host/DSP firmware strings. Implemented in
`SerialPppBridge` (`_modem_reply` + the AT/ATD loop in `serve_forever`). Plain `OK` to `AT&V`
makes CPS fail "Open Radio Failed" (it needs the full config block).

### 2. PPP `CLIENT` -> `CLIENTSERVER` -> LCP/IPCP fixed
The old handler answered `CLIENT` with `CLIENTSERVER` **immediately followed by** a raw LCP
Configure-Request frame. The `0x7E` frame bytes arriving before Windows switched to PPP framing
broke its `CLIENTSERVER` match, so it re-sent `CLIENT` forever. Fix: reply with exactly
`CLIENTSERVER`, then send our own LCP Configure-Request only **after** we ACK the peer's first
LCP Configure-Request (`self._lcp_req_sent` guard). PPP/LCP/IPCP now complete and RCMP flows.

### 3. CPS "supported radio" authorization gate cracked
After the session handshake CPS issues `0x0012` ("Query Authorization UUID"). It rejects the
radio as **"This Radio is not supported by this application" (Status c0001013)** unless the
`0x0012` response is a **genuine/authorized UUID**. Findings:
- The `.cpg` "uuid" header field is a **constant artifact** (`cde9c2bd...` in *every* codeplug) —
  NOT a real per-radio UUID. Using it fails the gate.
- The genuine 407CHT0214 UUID `d105add323864e539b513a65076458d3` (from the live capture
  `captures/cps_20261023_082619_decoded.json`) **passes**, and it passes **even on a 721CLZ0655
  identity** (different serial/model) — so the UUID is validated for authenticity but is **not**
  bound to the serial/model.
- A fabricated UUID (`00112233...`) is **rejected**. So the check is algorithmic/whitelist, like a
  credit-card number: it must be a valid genuine value, but any one genuine value works everywhere.
- Firmware version (Host/DSP via ATI2/ATI3) is **not** the gate (R15 vs R20 made no difference).
- XTS 5000 / model `H18UCF9PW6AN` IS supported (NextGen10.dll references it, and 721 reads once the
  UUID gate passes). So 721 is drivable virtually by borrowing 407's genuine UUID.

New `virtual_radio.py` flags for this: `--host-version`, `--dsp-version`, `--model`,
`--radio-name`, `--uuid`; wired into the compose `virtual-radio` command via `RADIO_HOST_VER`,
`RADIO_DSP_VER`, `RADIO_MODEL`, `RADIO_NAME`, `RADIO_UUID`.

### 4. `0x8100` read-ack length bug fixed (was crashing CPS)
With the gate passed, CPS began a full partition-`0x80` read, then **crashed PatPort.exe**
(null-deref at `0x00000011`) on the small object `0x80/0x0050`. Root cause: our `0x8100` read-ack
put the **requested** length (`0x0370` = 880) in the length field and set `acklen` to the data size
**excluding** the trailing CRC-16. Genuine `0x8100` sets **both** length fields to the returned
payload size **including** the CRC (a 10-byte object reports `0x000c` = 12). The off-by-framing
made CPS mis-parse/over-read the small record and crash. Fixed in the `0x0100` handler:
`acklen = len(sliced) + 2` and the header length field now carries `acklen` (not `reqlen`).
After the fix CPS reads well past `0x0050`.

## Open blockers (next)
- **Multi-instance read `0x80/0x0FA1`**: after the `0x0050` fix the read reaches `0x0FA1` (a
  linked multi-instance object: each instance's data embeds a next-instance pointer `0fa1 000N`,
  inst3 next = `0000` = end). CPS reads inst 0-3, retries inst2, requests inst4, gets the
  "instance not found" reply, then fails **"Read Radio Failed" (Status ecec0031)**. This is a
  fidelity gap in how `virtual_radio` serves multi-instance objects from the `.cpg` (likely the
  next-pointer/instance-count the data advertises vs. what we actually serve). Compare our
  `0x0FA1` responses to a genuine multi-instance read and align the framing/instance termination.
- **`0x0107` unlock not reachable by a plain read**: all genuine captures (`captures/cps_*.json`)
  are pure `0x0100` reads of partition `0x80` with **no** `0x0107`. The unlock only fires on a
  partition-`0x81` write-back (CPS **Write Device**). We have **no** genuine write capture and
  **no** `0x0107` capture yet (the `depot_*` decoded captures contain no RCMP segments). After the
  read path is clean, do a CPS **Write Device** against the fake radio to capture the write framing
  **and** the `0x0107` seed/response — that is the prize for validating flashing + the unlock LFSR.

## Inventory (what is actually stored in the repo)
- Codeplugs: all four + variants in `backups/*.cpg` (205CFR2930, 205CMB2249, 407CHT0214, 721CLZ0655).
- Flashcodes: only **721CLZ0655** = `400008-002000-0` is in the logs; the other three are not stored.
- Genuine authorization UUIDs: only **407CHT0214** = `d105add323864e539b513a65076458d3`
  (from the live capture). The `.cpg` uuid field is a constant artifact, not real. The real UUIDs
  for 721/205x exist only on the physical radios or a future live capture — but are **not needed**
  for virtual capture, since 407's genuine UUID drives any identity.

## Rig operation notes
- Recreating `virtual-radio` (compose `up -d` / `docker restart`) drops the socat PTY; the guest
  QEMU exits on the chardev EOF, so `cps-winxp` must be brought back up (`up -d`) and **XP reboots**
  (the CPS + .NET4 install persists on the `winxp_data` volume).
- To override identity without editing files, export the vars before `up -d`, e.g.
  `export RADIO_UUID=...; CPS_HOST_DIR=/opt/oa/cps docker compose -f docker/docker-compose.yml --profile winxp up -d`.
  Inline `VAR=... docker compose` did NOT reach compose interpolation over SSH; use `export`.
- Known-good default config (committed): 721 identity + borrowed genuine 407 UUID, R15 firmware.

## Read protocol SOLVED + byte-validated (commit e81a048)

Pivoted from live trial-and-error (slow: each attempt reboots XP) to an OFFLINE
diff harness that replays the complete genuine 407CHT0214 capture
(`captures/cps_20261023_082619_decoded.json`, 227 partition-0x80 objects) against
`VirtualRadioServer.process_record` and byte-compares every response. This
surfaced all fidelity bugs at once. Promoted to the regression test
`tests/test_virtual_radio_fidelity.py`.

Two ground-truthed fixes made the full 228-object read complete end-to-end:

1. **Read-ack MTU cap (248 bytes).** Genuine radios cap every `0x8100` read-ack
   record at 248 bytes. Objects larger than the MTU are truncated mid-payload
   while the length field still advertises the full object size; CPS issues no
   offset/continuation read (verified: all 228 genuine reads use offset 0). We
   returned the whole object (up to the requested 880 bytes), overflowing CPS's
   receive buffer and aborting the read ("Read Radio Failed", ecec003x) on the
   first large object. Cap the payload at 248 - 14 = 234 bytes.
2. **Absent-object NAK for instance 0.** A missing object (e.g. `0x80/0x0FA3`)
   must get the 14-byte `0x81` not-found NAK, not a status-0 empty success,
   which also aborted the read.

Result vs genuine: 235/240 records exact; 227/227 codeplug objects byte-perfect.
The only diffs are `0x0047` (last-programmed timestamp) and `0x000F`/`0x0011`
(identity records), which legitimately differ between a saved `.cpg` and a live
radio. The read pipeline is validated against hardware ground truth.

## Write Device / 0x0107 capture still blocked (codeplug-data walls, not protocol)

Reaching CPS **Write Device** (to capture genuine write framing + the `0x0107`
unlock) needs a codeplug CPS R20 fully accepts: reads clean AND loads into the
editor. Both available codeplugs fail for codeplug-specific reasons:

- **407** reads byte-perfect but CPS aborts the parse with repeated warnings
  "Field (Prefix ID / Prefix Emergency) in block ID Disp List Vector is defined
  outside the block max entry size" -> the editor never opens (View menu shows no
  codeplug tree). Because our served bytes are identical to the genuine radio,
  genuine CPS would behave the same: a trait of this VHF codeplug under CPS R20.
- **721** (the XTS5000 flashing target, Host R15) fails mid-read at `0x80/0x0FFD`
  instance 27 with ecec0031, even though its `.cpg` 0x0FFD chain ends cleanly at
  inst26 (null next-pointer, 27 instances stored). Likely an R15-codeplug vs
  R20-CPS validation mismatch. No genuine 721 capture exists to byte-validate.

Next options: obtain/produce a codeplug CPS R20 reads+loads, or repair the 407
ID-Disp-List block, then drive Write Device to capture the write path + 0x0107.

## Rig stability notes

- After restarting `virtual-radio`, cps-winxp's QEMU loses its COM2 chardev.
  Restart cps-winxp ONLY after socat/pty is back (`[ -e /tmp/radiotty ]`), else
  QEMU aborts (exit 134) in a startup race. The LXC has only 4 GB RAM.
- Helper scripts added under `C:\Users\v-mariorivas\wsl-setup\`: `deploy-mtu.sh`
  (push code + restart stack safely), `deploy-721.sh` (switch to 721 defaults),
  `diff_genuine_407.py` (the offline fidelity harness; lives in gitignored
  `scratch/`, promoted to the tracked test above).
