# Running OpenAstro on Fedora Linux

Motorola's official CPS software **never ran natively on Linux**. 

**OpenAstro runs 100% natively on Fedora** (and all modern Linux distributions) with zero virtual machines, zero Wine, and full USB serial support.

---

## 🛠️ 1. Prerequisites on Fedora

Open your terminal and install Python 3 and git:

```bash
sudo dnf install -y python3 python3-pip python3-devel git
```

---

## 🔌 2. USB Cable Permissions (One-Time Setup)

By default, Linux restricts access to serial hardware (`/dev/ttyUSB0`). To give your standard user access without needing `sudo`:

### Step A: Add your user to the `dialout` group
```bash
sudo usermod -aG dialout $USER
```
*(Log out and log back in for the group change to take effect, or run `newgrp dialout`)*.

### Step B: Install the OpenAstro Udev Rules
Inside the `open-astro-cps` repository:
```bash
sudo cp scripts/99-openastro.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

This ensures that whenever you plug in an FTDI, Prolific, or CH340 programming cable, Linux automatically grants read and write permissions to your user account.

---

## 🚀 3. Installing OpenAstro on Fedora

```bash
# Clone the repository
git clone https://github.com/RivasMario/open-astro-cps.git
cd open-astro-cps

# Create and activate a clean virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies and OpenAstro in editable mode
pip install -e .
```

---

## 🧪 4. Testing Hardware on Fedora

### A. Detect Connected Radio Cable
Plug in your Motorola USB programming cable and run:
```bash
open-astro ports
```
Fedora will report:
```
[+] Detected Serial Ports:
  -> /dev/ttyUSB0 (FT232R USB UART - FTDI)
```

### B. View Your 800 MHz Fleet Template
```bash
open-astro info examples/king_county_800mhz_fleet.json
```

### C. Convert Between JSON and CSV (LibreOffice Calc)
On Fedora, you can open and edit your channel list directly in LibreOffice Calc:
```bash
# Export to CSV
open-astro to-csv examples/king_county_800mhz_fleet.json my_fleet.csv

# Open in LibreOffice Calc
libreoffice my_fleet.csv &

# Convert back to JSON when done
open-astro from-csv my_fleet.csv updated_fleet.json
```
