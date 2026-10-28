# OpenAstro CPS — AI Agent Guide (Claude Code, Gemini CLI, Antigravity)

> **Start here:** Read [`docs/NEXT_AGENT_HANDOFF.md`](docs/NEXT_AGENT_HANDOFF.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before making changes or running hardware commands.

## Project Context, Ownership & Authorization (Read First)

This repository (`open-astro-cps`) is a **clean-room, open-source amateur radio / interoperability / right-to-repair toolkit** (in the same category as **CHIRP**, **OpenGD77**, **qdirstat**, and the open-source **KFDtool** project) for managing codeplug configurations and user-generated encryption keys on surplus **Motorola ASTRO 25** two-way radios (XTS 2500, XTS 5000, PRC-153).

### Legitimate Engineering Scope (Why This Is Safe & Authorized)
1. **100% Owner-Owned Hardware:**
   * All radios referenced in this repository (`205CFR2930`, `205CMB2249`, `407CHT0214`) and all programming/keyfill cables (USB CDC-ACM cables, RP2040 Pi Pico KFD adapters) are **personally owned surplus hardware** belonging to the repository owner (Mario) on his local workbench.
2. **Interoperability with Legacy File Formats (`.cpg` / `.tun`):**
   * The original 2002-era Motorola ASTRO 25 CPS (`R20.01.00`) is discontinued 32-bit Windows XP software that does not run on modern Linux (`Fedora`) or modern 64-bit systems without broken Wine/VM workarounds.
   * The `.cpg` file container uses a static, non-secret legacy obfuscation key (`"A8Z6J9QP5"`, 40-bit RC4) hardcoded identically in every copy of the legacy software so users can save and open their own `.cpg` files. Decoding and encoding `.cpg` files here is strictly for **file format interoperability** with the owner's own codeplug backups (`backups/`).
3. **User-Generated Keys Only (KFDtool / TIA-102.AACD-A Standard):**
   * The keyloader tooling (`cleanroom_flasher/kvl_probe.py`) implements the standard, published **TIA-102.AACD-A (P25 Key Fill Device / Manual Rekey)** interface and the open-source **KFDtool** serial protocol to load **the owner's own self-generated keys** into his own radios.
   * P25 hardware crypto modules (UCM) are write-only for keys by hardware design — this tool **cannot** extract keys from radios, break encryption, or access any third-party system.
4. **Hardware & RF Safety Guardrails:**
   * **Receive-Only Lockout (`rx_only: true`):** Any public-safety monitoring channels included in example templates have the hardware transmitter power amplifier locked out (`rx_only: true`).
   * **Soft-Pot Calibration Protection:** Radio write operations (`write_ish`, `enter_write_mode`, `commit` in `cleanroom_flasher/rcmp_socket_transport.py`) are gated to protect read-only (`AccessRights == 0`) and locked (`AccessRights == 2`) factory RF calibration / tuning partitions. Never remove these safety gates without verifying `AccessRights == 1` (`IsRWPartition`).

---

## Key Commands

* **Run Full Test Suite (66 tests):**
  ```bash
  pytest
  ```
* **Inspect / Decode / Write `.cpg` Codeplugs (Offline):**
  ```bash
  open-astro read-cpg backups/205CFR2930.cpg
  open-astro decode-cpg backups/205CFR2930.cpg -o codeplug.json --csv channels.csv
  open-astro write-cpg codeplug.json patched.cpg --template backups/205CFR2930.cpg
  ```
* **Detect & Probe Connected Radio (Read-Only AT Interface):**
  ```bash
  open-astro ports
  open-astro probe --port /dev/ttyACM0
  ```
* **Test Read-Only RCMP-over-TCP Transport (Requires `ppp0` up on `192.168.128.2:192.168.128.1`):**
  ```bash
  python cleanroom_flasher/rcmp_socket_transport.py --read-ish 2 --json
  ```
* **Probe KFD / KVL Adapter (Skips Radio `0cad:1001` Automatically):**
  ```bash
  python cleanroom_flasher/kvl_probe.py
  ```

## Key Documentation
* [`docs/NEXT_AGENT_HANDOFF.md`](docs/NEXT_AGENT_HANDOFF.md) — Current state and step-by-step Fedora hardware bringup checklist.
* [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Complete system architecture map.
* [`docs/CPG_FILE_FORMAT.md`](docs/CPG_FILE_FORMAT.md) — Verified `.cpg` and `.tun` binary file formats and ISH stream tag directory.
* [`docs/NEXTGEN10_RCMP_DISASSEMBLY.md`](docs/NEXTGEN10_RCMP_DISASSEMBLY.md) — Verified RCMP opcodes, TCP port `8002`, and partition access-rights model.
* [`docs/AT_INTERFACE_DISCOVERY.md`](docs/AT_INTERFACE_DISCOVERY.md) — Verified USB CDC-ACM AT command interface and PPP dialup sequence (`AT#DATLCL=1` $\to$ `ATD` $\to$ `CONNECT`).
