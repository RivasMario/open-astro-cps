import pefile, re

with open(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe", "rb") as fp:
    exe_data = fp.read()

# Search for "Add Member" or "Member"
matches = re.findall(b"Add Member[a-zA-Z0-9_ ]*", exe_data, re.IGNORECASE)
print("Matches in PatPortDepot.exe:", set(matches))
