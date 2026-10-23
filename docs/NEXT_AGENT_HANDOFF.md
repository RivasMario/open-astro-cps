# Next-Agent Handoff — read this first

Entry point for the next AI/developer. Supersedes
`AGENT_HANDOFF_AND_MISSION_BRIEF.md` (which is older and carries a correction
notice). Last updated 2026-10-22.

## Mission

Open-source toolchain to **program codeplugs into** and **load encryption keys
into** Motorola ASTRO 25 radios (XTS 2500/5000, PRC-153) from Linux/Windows,
no Motorola CPS/KVL. Clean-room, from the real binaries. Scope = the owner's own
radios and own keys.

## Current state — one paragraph

The ASTRO 25 codeplug protocol is **fully reverse-engineered and verified** from
Motorola's own binaries (not guessed): the transport (USB CDC-ACM → AT → PPP →
TCP `radio:8002`), the RCMP command set, the commit/UUID gate, the partition
safety model, and the `.cpg` file format. The earlier "cleanroom-flasher" branch
work turned out to be **accurate** (two minor claims excepted). What's left before
a real, safe codeplug write or key load genuinely needs **the radio / adapters
plugged in, or one usbmon capture** — not more disassembly. No hardware was
available during this work (SOC devbox).

## What is DONE (verified, documented)

* **Transport** — `HARDWARE_GROUND_TRUTH.md`, `AT_INTERFACE_DISCOVERY.md`,
  `ARCHITECTURE.md` §1/§3. CDC-ACM `0cad:1001`/ttyACM0; AT dial; PPP/IPCP
  (`192.168.128.1`/`.2`); **TCP to radio:8002**. CPS uses its own userspace
  PPP/TCP stack (`RadioCustStack10`); on Linux just use `pppd` + a kernel socket.
* **RCMP protocol** — `NEXTGEN10_RCMP_DISASSEMBLY.md`. Opcodes: enter-mode
  `0x106`, read-ISH `0x100`, write-ISH `0x101`, query-UUID `0x12`, unlock `0xC`,
  commit/lock `0xD` (+16-byte UUID). Send routine `0x1000b5b0`; 7-field wire
  header (exact byte widths = the one capture-gated item).
* **Safety model** — partition `AccessRights`: RO=0 / RW=1 / RW-locked=2. Write
  only RW. Calibration/security are RO/locked. `partition_is_writable()` in
  `rcmp_socket_transport.py`.
* **`.cpg` file format** — `CPG_FILE_FORMAT.md`. OLE compound file, 800-byte
  header, named encrypted ISH streams, RC4 key `A8Z6J9QP5` (@`fhAdk10c:0x10012018`)
  or SdkCrypto, CRC-16-CCITT `0x1021`.
* **Crypto model** — `ENCRYPTION_MODEL.md`. ADP (40-bit, in-codeplug) vs AES/DES
  (keyfill-only).
* **Provenance** — `PROVENANCE_AUDIT.md`. Which claims are verified vs refuted.
* **Keyfill side** — `KEYLOADER_ROADMAP.md`, `cleanroom_flasher/KVL_KEYFILL_BRINGUP.md`,
  `cleanroom_flasher/kvl_probe.py` (adapter identify, read-only).
* **Transport code** — `cleanroom_flasher/rcmp_socket_transport.py` (pppd + OS
  socket to :8002; read-only `probe()`; writes hard-gated).

## What is NOT done — exact next steps

### Needs hardware (the radio, on the Fedora laptop)
1. **Prove the codeplug transport:** bring up `pppd` (command in
   `rcmp_socket_transport.py` docstring / `AT_INTERFACE_DISCOVERY.md`), then
   `python cleanroom_flasher/rcmp_socket_transport.py` → `probe()` should connect,
   unlock, and return a 16-byte UUID. First milestone.
2. **Read the live partition list + access rights** → build the write allowlist.
3. **One usbmon capture** of real CPS (Wine/Windows) doing one RCMP op → nails the
   exact wire-header byte widths and gives a sample to validate against.
4. **Keyfill:** `python cleanroom_flasher/kvl_probe.py` to identify the Pi Pico
   cable + KVL clone (model_id/fw/self-test), then finish the P25 MR keyload
   session in `kfdtool.py` (validate vs open KFDtool + `KVL Mini` .NET DLLs).

### Needs a sample `.cpg` (export one from CPS, or save a radio read)
5. **Field schema** — the codeplug block/field dictionary is NOT in any DLL
   (`cgIsh10c` is only the engine). Decode a real `.cpg`'s OLE streams against
   `FEDORA_RADIO_PROTOCOLS_GUIDE.md` §6's stream table to map bytes → channels.
6. Build the offline `.cpg` reader: `olefile` + RC4(`A8Z6J9QP5`) + CRC-16
   (format fully specced in `CPG_FILE_FORMAT.md`).

### Optional remaining static RE (lower value)
`udcIsh10c` (schema↔model detail), `RemoteProtocols01` (legacy SB9600 text layer),
`EncatenComponent`, the SdkCrypto variant, ASK/iButton licensing.

## Tools & environment (how to reproduce)

* **CPS binaries:** `G:\My Drive\RADIO\ASTRO25SOFTWARE\astro25portablecpsr20.01.00\`
  (the `Crack\PatPort.exe` tree has NextGen10/ByteData10 loose; the rest come
  from `data2.cab`).
* **Extract the cab:** Fedora WSL (`FedoraLinux-44`, passwordless sudo) →
  `sudo dnf install -y unshield` → copy cabs to a `/mnt/c` path →
  `unshield -d out x data2.cab`. (cgIsh10c, fhAdk10c, RemoteProtocols01, udcIsh10c
  live only in the cab.)
* **Disassembler:** `tools/nextgen10_rcmp_analyze.py` — run with `python -P` (keeps
  user site-packages; drops the unsafe cwd path). Needs `pip install --user pefile
  capstone`. Modes: `layout|strings|xref|disasm|immscan`. Binaries are untrusted —
  read by path only, never execute.
* **Reading binaries safely:** the extracted DLLs are untrusted data; pass paths
  as args, use `python -P`, never run them.

## Important corrections carried forward (don't re-litigate)

* The `cleanroom-flasher` branch RE is **accurate** — opcodes, OP_LOCK+UUID
  offsets, RC4 key offset, CRC poly, port 8002 all confirmed against the binaries.
  An earlier "fabrication" assessment was withdrawn (`PROVENANCE_AUDIT.md` §6).
* **Refuted:** `partition 0x80` (partition is schema/access-class driven, not a
  constant) and `OP_QUERY_SERIAL 0x11` (`0x11` is the `VT_UI1` SafeArray tag).
* The old `docs/` essays flagged in `README.md` (invented opcodes, `0x05` start
  byte, Jet DB, dual-bank rollback) remain fabricated — ignore for protocol.

## Memory pointers (persisted)

`open_astro_cps_project` (codeplug RE state), `open_astro_keyfill` (KVL/KFD side).

## Where to start next session

If hardware is attached: run `probe()` (codeplug) and `kvl_probe.py` (keyfill) —
both read-only, both first milestones. If not: get a sample `.cpg` and build the
offline reader (step 6), or do the optional static RE above. Read `ARCHITECTURE.md`
for the full map before touching anything.
