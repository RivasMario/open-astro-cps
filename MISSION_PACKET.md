# MISSION PACKET: Open Astro CPS & ADP Entitlement Analysis

```json
{
  "mission_understanding": "Analyze ADP software encryption structures in open-astro-cps and determine safe codeplug configuration paths for Motorola XTS 5000 Model III (Serial: 721CLZ0655) without touching protected factory RF alignment partitions.",
  "affected_systems": [
    "/home/mario/Documents/GitHub/open-astro-cps",
    "/home/mario/Documents/GitHub/open-astro-cps/captures",
    "/home/mario/Documents/GitHub/open-astro-cps/scratchpad",
    "/home/mario/Documents/GitHub/open-astro-cps/src/open_astro/protocol",
    "/dev/ttyACM0"
  ],
  "execution_steps": [
    {
      "step_id": 1,
      "action_description": "Review codeplug decoding and conventional channel records in src/open_astro/protocol/ to locate encryption strap fields and key index mapping.",
      "tools_required": ["read_file", "search_files"],
      "expected_outcome": "Identify the exact struct offsets and bitmasks used for conventional channel ADP / clear straps."
    },
    {
      "step_id": 2,
      "action_description": "Inspect offline captures in captures/ (depot_write_20261024_215836_decoded.json and DUMP_721CLZ0655_*.json) to contrast Partition 0x80 object layout with Partition 0x81 entitlement blocks.",
      "tools_required": ["read_file", "python3"],
      "expected_outcome": "Map the difference between software ADP codeplug enablement vs hardware FLASHcode partition 0x81 feature bits."
    },
    {
      "step_id": 3,
      "action_description": "Verify scratchpad/radio4_king_county_fixed.cpg and validate channel 1 conventional simplex / direct parameters against Zone 1 requirements.",
      "tools_required": ["read_file", "run_command"],
      "expected_outcome": "Confirm Zone 1 conventional simplex configuration is 100% clean and consistent with King County channel plan."
    },
    {
      "step_id": 4,
      "action_description": "Query Proxmox LXC 120 (cps-capture) on 100.70.69.28 for reference CPS configuration dumps if additional comparison data is required.",
      "tools_required": ["ssh"],
      "expected_outcome": "Acquire baseline Motorola CPS reference codeplugs for comparison without live radio interception."
    }
  ],
  "safety_constraints": [
    "NEVER write to Partition 0x82 (RF alignment / tuning soft-pots). Modifying this partition can desensitize or permanently brick the RF deck.",
    "Do NOT execute live intrusive pcap sniffing or raw packet injection scripts on the active hardware interface /dev/ttyACM0.",
    "All radio communication scripts interacting with the serial interface must enforce identity verification: --expect-serial 721CLZ0655.",
    "Respect homelab host access boundaries (Tailscale 100.x network, key-only SSH ~/.ssh/homelab)."
  ]
}
```

---

## Technical Context & Reference Summary

### Target Radio Profile
- **Hardware Model:** Motorola XTS 5000 Model III (`H18UCF9PW6AN`)
- **Serial Number:** `721CLZ0655`
- **Current Operational State:** Online, connected via USB/PPP bridge on `/dev/ttyACM0`. Zone 1 conventional simplex direct channel operational without "OUT OF RANGE" warning.
- **Current Codeplug File:** [scratchpad/radio4_king_county_fixed.cpg](file:///home/mario/Documents/GitHub/open-astro-cps/scratchpad/radio4_king_county_fixed.cpg)

### Partition Architecture
- **Partition `0x80`:** Primary Codeplug Configuration. Standard read/write target for CPS. Holds zone pointers (`0x0FFC`), channel definitions (`0x0FFD`), scan lists, and talkgroups.
- **Partition `0x81`:** Radio Feature Configuration / FLASHcode entitlements. Holds cryptographic hardware IDs and licensed feature flags. Modifying without valid crypto signatures results in revert upon radio reboot.
- **Partition `0x82`:** Hardware Factory Tuning & Soft-Pots. **PROTECTED / FORBIDDEN.** Contains VCO calibration, deviation, reference oscillator tuning, and power output tables.

### Homelab Environment Links
- **Proxmox Node:** `100.70.69.28` (`pve`), LXC 120 (`cps-capture`), VM 102 (`win11-test`).
- **TrueNAS Node:** `100.81.194.15`, Ollama service at port `30068` (running `qwen2.5-coder:14b` and `qwen3-hl:latest`).
- **Local Runner Command:** `HOMELAB_GOOSE_MODEL="qwen3-hl:latest" homelab-goose` or `diddy execute`.
