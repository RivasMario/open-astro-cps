# Encryption Model: ADP vs AES, Codeplug vs Keyfill

How P25 encryption is split across the two subsystems this project touches —
the **codeplug** (programmed over the RCMP/CPS path) and the **crypto module**
(filled over the 3-wire keyfill path). Getting this split right determines how
`rcmp_socket_transport.py` (codeplug) and `kfdtool.py` (keyfill) must cooperate.

## The two crypto classes

| | **ADP** | **DES / AES-256** |
|---|---|---|
| What it is | Motorola "Advanced Digital Privacy" — 40-bit RC4, software crypto | Hardware crypto in the secure module (DES-OFB/XL, AES-256) |
| Algorithm ID | `0xAA` | DES-OFB `0x81`, DES-XL `0x80`, AES-256 `0x84` |
| Where the key lives | **Can be stored in the codeplug** (software) | **Only in the tamper-protected key store** of the crypto module |
| How it's set | CPS / codeplug write (no KVL needed) | **Keyfill session** (KVL / KFD, 3-wire MR) |
| Strength | Weak — "privacy," not security (see note) | Strong (AES-256 is the real deal) |

## Codeplug vs keyfill — who stores what

**The codeplug never contains AES/DES key bits. It stores only references:**

* per channel/talkgroup: the **algorithm**, a **Key ID**, and a **slot / SLN /
  CKR** ("use the key in storage slot N").
* keyset / CKR definitions that map logical keys to slots.

The actual AES/DES key **bytes** live in the crypto module's isolated key store,
loaded separately via a keyfill (Manual Rekey) session. ADP is the exception:
being software crypto, an ADP key *can* sit in the codeplug.

### Why the separation exists (it is a feature)

* **Separation of duties** — a tech can program channels without holding the
  keys; a crypto officer can load keys without touching the config.
* **Key isolation** — reading or cloning a codeplug must not expose the real
  keys. The crypto module takes keys in through an authenticated path and does
  not read them back out.
* **Different transport / processor** — codeplug = data interface →
  config processor; keyfill = 3-wire bus → crypto module. Separate state
  machines, not one "write."

## Tooling implication for this repo

The two sides **cooperate in order**, they do not merge:

1. **Codeplug first** (`rcmp_socket_transport.py` / CPS): define keysets, assign
   each encrypted channel its algorithm + Key ID + SLN/CKR slot. For **ADP**,
   also set the key here.
2. **Keyfill second** (`kfdtool.py` + a KVL/KFD): load the actual **DES/AES-256**
   key bytes into the SLN/CKR slots the codeplug referenced.

So "write an AES key at the same time as the codeplug" is not possible by design
— the codeplug makes the *slots*, the keyfill fills them. Only ADP blurs this,
because it is software crypto that the codeplug can carry directly.

## Note on ADP strength (factual)

ADP is a **40-bit** key RC4 stream cipher (the key is derived from the entered
passphrase). 40 bits is far below any modern security margin — ADP is widely
regarded in public security literature as **obfuscation / "privacy," not real
confidentiality**, and Motorola itself positions AES-256 as the secure option.
This is exactly why this project treats ADP (settable in-codeplug) and AES/DES
(keyfill-only, secure module) as different trust tiers. Use AES-256 for anything
that actually needs to stay private.

## APX note

Same split on APX: **APX CPS** (USB) programs the codeplug; a **KVL/KFD** loads
AES/DES keys; ADP is in-codeplug. APX uses a different accessory connector than
the XTS Hirose, so keying an APX needs the correct APX keyfill cable on the radio
end (host side unchanged). APX codeplug programming is a different protocol from
the ASTRO 25 RCMP stack and is out of scope here.
