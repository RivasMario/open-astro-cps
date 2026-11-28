# Bite-Sized Mission Directives for Local AI (Homelab)

Target Host: Proxmox LXC 112 / LXC 120 / TrueNAS Ollama  
Runner: `homelab-goose`, `homelab-claw`, or `diddy`  
Model: `qwen2.5-coder:14b` or `qwen3-hl:latest`  

---

## Bite 1: Depot Capture Delta Analysis
- **Goal:** Isolate the exact byte differences between standard CPS writes and Depot feature writes in offline JSON decodes.
- **Input Files:**
  - `captures/depot_write_20261024_215836_decoded.json`
  - `captures/DUMP_721CLZ0655_20261030_224912.json`
- **Action:**
  1. Parse the incoming RCMP packets where opcode indicates partition writes (`0x0002` or `0x0101`).
  2. Extract the target partition byte from the packet header.
  3. Filter out all Partition `0x80` records to isolate writes directed to Partition `0x81`.
  4. Print the exact byte offsets, lengths, and raw byte values written to Partition `0x81`.
- **Expected Output:** A concise table of `(offset, length, data_hex)` showing what Depot wrote to Partition `0x81`.

---

## Bite 2: Bootloader Rollback & Shadow EEPROM Analysis
- **Goal:** Determine why Partition `0x81` modifications revert upon radio power cycle.
- **Action:**
  1. Review `src/open_astro/protocol/` and documentation in `docs/` regarding the EEPROM partition layout.
  2. Identify the location of the checksum/HMAC trailer in Partition `0x81` (usually the trailing 16 or 32 bytes).
  3. Document whether the radio's Host firmware compares the primary Partition `0x81` image against a secondary shadow partition at boot time.
- **Expected Output:** Technical summary explaining the integrity check mechanism that triggers the rollback.

---

## Bite 3: Virtual Radio Sandbox Emulation (LXC 120)
- **Goal:** Run a virtual test with simulated ADP FLASHcode in pure software without touching physical hardware.
- **Action:**
  1. Access LXC 120 container `openastro-virtual-radio` or run locally:
     ```bash
     python tools/virtual_radio.py scratchpad/radio4_king_county_fixed.cpg \
       --host 0.0.0.0 --port 8002 \
       --serial 721CLZ0655 \
       --flashcode 500008-002000-0 \
       --model H18UCF9PW6AN \
       --capture-pcap captures/test_adp_emulation.pcap \
       --capture-jsonl captures/test_adp_emulation.jsonl \
       --verbose
     ```
  2. Connect a client or test script to port 8002 to verify that the virtual radio returns the simulated FLASHcode without error.
- **Expected Output:** Verified pcap and JSONL trace showing virtual CPS negotiation with simulated feature bits.

---

## Bite 4: Partition 0x80 Software Key Strap Feasibility
- **Goal:** Check whether conventional channel objects in Partition `0x80` can reference ADP key straps without modifying Partition `0x81`.
- **Action:**
  1. Inspect `src/open_astro/protocol/codeplug.py` structure for conventional channel records (`0x0010` / `0x0FFD`).
  2. Check if the encryption flag bit and key strap index byte can be populated in the codeplug JSON.
  3. Determine how the radio UI behaves if a channel has encryption enabled in Partition `0x80` while the global entitlement bit in `0x81` is clear.
- **Expected Output:** Recommendation on whether codeplug-level strapping provides soft-ADP operation.
