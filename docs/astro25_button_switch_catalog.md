# Motorola ASTRO 25 Physical Controls & Button Catalog

This document provides the complete catalog of physical button, switch, and rotary control options extracted directly from the internal schema of **ASTRO 25 Portable Depot (`PatPortDepot.exe`)**.

---

## 1. Physical Controls Architecture

On Motorola ASTRO 25 portables (XTS 2500 / XTS 5000), physical controls are managed primarily by two codeplug objects:

* **`0x0020:0` (Conventional Physical Controls Table):**
  Controls the physical assignments when operating on conventional channels.
* **`0x0022:0` (Trunking Physical Controls Table):**
  Controls the physical assignments when operating on trunked systems.

### Hardware Control IDs (`0x0020:0` / `0x0022:0`)

| Control ID | Hardware Control | Physical Location | Default Value | Notes |
| :---: | :--- | :--- | :---: | :--- |
| **`0x60`** | **Side Button 1** | Top button above PTT (**Purple**) | `0x18` (Light) | Momentary push |
| **`0x03`** | **Side Button 2** | Middle button below PTT (**1-Dot**) | `0x1a` (Scan) | Momentary push |
| **`0x62`** | **Side Button 3** | Bottom button below PTT (**2-Dot**) | `0x19` (Monitor) | Momentary push |
| **`0x61`** | **Top Button** | Top panel push button (**Orange/Red**) | `0x21` (Talkaround) | Momentary push |
| **`0x04`** | **16-Pos Rotary** | Top rotary selector knob | `0x1d` (Ch Select) | 16-position continuous |
| **`0x94`** | **Switch 94** | Internal switch matrix / logic | `0x1a` | Hardware strapping |
| **`0x86`** | **Switch 86** | Concentric collar / ancillary | `0x23` (Unprog) | Floating collar on Model II |

---

## 2. Complete Catalog of Conventional Momentary Button Options

The following 45 functions are available for the momentary buttons (Purple, 1-Dot, 2-Dot, Orange) in ASTRO 25 Portable Depot:

| # | Function Name | Screen Indicator / Behavior | Notes & Hardware Feedback |
| :---: | :--- | :--- | :--- |
| 1 | **`Light`** | Backlight illuminates timer | **Verified Working** on Purple button (`0x18`). |
| 2 | **`Monitor`** | Squelch open icon / static hiss | **Verified Working** on Bottom Side button (`0x19`). |
| 3 | **`TalkAround/Direct`** | `|<-|` icon (Repeater bypass) | **Active only on repeater channels** (TX != RX). Silent/bonks on simplex channels. |
| 4 | **`Scan`** | `Z` scan icon | **Requires non-empty Scan List**. Bonks if scan list has no channels. |
| 5 | **`ZnUp` (Zone Up)** | Zone name changes (`TEAM OPS` &rarr; `800 INTEROP`) | **Immediate screen feedback** on every press. Cycles forward through zones. |
| 6 | **`ZnDn` (Zone Down)** | Zone name changes backward | **Immediate screen feedback**. Cycles backward through zones. |
| 7 | **`Unprogrammed`** | None | Button disabled (`0x23`). |
| 8 | **`Volume Set Tone`** | Audio tone emitted | Emits continuous tone for setting volume knob level. |
| 9 | **`Emergency`** | `EMERGENCY` on LCD / alarm | Sends emergency MDC/P25 packet or alarm tone. |
| 10 | **`Channel Select`** | Channel name changes | Steps channel up. |
| 11 | **`Zone Select`** | Zone name changes | Steps zone up. |
| 12 | **`Phone`** | Phone icon / keypad dial prompt | Initiates telephone interconnect interconnect mode. |
| 13 | **`Select Call`** | Call ID list | Paging/Call list entry. |
| 14 | **`Call Alert`** | Page alert list | Sends call alert page. |
| 15 | **`Nuisance Delete`** | Removes channel from current scan | Temporarily ignores active nuisance channel while scanning. |
| 16 | **`Dynamic Priority`** | Priority scan indicator | Changes dynamic priority channel in scan list. |
| 17 | **`Keypad Lock`** | `LOCK` / Key icon | Locks front keypad from accidental presses. |
| 18 | **`One Touch 1..4`** | Pre-programmed call/status | Sends 1-touch MDC/P25 status or call. |
| 19 | **`Channel Announcement`**| Voice audio prompt | Radios with voice announcement chip speak current channel. |
| 20 | **`Secure/Clear Mode`** | `Ø` lock icon toggle | Toggles personality between ADP encrypted and clear TX. |
| 21 | **`Voice Mute`** | Mutes RX speaker | Silence audio. |
| 22 | **`Dim`** | LCD contrast / dim toggle | Dims LCD for night operations. |
| 23 | **`SPKR`** | Speaker toggle | Routes audio between internal speaker and RSM. |
| 24 | **`TMS` / `TMS Quick Text`** | Text messaging inbox / templates | ASTRO 25 Packet Data text messaging. |
| 25 | **`MS1` / `MS2` / `MS3`** | Mode Select memory preset | Recalls pre-programmed Zone/Channel snapshot. |

---

## 3. Rotary & Switch Options (Toggle / Concentric Collar)

Switches that maintain a physical static state (such as the 3-position toggle `A/B/C` or 2-position concentric collar switch) support stateful functions:

| Function Name | Description |
| :--- | :--- |
| **`Tx Low Power`** | Toggles RF output power between Low (1W) and High (3W/5W). `LOW PWR` icon on LCD. |
| **`PL Disable`** | Disables CTCSS / DCS receive decoding to listen to carrier squelch. |
| **`Secure Tx Select`** | Forces all transmissions to be hardware/software encrypted (`Ø` icon). |
| **`Clear Tx Select`** | Forces all transmissions to be clear unencrypted. |
| **`Tx Inhibit`** | Disables transmitter RF amplifier entirely (receive-only mode). |
| **`Zone Select (A/B/C)`** | Switch position A = Zone 1, B = Zone 2, C = Zone 3. |
| **`Scan On/Off`** | Position A = Scan enabled, Position B = Scan disabled. |

---

## 4. Why 1-Dot and Orange Buttons Didn't Change the Screen

1. **Top Orange Button (`TalkAround/Direct`):**
   * **Behavior:** Motorola firmware only allows Talkaround toggling on **repeater channels** where the transmit frequency differs from the receive frequency.
   * **Our Test Codeplug:** All 3 channels (`OPEN ASTRO`, `TEAM ANALOG`, `ADP SECURE`) are programmed as **simplex** channels (`851.0125 / 851.0125 MHz`, `852.0125 / 852.0125 MHz`).
   * Because the radio is already communicating directly without a repeater, pressing `TalkAround` is ignored by firmware (or emits a bonk).
2. **Side Button 2 (1-Dot, `Scan`):**
   * **Behavior:** The scan list in our codeplug (`0x0049:0`) is currently empty (`0xFF`).
   * When `Scan` is pressed on a channel with no members in its scan list, the firmware refuses to engage scanning and does not display the `Z` icon.

---

## 5. Recommended Adjustments for Instant Screen Feedback

If you want immediate visual/audio confirmation on all buttons:

* **Top Orange Button:** Can be mapped to:
  * **`Volume Set Tone`**: Emits a test tone when pressed.
  * **`Emergency`**: Displays `EMERGENCY` on LCD and emits alert.
  * **`ZnUp` / `Zone Select`**: Cycles zones.
* **Side Button 2 (1-Dot):**
  * **Option A:** Map to **`ZnUp`** &rarr; Pressing it immediately changes the zone name on the LCD (`TEAM OPS` &rarr; `800 INTEROP` &rarr; `TAC OPS`).
  * **Option B:** Keep as **`Scan`**, and we populate Scan List 1 (`0x0049:0`) with Channels 1, 2, and 3 so the **`Z`** scan icon lights up and starts cycling channels.
