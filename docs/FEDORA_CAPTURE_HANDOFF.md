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
