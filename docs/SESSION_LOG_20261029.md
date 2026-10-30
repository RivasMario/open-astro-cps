# Session Log — 2026-10-29 (Windows 11 workstation, Claude Code + Claude-in-Chrome)

Goal: capture the genuine Motorola CPS `0x0107` unlock handshake + `0x80` codeplug read
against `tools/virtual_radio.py`, to add a golden seed/response vector to
`tests/test_unlock.py` (closes RE_0107 open item #3).

Rig host: Proxmox LXC 120 `cps-capture` (Debian 13, `192.168.128.231`), reached from the
Windows box via WSL `FedoraLinux-44` Tailscale SOCKS5 proxy. Driven through the dockur
noVNC viewer at `http://localhost:8006/` (SSH tunnel) with Claude-in-Chrome.

## Done

### 1. Wine path abandoned — real WinXP VM instead
- `docker/Dockerfile.wine-cps` (committed `5c7cc25`) runs the CPS GUI, but `PortMgrWrapper.dll`
  is a mixed-mode (C++/CLI) assembly that **Wine Mono cannot execute** — port list always empty.
- Switched to the `winxp` compose profile (`dockurr/windows`, Windows XP VM via `/dev/kvm` in LXC 120).

### 2. Genuine CPS installed and running natively on WinXP
- Installed **ASTRO 25 Portable CPS R20.01.00** from the staged installer (`\\host.lan\Data`),
  skipping ARS and AKA (not needed for a read), plus Adobe Flash (intro video) and the Tutorials disk.
- Installed **.NET Framework 4** (`Support\dotnet4full.exe`) — the setup's bundled .NET4 failed; the
  standalone full installer succeeded. Required for the .NET-based port/comms layer.
- **Mixed-mode wall cleared:** CPS launches, `PortMgrWrapper.dll` loads, and `File -> Read Device`
  opens a **"Select Port"** dialog (COM1 / COM2 / USB). So this CPS reads a portable **only over a
  serial COM port** (RAS/PPP `CLIENT` -> RCMP over TCP :8002), never raw IP.

### 3. Serial PPP bridge (guest COM2 -> virtual_radio)
- `docker/docker-compose.yml` winxp profile now wires a serial link:
  - `cps-winxp` `ARGUMENTS`: a QEMU `-chardev socket` (guest **COM2**) that connects OUT to
    `192.168.128.1:7000`. Outbound is required because dockur's `QEMU_DNAT` iptables chain forwards
    all inbound container ports to the guest (only 5900/8006 excepted), so the radio side must listen.
  - `virtual-radio`: `socat` presents a PTY (`/tmp/radiotty`) and listens on `:7000`; the radio runs
    with `--ppp-serial /tmp/radiotty` so `SerialPppBridge` answers the dial.
- Verified end to end: serial TCP link ESTABLISHED (guest COM2 <-> socat PTY <-> SerialPppBridge),
  and CPS enumerates **COM2** in Select Port.

## Blocker diagnosed + fix applied (verify next session)
- CPS `Read Device` over COM2 runs NextGen10, then fails: **"NextGen10 — Radio Failed to Acknowledge.
  Error Context: 24, Status: c0000386"**.
- Root cause found via the `socat -v -x` byte trace (`/tmp/socat.log`): CPS/Windows RAS writes
  **`41 54 26 56 0d` = `AT&V\r`** repeatedly — **Hayes modem AT commands**. Genuine CPS dials the
  radio over the serial RIB **as a modem** (AT init -> expects `OK`, then `ATD...` -> expects
  `CONNECT`, then PPP), NOT the Windows Direct-Connection `CLIENT` null-modem handshake that
  `SerialPppBridge` implemented. With no `OK`, RAS never progressed, so zero PPP bytes and no capture.
- **Fix applied** in `tools/virtual_radio.py` `SerialPppBridge.serve_forever`: added Hayes modem
  emulation — answer `AT*` with `OK`, `ATD*` with `CONNECT 115200` then kick the radio LCP
  Configure-Request, before the existing CLIENT/PPP/HDLC handling. Guarded to only run while no PPP
  `FLAG` (0x7E) / `CLIENT` is in the buffer so real link data is never eaten.
- **Not yet verified.** Next session: stage the updated `tools/virtual_radio.py` on the LXC
  (`/opt/oa/repo`), restart `openastro-virtual-radio` (re-check the serial link ESTABLISHED; if the
  guest QEMU exited on the socat drop, `up -d` restarts cps-winxp too — XP reboots, install persists),
  then CPS `Read Device` -> COM2 and watch for `Serial modem: ... -> OK/CONNECT` then
  `received ...`/RCMP in the virtual-radio log and a growing `captures/virtual_radio_trace.jsonl`.
- If AT init now completes but PPP still stalls, capture the next `socat.log` bytes (the ATD dial
  string + any post-CONNECT bytes) to see whether Windows expects `CLIENT` after `CONNECT` or goes
  straight to LCP.

## Rig quick reference
- LXC: `ssh cpslxc` (via WSL FedoraLinux-44). Compose at `/opt/oa/repo/docker/docker-compose.yml`,
  installer share `/opt/oa/cps` (= `CPS_HOST_DIR`).
- Recreate: `cd /opt/oa/repo && CPS_HOST_DIR=/opt/oa/cps docker compose -f docker/docker-compose.yml --profile winxp up -d`.
  Recreating `cps-winxp` reboots XP; the CPS + .NET4 install persists on the `winxp_data` volume.
- Serial link check: look for TCP port `0x1B58` (=7000) ESTABLISHED in both containers' `/proc/net/tcp`.
