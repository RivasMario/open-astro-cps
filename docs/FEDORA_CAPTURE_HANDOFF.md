# Handoff: real-CPS flashcode-write capture on the x86 Fedora laptop

**Goal:** run the genuine Motorola ASTRO 25 CPS against a fake radio
(`tools/virtual_radio.py`), let CPS write a flashcode and read the codeplug,
capture the RCMP traffic, and prove our clean-room handshake + codeplug decode
against that ground truth.

## Why not on the Windows workstation
That box is **ARM64** *and is itself a VM*. Every container route was exhausted
there (recorded so nobody retries):

- CPS is 32-bit **x86**; ARM64 Windows can't host the installed legacy suite.
- WSL2 `linux/386` + Wine: podman/crun fails `capget: invalid argument` on the
  WSL kernel; binfmt rejects the `F` flag.
- Docker Desktop: backend needs nested virtualization the VM host doesn't expose.

The Fedora laptop is **x86_64**, so `linux/386` runs natively (no emulation, no
kernel hacks) — the only path with real success odds.

## Prereqs on Fedora
- `x86_64` Linux, `docker` + `docker compose` v2 (or adapt to `podman compose`).
- The extracted ASTRO25 CPS tree (the same zip:
  `ASTRO25SOFTWARE-...zip`). Note the dir that contains `PatPort.exe` and
  `NetworkRadioProgrammer/System32/NextGenNon98/NextGen10.dll` — that path (its
  root `.../astro25portablecpsr20.01.00`) is `CPS_HOST_DIR`.
- This repo cloned; `pip install olefile` for the validators.

## Run it
```bash
cd open-astro-cps
export CPS_HOST_DIR=~/re/ASTRO25SOFTWARE/astro25portablecpsr20.01.00
export RADIO_SERIAL=721CLZ0655
export RADIO_FLASHCODE=400008-002000-0
export RADIO_CODEPLUG=/workspace/backups/721CLZ0655.cpg   # container path
scripts/fedora-capture-rig.sh
```
Then:
1. Open <http://127.0.0.1:6080/vnc.html>.
2. In CPS (PatPort): connect, **Write Device** / **Flashport → Upgrade**, then
   **Read Device**. The virtual radio supplies identity + answers the `0x0107`
   seed→response, so CPS believes a radio is attached.
3. Back in the terminal, press ENTER. The script finds the new
   `captures/rcmp_trace_*.jsonl` and runs both validators.

Stop the rig: `docker compose -f docker/docker-compose.yml --profile wine down`.

## Acceptance (what "understood" means)
- `verify_handshake.py` → **PASS**: the real CPS/NextGen10.dll response equals
  `unlock_response(captured_seed)`. This is the live acceptance vector the RE
  notes (`docs/re/RE_0107_UNLOCKSECURITY.md`, open item #3) were missing — add
  the captured seed/response pair to `tests/test_unlock.py` as a golden vector.
- `verify_codeplug.py` → **PASS**: every captured Partition `0x80` object (CRC
  valid) matches our `CpgParser` decode of the reference `.cpg`.

## If no capture appears
`docker compose -f docker/docker-compose.yml --profile wine logs` — check that
`virtual_radio.py` bound `:8002` and CPS reached `192.168.128.1`. Wine under a
real x86 host is far more reliable than the emulated attempts, but a legacy
MFC/ActiveX GUI can still need `winetricks` nudges (vcrun, mfc42, msxml3).

## Alternative: real radio, no container
On an x86 **Windows** box with CPS installed and a bench radio on COM:
`tools/capture_cps_write.ps1` (USBPcap) + `tools/decode_usb_ppp.py` → same
`verify_*` step. Truest ground truth (real seed + real codeplug).

## Homelab Proxmox runbook (recommended host)

PVE (`proxmox` / tailnet `100.70.69.28`, i7-7700T, **x86_64 + KVM**) runs the
wine rig native — no emulation. Drive it from a machine whose network passes
Tailscale (home / `fedora-desktop`); the SOC network blocks the tailnet data
path, so this cannot run from the Windows workstation there.

CPS tree lives on the Windows box at `~/re/ASTRO25SOFTWARE/...`; move it to PVE
via WSL Fedora (which has the files at `/mnt/c/...` and the tailnet).

### 1. Stage files onto the PVE host (from WSL Fedora, at home)
```bash
RE=/mnt/c/Users/v-mariorivas/re/ASTRO25SOFTWARE/astro25portablecpsr20.01.00
rsync -a --info=progress2 "$RE/" proxmox:/root/openastro/cps/           # ~1.9 GB
# repo (or: git clone on PVE)
rsync -a /mnt/c/Users/v-mariorivas/open-astro-cps/ proxmox:/root/openastro/repo/ \
    --exclude rust/open_astro_cli/target --exclude .git
```

### 2. Create a Docker-capable Debian LXC on PVE (`ssh proxmox`)
```bash
# Debian 13 template (adjust storage names to your node):
pveam update && pveam download local debian-13-standard_*_amd64.tar.zst
pct create 120 local:vztmpl/debian-13-standard_*_amd64.tar.zst \
    --hostname cps-capture --cores 4 --memory 4096 --rootfs local-lvm:16 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp --features nesting=1,keyctl=1 --unprivileged 0
# bind-mount the staged dir into the container:
pct set 120 -mp0 /root/openastro,mp=/opt/oa
pct start 120
```

### 3. Bootstrap + run inside the container
```bash
pct exec 120 -- bash -lc '
  export OA_REPO=/opt/oa/repo
  export CPS_HOST_DIR=/opt/oa/cps
  export RADIO_SERIAL=721CLZ0655 RADIO_FLASHCODE=400008-002000-0
  export RADIO_CODEPLUG=/workspace/backups/721CLZ0655.cpg
  bash $OA_REPO/scripts/capture-vm-bootstrap.sh
'
```
The rig builds the `linux/386` wine image **native** (fast), starts
`virtual_radio.py` as the fake radio, and waits.

### 4. View CPS and drive the write
noVNC binds `127.0.0.1:6080` inside the container. Tunnel it out:
```bash
CTIP=$(ssh proxmox "pct exec 120 -- hostname -I | awk '{print \$1}'")
ssh -L 6080:$CTIP:6080 proxmox      # keep open
```
Browse <http://127.0.0.1:6080/vnc.html>, run **Write Device** then **Read
Device** in CPS, return to the rig terminal, press ENTER → `verify_handshake.py`
+ `verify_codeplug.py` run on the new capture.

### 5. Retrieve captures
```bash
rsync -a proxmox:/root/openastro/repo/captures/ ./captures-from-pve/
```
A `verify_handshake.py` PASS here is the live acceptance vector — add the
captured seed/response to `tests/test_unlock.py`.

> Alternative: the `winxp` compose profile (`--profile winxp`) runs a real
> WinXP VM via `/dev/kvm` (PVE has it) if Wine mishandles the MFC/ActiveX GUI.
> Needs `/dev/kvm` + `/dev/net/tun` passed into the container/VM.

---

## Homelab run log (2026-10-29/30) — Wine rig stood up on Proxmox LXC 120

Ran the rig on the homelab Proxmox node (`pve`) instead of the Fedora laptop,
because the Windows workstation is ARM64. Everything below is reproducible.

### Infrastructure provisioned
- **LXC 120 `cps-capture`** on `pve`: Debian 13, x86_64, 4 cores / 4 GiB /
  24 GiB, `features=nesting=1,keyctl=1`, DHCP `192.168.0.231`. Reached from the
  Windows box's WSL over the Tailscale SOCKS5 proxy (`127.0.0.1:1055`); SSH alias
  `cpslxc` (ProxyCommand `ncat --proxy 127.0.0.1:1055 --proxy-type socks5`).
- Installed: `docker.io` 26.1.5, compose v2 plugin, **buildx 0.38.1** (Debian's
  bundled 0.13.1 is too old for `compose build` — it needs ≥ 0.17).
- Repo synced to `/opt/oa/repo`; CPS program files (PatPort + 17 DLLs +
  `RemoteRadioProg.exe`, 52 MB, Support/ installers excluded) to `/opt/oa/cps`.

Bring-up: `CPS_HOST_DIR=/opt/oa/cps RADIO_CODEPLUG=/workspace/backups/721CLZ0655.cpg`
`RADIO_SERIAL=721CLZ0655 RADIO_FLASHCODE=400008-002000-0`
`docker compose -f docker/docker-compose.yml --profile wine up --build -d cps-wine`.

### Dockerfile fixes needed to get the CPS GUI running under Wine
All now baked into `docker/Dockerfile.wine-cps`:
1. **`winetricks` is in Debian `contrib`** — the i386 base only enables `main`,
   so `contrib non-free` is added to the apt sources before install.
2. **Dropped `wine32`** (that package name only exists on amd64-multiarch; on an
   i386 base plain `wine` is the 32-bit build).
3. **Wine Mono must be installed** — `RemoteRadioProg.exe` is a .NET app that
   imports `mscoree.dll`; without Mono it fails `status c0000135` (DLL not
   found). The `wine-mono-8.0.0-x86.msi` is installed at build. Mono/Gecko
   auto-install is suppressed during `wineboot --init` (`WINEDLLOVERRIDES=
   "mscoree=;mshtml="`) so init never blocks on a download prompt; runtime keeps
   only `mshtml=` disabled.
4. **Fonts** — the .NET GDI+ UI dies `System.ArgumentException: FontFamilyNotFound`
   with no fonts. `winetricks corefonts tahoma` + `fonts-liberation`/`-dejavu`.
5. **Entrypoint launches the wrong exe** — fixed to run `RemoteRadioProg.exe`
   (the actual CPS GUI). `Crack/PatPort.exe` is only the parallel-port/dongle
   loader and exits immediately.

### The wall: `PortMgrWrapper.dll` is a mixed-mode assembly
With Mono + fonts, the CPS GUI launches and renders. It then throws:

> **Network Radio Programmer Exception** — "Exception while getting computer
> ports. `PortMgrWrapper.dll` assembly:`<unknown assembly>` type:`<unknown type>`
> member:(null)"

`PortMgrWrapper.dll` is a **mixed-mode (C++/CLI, IJW) assembly**, and **Wine Mono
cannot execute mixed-mode assemblies** — a fundamental Mono limitation, not a
config miss. So under Mono the port list is always empty: CPS can never select
the virtual radio's COM1/network port, so no Read/Write Device, so no live
`0x0107` handshake capture. The GUI runs; the port layer does not.

### Two forward paths to clear the wall (pick up here)
1. **Real .NET Framework under Wine** — `winetricks -q dotnet48` and override
   `mscoree` to the Microsoft CLR instead of Mono. Real .NET *can* run mixed-mode
   assemblies. Same fast container, no new infra. Risk: `dotnet48` on `wine32` is
   finicky (often wants `win7` mode) and may not install cleanly.
2. **Real Windows VM** — pass `/dev/kvm` into LXC 120 (nesting already on) and
   run the `winxp` profile (`dockur/windows`): real Windows + real .NET Framework
   makes `PortMgrWrapper.dll` load natively. Highest certainty; largest setup
   (Windows ISO, VM install, mount `/cps`, wire the VM NIC to `virtual_radio.py`).

The fake radio side is fully proven: `virtual_radio.py` serves the 721CLZ0655
codeplug (461 objects, 32-byte challenge security) on `0.0.0.0:8002` and records
to `captures/rcmp_trace_*.jsonl`. Only the vendor-side port enumeration is
blocked. Once CPS connects, `verify_handshake.py` + `verify_codeplug.py` validate
the capture; a `verify_handshake.py` PASS is the live acceptance vector for the
`0x0107` seed/response in `tests/test_unlock.py`.
