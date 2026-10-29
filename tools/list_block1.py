with open('C:/Users/skyway/open-astro-cps/tools/depot_raw_strings.txt', 'r', encoding='utf-8') as fp:
    lines = [l.strip() for l in fp if l.strip()]

start_idx = None
for i, l in enumerate(lines):
    if l.endswith(': Light') and '0x0113bed8' in l:
        start_idx = i
        break

print(f"Start at line {start_idx}: {lines[start_idx]}")
button_options = []
for i in range(start_idx, start_idx + 60):
    parts = lines[i].split(': ', 1)
    if len(parts) == 2:
        foff = parts[0]
        name = parts[1]
        button_options.append((name, foff))
        if name == 'ZnDn':
            break

print(f"Total options in block 1: {len(button_options)}")
for idx, (name, foff) in enumerate(button_options):
    print(f"Index {idx:2d} (0x{idx:02x}): {name:<25} ({foff})")
