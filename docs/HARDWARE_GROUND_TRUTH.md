# Hardware Ground Truth

Everything in this file was measured on real hardware. Nothing here is inferred.
Keep it that way: if a claim cannot be reproduced by a command shown below, it
does not belong in this file.

**Verified:** 2026-10-20, Fedora (kernel 7.2.11), Motorola XTS 2500 attached.

---

## 1. The XTS 2500 is a native USB CDC-ACM device, not an FTDI serial cable

This invalidates the transport assumption the rest of this repo was built on.
There is no FTDI/Prolific/CH340 bridge chip in the path and no `/dev/ttyUSB0`.
The radio itself is the USB device.

```
$ lsusb
Bus 003 Device 005: ID 0cad:1001 Motorola CGISS MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO
```

```
$ lsusb -v -d 0cad:1001
bDeviceClass            2 Communications
bDeviceSubClass         2 Abstract (modem)
idVendor           0x0cad Motorola CGISS
idProduct          0x1001 MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO
iManufacturer           1 Motorola Inc.
bNumInterfaces          2
  Interface 0: class 2/2/1 (Communications / Abstract modem / AT-commands v.25ter)
    CDC Header 1.01, CDC Call Management, CDC Union, CDC ACM (line coding + serial state)
    EP 0x84 IN, Interrupt, 32 bytes, bInterval 1      <- notifications
  Interface 1: class 10/0/0 (CDC Data)
    EP 0x01 OUT, Bulk                                 <- host -> radio
    EP 0x82 IN,  Bulk                                 <- radio -> host
```

The kernel binds `cdc_acm` to both interfaces with no quirks or out-of-tree driver:

```
$ readlink /sys/bus/usb/devices/3-2:1.0/driver
.../bus/usb/drivers/cdc_acm
$ ls /sys/bus/usb/devices/3-2:1.0/tty/
ttyACM0
```

### What follows from this
* The port is **`/dev/ttyACM0`**, not `/dev/ttyUSB0`.
* Baud rate, parity and stop bits are **cosmetic**. CDC-ACM carries line-coding
  requests, but there is no UART on the far end of the USB link, so "19200 8-N-1"
  configures nothing. Byte timing is set by USB bulk transfers (12 Mbps full
  speed), not by a 19,200 baud wire. Any timing analysis in the other docs that
  reasons from `19200 / 10 = 1920 bytes/sec` does not apply to this radio.
* `MaxPower 20mA` / `Self Powered`: the radio powers itself from its battery and
  draws almost nothing from the host.
* The `AT-commands (v.25ter)` interface protocol is a hint, not proof, that the
  command layer is line-oriented rather than the binary SB9600 framing this repo
  currently implements. Treat it as a lead to confirm, not a conclusion.

```
$ python3 -c "import serial.tools.list_ports as l; [print(p.device,'|',p.description,'|',p.hwid) for p in l.comports() if p.vid]"
/dev/ttyACM0 | MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO - Motorola Communication Interface | USB VID:PID=0CAD:1001 LOCATION=3-2:1.0
```

---

## 2. Port permissions

```
$ ls -l /dev/ttyACM0
crw-rw----. 1 root dialout ... /dev/ttyACM0
$ id
uid=1000(mario) ... groups=1000(mario),10(wheel),968(docker)
```

`mario` is **not** in `dialout`, so opening the port fails with `PermissionError`.
Either fix works:

```bash
sudo cp scripts/99-openastro.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger   # uaccess, no re-login
# or
sudo usermod -aG dialout $USER                                # needs log out / newgrp
```

The udev rule in `scripts/` now covers `0cad:1001`; the earlier version only had
cable bridge chips and would never have matched this radio.

---

## 3. Port auto-detection was selecting the wrong device

This machine exposes 31 legacy 16550 ports (`/dev/ttyS0`–`ttyS31`) with no USB
hwid. The previous `auto_detect_port()` matched on description substrings
(`ftdi`, `prolific`, `ch340`, `cp210`, `usb serial`), none of which appear in
`MOTOROLA XTS 1500 , 2500 & MT 1500 RADIO`, then fell through to `ports[0]`:

```
auto_detect_port() -> /dev/ttyS31
```

Detection is now by USB VID/PID, and ports without a USB hwid are never
candidates. Verified result: `/dev/ttyACM0`.

---

## 4. What is still unknown

Open questions, in the order they block progress:

1. **The command protocol.** Unknown. The opcode table in
   `docs/astro_cps_reverse_engineering_guide.md`,
   `docs/cps_subsystems_reference_notes.md` and the packet traces in
   `docs/deep_dive_radio_port_and_cpg_relational_database.md` were reasoned out,
   not captured or disassembled. See `docs/PROTOCOL_STATUS.md`.
2. **The memory map.** Unknown. The partition addresses and the dual-bank A/B
   layout in `flasher.py` have the same origin.
3. **Whether reads are safe to attempt.** Sending unrecognized frames to the
   radio is probably inert, but "probably" is not a basis for a first contact
   test. Confirm the framing first.

### Ground-truth sources available offline
* `~/GoogleDrive/RADIO/ASTRO25SOFTWARE/astro25portablecpsr20.01.00/` — real
  ASTRO 25 Portable CPS R20.01.00 installer (InstallShield: `data1.hdr`,
  `data1.cab` 6.8 MB, `data2.cab` 28 MB). Contains the actual CPS binaries and
  its communication code.
* `~/GoogleDrive/RADIO/ASTRO25SOFTWARE/ASTRO_25_PORTABLE_DEPOT_R20.01.00.zip` —
  Depot build, same InstallShield layout (`data2.cab` 46 MB).
* `~/GoogleDrive/RADIO/ASTRO25SOFTWARE/KFDtool_Manual.pdf` — documents the P25
  TIA-102.AACA key-fill interface.

`7z` cannot open InstallShield `.cab` archives (`Open ERROR: Cannot open the file
as [Cab] archive`). `unshield` is the right tool and is packaged for Fedora but
not yet installed:

```bash
sudo dnf install -y unshield
unshield -d /tmp/cps_extract x "<path>/data1.cab"
```
