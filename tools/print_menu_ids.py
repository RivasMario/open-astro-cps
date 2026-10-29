import pefile
import sys
sys.path.append('C:/Users/skyway/open-astro-cps/tools')
from dump_depot_menus import parse_menu

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id == pefile.RESOURCE_TYPE['RT_MENU']:
        for subentry in entry.directory.entries:
            if subentry.id == 1030:
                data_rva = subentry.directory.entries[0].data.struct.OffsetToData
                size = subentry.directory.entries[0].data.struct.Size
                raw = pe.get_data(data_rva, size)
                menu = parse_menu(raw)
                def find_items(items, prefix=""):
                    for it in items:
                        if it.get('type') == 'item':
                            print(f"{it['id']:5d} (0x{it['id']:04x}): {prefix} -> {it['title']}")
                        elif it.get('type') == 'popup':
                            p = f"{prefix} -> {it['title']}" if prefix else it['title']
                            find_items(it.get('items', []), p)
                find_items(menu)
