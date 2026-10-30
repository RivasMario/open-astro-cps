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
