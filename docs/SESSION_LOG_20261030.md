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

---

## UnlockSecurity wired into the live RCMP write path (Claude, 2026-10-30)

`RcmpWriteClient` (`src/open_astro/protocol/rcmp_write.py`) now routes locked-partition
writes through `UnlockSecurity`:

- New per-connection `self._unlocked` set; `_needs_unlock(part)` (true when the CPS
  `PartitionPolicy` declares the partition `ACCESS_READ_WRITE_LOCKED` and it is not yet
  unlocked this session).
- `unlock_security(part, inst)` drives `UnlockSession.perform()` over the client's own
  framed socket transport, then marks the partition unlocked.
- `_retry_if_locked(...)`: a write ACK with non-zero `0x8101` status on a RW-Locked
  partition triggers `unlock_security()` + one retry. Both `write_object` and
  `send_prebuilt` (0x0101 path — the `tools/rcmp_replay_write.py` replay funnel) use it.
- **Safety preserved:** unlock is driven by the radio's *actual* refusal, not a static
  flag, so an unlocked radio/0x80 write never attempts unlock. `UnlockSession.perform()`
  stays guarded by `WIRE_PROFILE_CONFIRMED=False`, so a locked write currently raises
  `UnlockError` instead of transmitting a guessed 0x0107 frame. No guessed frame ever
  hits a radio. `0x82` firewall unchanged.

Tests: `tests/test_e2e_flash.py` +2 — `test_locked_write_routes_through_unlock_and_is_guarded`
(guard fires on locked write), `test_locked_write_retries_after_unlock_succeeds` (refusal →
unlock → retry → readback). Full suite: **263 passed, 1 skipped, 19 subtests**.

Also this session (homelab, not repo): XTS 5000 `721CLZ0655` full codeplug CLI-dumped via
`rcmp-dump` (44 objects, 9 zones/144 ch) to `captures/DUMP_721CLZ0655_20261030_224912.json`.

## Still blocking real FLASHcode persist
- `unlock_session.WIRE_PROFILE_CONFIRMED` still False — need the confirmed 0x0107 request
  body + seed offset (one live unlock capture, or finish the `FUN_1000c01f`→`FUN_1000d523`
  trace), then record a seed/response KAT and flip the flag. The write path is ready the
  moment it is flipped.
- 43-byte `0x81:1005` license bitmask byte/bit layout still `[OPEN]` (doc §7.2) — writing
  only `0x1006` ASCII will not change firmware feature gating.
