import pefile
import struct
import capstone

with open(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe', 'rb') as fp:
    raw = fp.read()

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Jump table at 0x00b2eec3 -> file offset = 0x0072eec3
# Index table at 0x00b2f07b -> file offset = 0x0072f07b
# Case index range: 0 to 0x191 (401 values)
# input_id = case_index + 0x78

jump_table_file_off = 0x0072eec3
index_table_file_off = 0x0072f07b

# Load strings from resources if possible, or see what string IDs are
# String IDs: 0x1562 = 5474, etc.
# In Win32 PE resources, string tables store strings by ID!
# String ID -> String Resource: bundle = ID // 16 + 1, index = ID % 16
pe = pefile.PE(data=raw)

strings_by_id = {}
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id == pefile.RESOURCE_TYPE['RT_STRING']:
        for subentry in entry.directory.entries:
            bundle_id = subentry.id
            for lang in subentry.directory.entries:
                data_rva = lang.data.struct.OffsetToData
                size = lang.data.struct.Size
                res_data = pe.get_data(data_rva, size)
                # Parse 16 strings in bundle
                idx = 0
                for i in range(16):
                    if idx >= len(res_data): break
                    str_len = struct.unpack('<H', res_data[idx:idx+2])[0]
                    idx += 2
                    if str_len > 0:
                        s = res_data[idx:idx+str_len*2].decode('utf-16le', errors='replace')
                        str_id = (bundle_id - 1) * 16 + i
                        strings_by_id[str_id] = s
                        idx += str_len * 2

print(f"Loaded {len(strings_by_id)} resource strings")

# For each target in jump table:
# Let's read jump table targets:
# Number of cases: default is at 0xb2eeb3 -> file 0x0072eeb3
# Let's disassemble each target
targets = {}
for edx in range(110): # max index in table
    ptr_foff = jump_table_file_off + edx * 4
    if ptr_foff + 4 > len(raw): break
    target_va = struct.unpack('<I', raw[ptr_foff:ptr_foff+4])[0]
    target_foff = target_va - 0x00400000
    if 0 <= target_foff < len(raw):
        # disassemble 15 bytes at target
        code = raw[target_foff:target_foff+15]
        str_id = None
        for ins in md.disasm(code, target_va):
            if ins.mnemonic == 'mov' and '0x' in ins.op_str:
                # e.g. mov dword ptr [ebp - 8], 0x1562
                parts = ins.op_str.split(',')
                if len(parts) == 2:
                    try:
                        str_id = int(parts[1].strip(), 16)
                    except:
                        pass
            if ins.mnemonic == 'jmp':
                break
        targets[edx] = (target_va, str_id)

# Now map input_id -> case_index -> edx -> str_id -> string
mappings = []
for case_idx in range(0x192):
    idx_foff = index_table_file_off + case_idx
    edx = raw[idx_foff]
    input_id = case_idx + 0x78
    if edx in targets:
        t_va, str_id = targets[edx]
        name = strings_by_id.get(str_id, f"Unknown string ID {str_id}")
        mappings.append((input_id, edx, str_id, name))

print(f"Total mapped button tokens: {len(mappings)}")
# Group by name to see unique buttons
unique_buttons = {}
for input_id, edx, str_id, name in mappings:
    if str_id is not None:
        if name not in unique_buttons:
            unique_buttons[name] = []
        unique_buttons[name].append(input_id)

with open('C:/Users/skyway/open-astro-cps/tools/depot_button_tokens.txt', 'w', encoding='utf-8') as out:
    out.write(f"{'Button Function':<35} | {'Token IDs (Hex)':<30} | {'Resource ID'}\n")
    out.write("-" * 80 + "\n")
    for name, ids in sorted(unique_buttons.items()):
        hex_ids = ', '.join(f"0x{i:02x}" for i in ids[:10])
        out.write(f"{name:<35} | {hex_ids:<30} | {strings_by_id.get(name, '')}\n")

print("Saved to tools/depot_button_tokens.txt")
