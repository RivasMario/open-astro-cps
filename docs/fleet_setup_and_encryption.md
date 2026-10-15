# Fleet Configuration & Encryption Guide

This guide documents the setup for your specific radio fleet and how to operate safely on 800 MHz without interfering with public safety systems.

---

## 📻 Hardware Inventory

Identified from your `RadioInventory.xlsx`:

| Radio Nickname | Model | Features | Assigned Role |
| :--- | :--- | :--- | :--- |
| **`KENTPD_XTS2500`** | **Motorola XTS 2500 Model II** | Front LCD Display, 6 Menu Keys, 700/800 MHz | **Command Unit / Master Scanner** |
| **`CHRIS_XTS_2500`** | **Motorola XTS 2500 Model I** | Top 16-ch Rotary Knob, No Display, 700/800 MHz | **Tactical Field Radio A** |
| **`FACEBOOK_XTS2500`** | **Motorola XTS 2500 Model I** | Top 16-ch Rotary Knob, No Display, 700/800 MHz | **Tactical Field Radio B** |
| **`BAOFENG UV5R`** | Baofeng UV-5R | Dual Band (VHF/UHF), Keypad VFO | Auxiliary / Cross-band Test |

---

## 🛡️ The Golden Rule: Preventing Emergency Interference

Because these radios operate in the **764–870 MHz** band where Washington State Patrol, King County, and municipal police/fire operate:

1. **`rx_only: true` Lockout**:
   * All public safety, county dispatch, and control channels must have `rx_only: true` set in the codeplug.
   * This **physically disables the transmitter Power Amplifier (PA)** inside the radio firmware. Pressing PTT will bonk and emit zero RF watts.
2. **Non-Affiliate Scan (NAS)**:
   * The radio passively monitors trunked control channels without transmitting registration ("affiliation") packets to the cell tower.

---

## 🔒 Encryption: Motorola ADP vs. Hardware AES

OpenAstro supports both software-based and hardware-based encryption:

### Level 1: Motorola ADP (Software 40-bit RC4)
* **Hardware required:** NONE (Runs natively on the XTS 2500 DSP vocoder).
* **Key Format:** 10 hexadecimal digits (e.g., `A1B2C3D4E5`).
* **How it works:**
  * In `king_county_800mhz_fleet.json`, `TEAM ENCRYPT` is strapped to `secure_strapping: "Secure"` with `key_id: 1`.
  * All 3 radios share the exact same key.
  * Transmissions are completely indecipherable to scanners, SDRs, and non-keyed radios (sounding like garbled digital static).

### Level 2: Hardware AES-256 (NSA Type-1)
* **Hardware required:** Universal Crypto Module (UCM) daughterboard installed inside the radio.
* **Key Format:** 64 hexadecimal characters.
* **Keyloading:** Loaded over the side accessory connector via **KFDtool** (included in your `ASTRO25SOFTWARE` archive).
* When you plug your `KENTPD_XTS2500` into OpenAstro, the probe command will check if `SEC_ALG` reports an internal crypto module.

---

## 📋 3-Zone Channel Plan Architecture

Included in [`examples/king_county_800mhz_fleet.json`](../examples/king_county_800mhz_fleet.json):

### Zone 1: TEAM SECURE (Transmit Enabled)
* **Ch 1: `TEAM CLEAR`** (`851.5125 MHz`) — P25 Digital Simplex ($293 NAC, Talkgroup 1).
* **Ch 2: `TEAM ENCRYPT`** (`852.0125 MHz`) — P25 Digital Simplex with **ADP Encryption** (`TEAM_ADP_1`).
* **Ch 3: `TEAM ANALOG`** (`853.0125 MHz`) — Analog FM Simplex with CTCSS PL tone `156.7 Hz`.

### Zone 2: 800 INTEROP (Mutual Aid Channels)
* **Ch 1: `8CALL90`** (`851.0125 MHz`) — National 800 MHz Calling Channel (PL 156.7 Hz).
* **Ch 2: `8TAC91`** (`851.5125 MHz`) — National Tactical Channel 1.
* **Ch 3: `8TAC92`** (`852.0125 MHz`) — National Tactical Channel 2.

### Zone 3: PS MONITOR (Strictly RX-Only Lockout)
* **Ch 1: `PSERN CTRL 1`** (`851.8875 MHz`) — PSERN King County Core Control Channel.
* **Ch 2: `PSERN CTRL 2`** (`852.8625 MHz`) — PSERN King County Alternate Control Channel.
* **Ch 3: `PSERN CTRL 3`** (`853.8250 MHz`) — PSERN King County Alternate Control Channel.
