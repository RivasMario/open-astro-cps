# Docker & Virtual Radio Capture Rig (`open-astro-cps`)

Run Motorola ASTRO 25 CPS / Depot inside an isolated Docker/Podman container while [`tools/virtual_radio.py`](../tools/virtual_radio.py) impersonates one of the fleet radios (`721CLZ0655` XTS 5000 or `205CFR2930` XTS 2500) on TCP `:8002` and Serial PPP (`COM1`) and captures every RCMP request and response packet.

---

## Architecture & Two Container Variants

Both container variants are defined in [`docker/docker-compose.yml`](docker-compose.yml) using Docker Compose profiles:

| Profile | Service | How It Works | Web UI |
|---|---|---|---|
| *(default)* | `virtual-radio` | Standalone Python RCMP + Serial PPP simulator on `192.168.128.1:8002` (`127.0.0.1:8002`) with live `.jsonl` and `.pcap` recording | CLI |
| `--profile wine` | `cps-wine` | `i386/debian:bookworm-slim` (`linux/386`) with clean 32-bit `WINEARCH=win32` prefix, auto-registered CPS COM DLLs (`regsvr32`), `socat` virtual `COM1` PPP bridge, `tcpdump`, and `virtual_radio.py` in the same network namespace | `http://127.0.0.1:6080/vnc.html` |
| `--profile winxp` | `cps-winxp` + `virtual-radio` | `dockurr/windows` 32-bit Windows XP KVM container on `192.168.128.2` connected directly to `virtual-radio` on `192.168.128.1:8002` | `http://127.0.0.1:8006` |

---

## Quick Start (Fedora Laptop or Linux/Windows Host)

### 1. Variant A: 32-bit Wine + noVNC + Virtual Radio (No KVM needed)
Point `CPS_HOST_DIR` at your extracted ASTRO 25 CPS directory (e.g., `~/re/openastro` on Fedora):

```bash
CPS_HOST_DIR=~/re/openastro \
RADIO_CODEPLUG=/workspace/backups/721CLZ0655.cpg \
RADIO_SERIAL=721CLZ0655 \
RADIO_FLASHCODE=400008-002000-0 \
docker compose -f docker/docker-compose.yml --profile wine up --build
```

1. Open **`http://127.0.0.1:6080/vnc.html`** in your browser.
2. In ASTRO 25 CPS / Depot, click **Read Device**, **Write Device**, or **Flashport -> Upgrade**.
3. Every packet sent by CPS and answered by the virtual radio is logged live to:
   - `captures/rcmp_trace_<timestamp>.jsonl` (parsed RCMP opcodes + raw hex)
   - `captures/docker_tcp_<timestamp>.pcap` (raw `tcpdump` capture on port `8002`)
   - `captures/rcmp_synth_<timestamp>.pcap` (synthetic IPv4/TCP PCAP from `virtual_radio.py`)

### 2. Variant B: 32-bit Windows XP VM in Docker + Virtual Radio Sidecar
If a CPS/Depot dialog requires the native Windows kernel or full ActiveX/MFC installer:

```bash
CPS_HOST_DIR=~/re/openastro \
docker compose -f docker/docker-compose.yml --profile winxp up
```

1. Open **`http://127.0.0.1:8006`** in your browser (or RDP to `127.0.0.1:3389`).
2. Your `CPS_HOST_DIR` is mounted inside Windows XP at `\\host.lan\Data`.
3. The Windows XP container lives at `192.168.128.2` and reaches the `virtual-radio` container directly at **`192.168.128.1:8002`**.

### 3. Standalone Virtual Radio Simulator (No Docker required)
You can also run the upgraded simulator directly on Fedora or Windows:

```bash
python tools/virtual_radio.py backups/721CLZ0655.cpg \
  --host 127.0.0.1 \
  --port 8002 \
  --serial 721CLZ0655 \
  --flashcode 400008-002000-0 \
  --lock-security \
  --challenge-security \
  --capture-jsonl captures/live_trace.jsonl \
  --capture-pcap captures/live_trace.pcap \
  --verbose
```

To also answer Windows RAS / CPS serial `CLIENT` -> `CLIENTSERVER` PPP dial-up on a virtual serial port or PTY, add `--ppp-serial /dev/pts/X` (or `--ppp-serial COM8`).
