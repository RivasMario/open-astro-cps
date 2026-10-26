import json

with open(r"C:\Users\skyway\open-astro-cps\schema\depot_fuzzer_buttons.json") as f:
    data = json.load(f)

for cid, info in data.items():
    print(f"Control ID {cid}:")
    for opt_name, opt_data in info["options"].items():
        diffs = opt_data.get("diffs", {})
        for obj, d in diffs.items():
            if "0020" in obj:
                print(f"  Option '{opt_name}': {d['changed_bytes']}")
