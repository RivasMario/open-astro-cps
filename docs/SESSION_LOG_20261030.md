# Session Log — 2026-10-30 (Claude, Opus 4.8, Fedora laptop)

Branch: `feat/0107-unlocksecurity-reverse`. Radio 4 (`721CLZ0655`, XTS 5000) attached on `/dev/ttyACM0`.

## Baseline
- `open-astro probe` OK: link up, Host/DSP R15.00.00, `SECURE: R000000`, model `H18UCF9PW6AN`.
- `pytest`: **261 passed, 1 skipped**.
- Fetched origin: `master` advanced `2892c45..daeb805`; new remote branch
  `fix/cps-cli-and-capture-validators`. Working branch tip was `2277909`.

## Work — 0x0107 UnlockSecurity wire frame
Picked up the one open unknown: how the `UnlockSecurity` request is framed on the wire (msg tag
`0x2011` → wire opcode/body, seed offset in reply).

Resolved the serialization path via Ghidra (headless, `ng` project, no re-import):
- Located the **`CRcmpBundler` vtable** (unsymbolized) by scanning `.rdata` for the pointer to
  `FUN_1000cce7` → base **`0x10025cc0`**, `UnlockSecurity` at slot `+0xd0`.
- Resolved the three slots `FUN_1000cce7` drives: `+0x60` build = `FUN_1000c01f`
  (`CRcmpBundler::Open` dispatcher), `+0x5c` send = `FUN_1000a610`, `+0xb0` reply = `FUN_1000f978`.
- Confirmed framing: `BundleTCP` (`FUN_100187b6`) = 2-byte BE length prefix; `SendRequest`
  (`FUN_10018123`) transmits an already-built buffer in `0x410` chunks, WRITE length at bytes 7–8 —
  both match `rcmp.py`.
- `FUN_1000c01f` `cmd==0xd` branch `memcpy`s a 0x20 (32) byte block and sets `_DAT_1002f7fe=0x1f43`.

New artifacts: `docs/re/nextgen10_bundler_vtable.txt`, `docs/re/nextgen10_unlock_slots_decomp.txt`;
write-up updated in `docs/re/RE_0107_UNLOCKSECURITY.md`. New Ghidra scripts in `~/re/ghidra_scripts`:
`FindBundlerVt.java`, `DumpBundlerVt.java`.

## Correction (static trace, option 1)
Decompiled the slot targets. The `0x10025cc0` table is the OLE-dispatch table, NOT the object
`FUN_1000cce7` indexes — slot mapping disproven: `+0x60`=`FUN_1000c01f` (`Open` dispatcher),
`+0x5c`=`FUN_1000a610` (`ReadIshList`), `+0xb0`=`FUN_1000f978` (`"Host"` request). `0x2011` is a
generic RCMP message-container tag (set identically by all three), not the unlock discriminator.
The real unlock opcode is a field inside the message body, not yet located. See corrected
`docs/re/RE_0107_UNLOCKSECURITY.md`.

## Stopped here (no transmit)
Did **not** transmit a guessed `UnlockSecurity` frame — `unlock_session.perform()` stays gated
(`WIRE_PROFILE_CONFIRMED = False`). Exact request body + seed offset still unconfirmed.

## Next
- Either trace `FUN_1000c01f`→`FUN_1000d523` + `DAT_1002f7xx` to byte-recover the request body, or
  capture one live unlock exchange, then fill `unlock_session.py` and flip the flag.
- Wire opcode `0x0107` is a strong inference from the verified opcode family, not byte-confirmed.
