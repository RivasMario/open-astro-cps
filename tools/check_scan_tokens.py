import json

with open(r"C:\Users\skyway\open-astro-cps\schema\depot_fuzzer_buttons.json") as f:
    data = json.load(f)

for cid, cdata in data.items():
    for opt_name, odata in cdata['options'].items():
        if 'scan' in opt_name.lower():
            diffs = odata.get('diffs', {})
            print(f"Control {cid} '{opt_name}': {diffs}")
