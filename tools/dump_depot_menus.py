import pefile
import struct
import json

def parse_menu(raw_data):
    # Standard Win32 Menu Resource:
    # WORD wVersion;
    # WORD wOffset;
    version, offset = struct.unpack_from('<HH', raw_data, 0)
    pos = 4 + offset
    
    items = []
    stack = [items]
    
    while pos < len(raw_data):
        flags = struct.unpack_from('<H', raw_data, pos)[0]
        pos += 2
        is_popup = bool(flags & 0x0010)
        is_end = bool(flags & 0x0080)
        
        if is_popup:
            # Read Unicode string
            text_chars = []
            while pos < len(raw_data):
                ch = struct.unpack_from('<H', raw_data, pos)[0]
                pos += 2
                if ch == 0:
                    break
                text_chars.append(chr(ch))
            text = ''.join(text_chars)
            submenu = []
            stack[-1].append({"title": text, "type": "popup", "items": submenu})
            stack.append(submenu)
        else:
            # Menu item: WORD menu_id followed by Unicode string
            menu_id = struct.unpack_from('<H', raw_data, pos)[0]
            pos += 2
            text_chars = []
            while pos < len(raw_data):
                ch = struct.unpack_from('<H', raw_data, pos)[0]
                pos += 2
                if ch == 0:
                    break
                text_chars.append(chr(ch))
            text = ''.join(text_chars)
            stack[-1].append({"title": text, "type": "item", "id": menu_id})
            
            while is_end and len(stack) > 1:
                stack.pop()
                # Check if parent was also at end
                break
                
    return items

def dump_tree(items, indent=0):
    lines = []
    prefix = "  " * indent
    for item in items:
        title = item.get('title', '')
        if not title:
            title = "--- Separator ---"
        if item['type'] == 'popup':
            lines.append(f"{prefix}[+] {title}")
            lines.extend(dump_tree(item['items'], indent + 1))
        else:
            cmd_id = item.get('id', 0)
            lines.append(f"{prefix}- {title} (ID: {cmd_id})")
    return lines

pe = pefile.PE(r'C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe')
RT_MENU = 4

all_menus = {}
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id == RT_MENU:
        for m in entry.directory.entries:
            data_rva = m.directory.entries[0].data.struct.OffsetToData
            size = m.directory.entries[0].data.struct.Size
            raw_data = pe.get_data(data_rva, size)
            try:
                tree = parse_menu(raw_data)
                all_menus[m.id] = tree
            except Exception as e:
                print(f"Error parsing menu {m.id}: {e}")

# Print major menus
for mid in [165, 1030, 524, 520]:
    if mid in all_menus:
        print(f"\n=======================================================")
        print(f"               MENU RESOURCE {mid}")
        print(f"=======================================================")
        for line in dump_tree(all_menus[mid]):
            print(line)
