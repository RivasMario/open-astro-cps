# Key-Loader Roadmap

How the P25 key-fill side evolves — split clearly into **what this repo does now**
and **what belongs to the future from-scratch radio-building project**. Don't
pull the future scope into the current tooling.

See also: [`ENCRYPTION_MODEL.md`](ENCRYPTION_MODEL.md) (ADP vs AES, codeplug vs
keyfill), [`cleanroom_flasher/KVL_KEYFILL_BRINGUP.md`](../cleanroom_flasher/KVL_KEYFILL_BRINGUP.md),
`kfdtool.py` (adapter layer, cleanroom-flasher branch).

## Near-term — THIS repo (key Mario's own Motorola radios)

Goal: load DES/AES-256 keys into the **existing XTS 2500/5000** radios Mario
owns, using commodity KFD hardware (the Pi Pico cable / KVL clone) + open
software — no Motorola KVL. Scoped to his own radios and his own keys.

| Layer | State |
|---|---|
| USB adapter protocol (drive the Pi/clone) | **Done** — `kfdtool.py` |
| Adapter identify + self-test | **Done** — `cleanroom_flasher/kvl_probe.py` |
| P25 **Manual Rekey (MR)** / KMM keyload session | **The gap** — build against the open KFDtool source + the `KVL Mini` .NET DLLs (decompilable) |
| Key management (keysets, SLN/CKR map, algo IDs, key entry) | To build |
| Codeplug ↔ keyloader handoff (codeplug defines slots → keyloader fills them) | Designed — `ENCRYPTION_MODEL.md` |

First milestone once hardware is attached: `kvl_probe.py` identifies both
adapters → finish the MR session → test-load an ADP key, then AES-256, into one
XTS, verified on the radio. Keep it off any shared/public channel.

Why tractable: KFDtool is **open source** and already does P25 MR keyload, so this
is build-against-a-reference, not blind RE like the codeplug side.

## Future — the from-scratch radio-building project (SEPARATE, not this repo)

Vision, belonging to the future open/"sovereign" radio build (see
`inventing_sovereign_digital_radio_protocols.md`), **not** current scope:

* **OpenAstro as the native software KVL.** In a radio we build ourselves, the
  key-loader isn't an external box talking to a Motorola crypto module over a
  3-wire bus — it's a first-class part of the radio's own software/crypto stack.
  Key management, OTAR, keysets, and algorithm support become native features
  rather than something reverse-engineered onto someone else's secure module.
* That removes the whole "you still need a KVL" constraint by design: the
  constraint only exists because Motorola's crypto module demands an
  authenticated external keyfill. Our own radio defines its own (ideally
  standards-compatible) key-management path.
* Pairs with the broader sovereign-radio goals (Codec2 vocoder, custom/M17-style
  digital, Meshtastic side-car) already sketched in the docs.

**Boundary:** everything in this file is for keying **our own radios with our own
keys** — an open key-management tool, the same category as KFDtool. Not about
other systems.
