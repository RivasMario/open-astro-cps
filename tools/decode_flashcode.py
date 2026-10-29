# Standard Motorola FLASHcode decoder
# 14 hex digits: D1 D2 D3 D4 D5 D6 - D7 D8 D9 D10 D11 D12 - Checksum

flashcode = "50000800048C"

# Known ASTRO 25 FLASHcode bits:
# D1: 0x4 = Q806 (ASTRO IMBE Digital Operation), 0x1 = H14/G114 (Digital ID Display) -> 0x5 = Q806 + H14
# D6: 0x8 = Q387 (Conventional Voting Scan)? Or H38 (SmartZone)?
# D9: 0x4 = Q667 (ADP Software Encryption)?
# D11: 0x8 = H35 (Conventional Systems Operation)?
# D12: 0x4 = Q157? 0x8 = ?
print(f"Analyzing {flashcode}...")
