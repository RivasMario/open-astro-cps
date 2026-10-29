# KVL / KFD Key-Fill Bring-Up (side project)

Goal of this step: **get the two key-fill adapters talking** before any key is
ever loaded. Identify them, confirm firmware/self-test. No keys, no radio
writes yet.

## The hardware

Two adapters, same host-side protocol (KFDtool adapter protocol, USB CDC serial
115200 8N1), different box:

| Adapter | Chain |
|---|---|
| Pi cable | USB-A → USB-C → **Pi Pico (RP2040)** → TRRS → Hirose → radio |
| KFDtool-compatible USB adapter (KVL Mini) | USB-A → USB-C → **adapter box** → TRRS → Hirose → radio |

* **TRRS** carries the P25 **3-wire key-fill bus** (data / sense / ground) — the
  classic "keyloader" interface (TIA-102.AACD).
* **Hirose** = the XTS side connector. The radio must be put into key-load mode
  for an actual fill (menu / key-signature pulse); identify + self-test below do
  **not** need the radio and do not touch the bus.
* Reference: `KFDtool_Manual.pdf` and the KFDtool-fork app `KVL Mini.zip`
  (both on the Drive, `…/ASTRO25SOFTWARE/`). KFDtool is open source — the
  protocol here is public, not blind-RE'd like the codeplug side.

## Expected USB enumeration (Fedora)

* **Pi Pico**: usually VID `2e8a` (Raspberry Pi), `/dev/ttyACM*`. A custom
  firmware may report a different VID.
* **KFDtool-compatible USB adapter (KVL Mini)**: often a USB-UART bridge — CH340 (`1a86`), CP210x (`10c4`), or a
  TI MSP430 (`2047`) if it's a KFDtool-compatible adapter — `/dev/ttyUSB*` or
  `/dev/ttyACM*`.
* **Do NOT** confuse with the XTS radio itself (`0cad:1001`, also `ttyACM*`);
  `kvl_probe.py` auto-skips that VID:PID so it never sends keyfill framing to the
  radio's AT port.

`lsusb` and `python -c "import serial.tools.list_ports as l;[print(p.device,p.vid,p.pid,p.description) for p in l.comports()]"` show what's attached.

## Steps (run on the Fedora laptop with the adapter plugged in)

```bash
# one adapter at a time is cleanest for first contact
python cleanroom_flasher/kvl_probe.py                 # scan all candidate ports
python cleanroom_flasher/kvl_probe.py /dev/ttyACM0    # a specific port
python cleanroom_flasher/kvl_probe.py --no-self-test  # identify only
```

Reports, per adapter: AP version, firmware version, hardware rev, **model_id**,
serial, and self-test pass/fail.

## Reading the result

* **Answers with a model_id + fw** → it's a KFDtool-protocol adapter and our
  pure-Python stack can drive it. Note the `model_id` for each (it tells us what
  each box emulates — stock KFDtool, MR, Pi-firmware, etc.).
* **Self-test pass** → the adapter's own 3-wire driver/loopback is healthy.
* **No answer** → wrong port, or the firmware uses a different framing. Capture
  the model/markings and we adapt `kvl_probe.py`.

## After both are identified (next steps, not this step)

1. Decide which adapter to drive (likely whichever self-tests clean).
2. Finish the P25 **Manual Rekey (MR)** key-load session on top of the adapter
   layer in `kfdtool.py` (the adapter I/O exists; the MR/KMM frames are the gap),
   validated against the open KFDtool source + the `KVL Mini` .NET DLLs.
3. First real fill: an **ADP (0xAA)** test key into one XTS, verified by the
   radio showing the key loaded — then AES-256. Keep it off any shared/public
   channel.
