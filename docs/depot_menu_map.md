# Motorola ASTRO 25 Depot / CPS Complete Menu Hierarchy Map

*Extracted directly from `PatPortDepot.exe` Win32 PE Menu Resources (no internet guesswork).*

---

## 1. Top Menu Bar (Resource 165 / 1030)

When a codeplug is open, the main menu bar provides access to:

### `File`
- **Open...** (`Ctrl+O`)
- **Save** (`Ctrl+S`)
- **Save As...**
- **Read Device...** (`Ctrl+R`)
- **Write Device...** (`Ctrl+W`)
- **Import** &rarr; From Applications...
- **Export** &rarr; To Applications...
- **Print Choices** &rarr; Print Preview, Print (`Ctrl+P`), Custom Print (`Ctrl+T`), Advanced Print
- **Exit**

### `Edit`
- **Undo** (`Ctrl+Z`), Cut, Copy, Paste, Find (`Ctrl+F`)

### `View`
- **Toolbar** &rarr; Standard, Utilities, Macro
- **Status Bar**
- **Tree View...**
- **Invalid Fields...**
- **Modification Log...**
- **Options...**

---

## 2. `Feature` Menu (Resource 1030 — Core Configuration Engine)

```
[+] Feature
    ├── Radio Information
    │
    ├── [+] Radio Configuration
    │   ├── Radio Wide
    │   ├── Display / Menu
    │   │
    │   ├── [+] Controls
    │   │   ├── Buttons               <-- Physical Buttons Dialog
    │   │   ├── Switches              <-- Top Toggle & Rotary Knobs
    │   │   └── Hand Held Control Head
    │   │
    │   ├── [+] Phone
    │   │   ├── Phone Configuration
    │   │   ├── DTMF Codes
    │   │   └── Phone Number
    │   │
    │   ├── [+] Secure
    │   │   ├── Secure Configuration   <-- Hardware / Software Encryption Engine
    │   │   └── Secure Multikey List   <-- Key & CKR Tables
    │   │
    │   ├── NAT
    │   ├── Data User List
    │   ├── Quick Text Message
    │   └── Clock Shifts (DSP, Host, Secure)
    │
    ├── [+] Conventional
    │   ├── Conventional Configuration
    │   ├── [+] MPL (Configuration, Entry)
    │   ├── Conventional Personality   <-- RX/TX Freqs, Strapping, Squelch
    │   ├── [+] ASTRO Systems (Config, System, Call List, Talkgroup List)
    │   ├── [+] MDC (Call List, Repeater ID List, System)
    │   ├── [+] Quik-Call II (Call List, System)
    │   ├── Message Alias List
    │   ├── Status Alias List
    │   ├── [+] Singletone (Freq List, System)
    │   └── [+] DTMF (Call List, System)
    │
    ├── [+] Trunking
    │   ├── Trunking Configuration
    │   ├── Trunking System
    │   ├── Trunking Personality
    │   └── Call Lists (ASTRO 25 & Type II)
    │
    ├── [+] Scan
    │   ├── Scan Configuration
    │   └── Scan List
    │
    └── Zone Channel Assignment        <-- 16 Channels per Zone Mapping
```

---

## 3. `Tools` & `Depot` Menu (Resource 524)

```
[+] Tools
    ├── [+] Depot
    │   ├── Create Codeplug
    │   ├── Read Codeplug
    │   ├── Update Codeplug
    │   ├── Write Codeplug
    │   ├── CBI Program
    │   ├── Program Auth Code
    │   ├── Flash Radio
    │   ├── Upgrade UCM
    │   ├── Upgrade Tuning Partition
    │   └── Upgrade Codeplug Model Number
    │
    ├── User Settings
    ├── [+] System Keys (Advanced Keys, Software Keys, Report)
    ├── [+] Cloning (Clone Radio, Clone Wizard, Clone Express)
    ├── [+] FLASHport (Read Radio Config, Read FLASHkey, Upgrade Radio)
    ├── [+] Password (Read/Write Password)
    ├── Frequency Picklists / Channel Picklist
    └── [+] Voice Files (Compression, Report, Memory Usage)
```

---

## 4. `Debug_Only` Menu (Resource 520 — Low-Level Database Access)

```
[+] Debug_Only
    ├── Show DB
    ├── Blast Radio
    ├── [+] Features DB
    │   ├── [+] Radio Config
    │   │   ├── Radio Wide DB
    │   │   ├── Display & Menus DB
    │   │   ├── VIP/HW Lab Btn DB        <-- Direct Hardware Lab Button DB
    │   │   └── Cntrl Head RecSet/DEK DB
    │   ├── [+] Conventional (Conv Config DB, Conv Pers DB, MPL List DB)
    │   ├── [+] Secure (Secure Config DB, Hardware Multikey DB, Software Key Entry DB)
    │   └── [+] Scan & Zn Chan (Scan Config DB, Scan List DB, Zn/Chan DB)
```

---

## 5. Physical Buttons Dialog Layout (from `PatPortDepot.exe`)

The **Buttons** dialog (`Feature -> Controls -> Buttons`) displays side-by-side columns:

```
+-------------------------------------------------------------------------------+
|  Buttons Configuration                                                        |
+-------------------------------------------------------------------------------+
|                      |  Conventional Option       |  Trunking Option          |
+----------------------+----------------------------+---------------------------+
| Top Button (Orange)  |  [ Dropdown Selection ]    |  [ Dropdown Selection ]   |
| Top Side (Purple)    |  [ Dropdown Selection ]    |  [ Dropdown Selection ]   |
| Middle Side (1-Dot)  |  [ Dropdown Selection ]    |  [ Dropdown Selection ]   |
| Bottom Side (2-Dot)  |  [ Dropdown Selection ]    |  [ Dropdown Selection ]   |
| Data Button          |  [ Dropdown Selection ]    |  [ Dropdown Selection ]   |
+-------------------------------------------------------------------------------+
```
