import json

with open(r"C:\Users\skyway\open-astro-cps\schema\depot_fuzzer_buttons.json") as f:
    data = json.load(f)

for cid, cdata in data.items():
    print(f"Control {cid}: options = {list(cdata['options'].keys())}")
