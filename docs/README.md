# Docs index

Every doc, labelled by how far to trust it. **Rule:** a claim about Motorola's
software or the radio is only "verified" if it was checked against the real CPS
binaries or a real radio/capture. This repo has a history of plausible but
invented protocol docs, so check the label before relying on anything.

## Current — start here

| Doc | What it is |
|---|---|
| [HANDOFF_RCMP_LIVE.md](HANDOFF_RCMP_LIVE.md) | **Current state**, how-to, open work, end-of-session status |
| [RCMP_WIRE_PROTOCOL.md](RCMP_WIRE_PROTOCOL.md) | RCMP records, opcodes, CRC, session shape (verified vs captures) |
| [CPS_ISH_SCHEMA.md](CPS_ISH_SCHEMA.md) | CPS codeplug schema from the binaries: partitions/access rights, 169-block type→item map, `.cpg` directory, write-path architecture, partial field layouts |
| [CPG_FILE_FORMAT.md](CPG_FILE_FORMAT.md) | `.cpg` container, RC4, per-object CRC |
| [PROVENANCE_AUDIT.md](PROVENANCE_AUDIT.md) | Claim-by-claim verified / contradicted / unverified table |

## Verified reference

| Doc | What it is |
|---|---|
| [NEXTGEN10_RCMP_DISASSEMBLY.md](NEXTGEN10_RCMP_DISASSEMBLY.md) | NextGen10.dll opcode/send-routine analysis |
| [HARDWARE_GROUND_TRUTH.md](HARDWARE_GROUND_TRUTH.md) | USB descriptors, ports, permissions (XTS 2500) |
| [AT_INTERFACE_DISCOVERY.md](AT_INTERFACE_DISCOVERY.md) | AT identity interface + the ATD→PPP discovery |
| [CPS_BINARY_ANALYSIS.md](CPS_BINARY_ANALYSIS.md) | Early real-binary pass; §1 lists the real DLL names |
| [CPS_FILE_INVENTORY.md](CPS_FILE_INVENTORY.md) | What ships in the CPS install |
| [CPS_NETWORK_AND_SECURITY.md](CPS_NETWORK_AND_SECURITY.md), [ENCRYPTION_MODEL.md](ENCRYPTION_MODEL.md) | Network topology and crypto model notes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System overview (2026-10-22; write-path details now in CPS_ISH_SCHEMA.md) |
| [linux_fedora_setup.md](linux_fedora_setup.md) | Fedora setup and udev rules |

## Historical — superseded status docs (bannered)

[NEXT_AGENT_HANDOFF.md](NEXT_AGENT_HANDOFF.md),
[AGENT_HANDOFF_AND_MISSION_BRIEF.md](AGENT_HANDOFF_AND_MISSION_BRIEF.md),
[PROTOCOL_STATUS.md](PROTOCOL_STATUS.md), [KEYLOADER_ROADMAP.md](KEYLOADER_ROADMAP.md),
[gui_mockup.html](gui_mockup.html).

## Unaudited background essays (2026-10-14..19)

Written before the real binaries were read. Useful for RF/P25/trunking
background; **not** a protocol or CPS-internals reference. Several carry
known-wrong claims (fabricated opcode table, a nonexistent Jet database, an
invented dual-bank rollback):

[astro_cps_reverse_engineering_guide.md](astro_cps_reverse_engineering_guide.md),
[deep_dive_radio_port_and_cpg_relational_database.md](deep_dive_radio_port_and_cpg_relational_database.md),
[motorola_astro_cps_architecture_and_design_paper.md](motorola_astro_cps_architecture_and_design_paper.md),
[radio_write_failure_diagnosis_and_flashing_engine.md](radio_write_failure_diagnosis_and_flashing_engine.md),
[radio_architecture_and_demystification.md](radio_architecture_and_demystification.md),
[firmware_analysis_and_elint_fingerprinting.md](firmware_analysis_and_elint_fingerprinting.md),
[inventing_sovereign_digital_radio_protocols.md](inventing_sovereign_digital_radio_protocols.md),
[p25_infrastructure_and_roaming_systems_paper.md](p25_infrastructure_and_roaming_systems_paper.md),
[fleet_setup_and_encryption.md](fleet_setup_and_encryption.md).

## Unverified — confirmed fabricated (`_unverified/`)

Audited 2026-10-23 against every file in the CPS cab and the RADIO folder:
[_unverified/astro_25_software_internals_and_dll_architecture.md](_unverified/astro_25_software_internals_and_dll_architecture.md)
(all `A25*.dll` / `A25CPS.exe` names are invented),
[_unverified/cps_subsystems_reference_notes.md](_unverified/cps_subsystems_reference_notes.md)
(repeats the fake executables). Do not cite.
