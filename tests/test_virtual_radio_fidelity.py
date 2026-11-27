"""Byte-fidelity regression: replay a complete genuine CPS read against our
VirtualRadioServer and assert the responses match the captured radio.

Ground truth: ``captures/cps_20261023_082619_decoded.json`` is a full genuine
Motorola ASTRO 25 Portable CPS read of radio 407CHT0214 (227 distinct
partition-0x80 objects). ``backups/407CHT0214.cpg`` is that radio's codeplug.
Feeding each genuine request record to ``VirtualRadioServer.process_record``
must reproduce the radio's reply for every codeplug object, which is what lets
the virtual radio stand in for real hardware when capturing CPS behaviour.

Two protocol invariants this pins (both discovered by diffing against this
capture; without them genuine CPS aborts the read, "Read Radio Failed"):

* 0x8100 read-ack records are capped at a 248-byte RCMP MTU; larger objects are
  truncated mid-payload while the length field still advertises the full size.
* An absent object/instance (including instance 0 of a missing object) is
  answered with the 14-byte 0x81 not-found NAK, never a status-0 empty success.

Object reads must match exactly. The handful of identity/metadata records whose
values legitimately differ between a saved ``.cpg`` and a live radio are
excluded and listed in ``KNOWN_METADATA_DIFFS``.
"""
import json
import os

import pytest

from tools.virtual_radio import load_codeplug, VirtualRadioServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(REPO, "captures", "cps_20261023_082619_decoded.json")
CPG = os.path.join(REPO, "backups", "407CHT0214.cpg")

# Records whose payload legitimately differs between a saved codeplug file and
# the originating radio, so they are not fidelity failures:
#   0x0047 - last-programmed timestamp (the .cpg carries its own save time)
#   0x000F - host/DSP version & capability strings (identity, radio-specific)
#   0x0011 - electronic serial / unit id binary blob (identity, radio-specific)
KNOWN_METADATA_DIFFS = {0x0047, 0x000F, 0x0011}


def _records(side):
    return [bytes.fromhex(s["rcmp_hex"])[2:]  # strip the 2-byte length prefix
            for s in side["rcmp_segments"] if s.get("rcmp_hex")]


def _resp_ident(rec):
    """Identity used to pair a response with its request (echoed opcode/obj)."""
    if len(rec) < 2:
        return ("short", rec.hex())
    base = ((rec[0] << 8) | rec[1]) & 0x7FFF
    if base in (0x0100, 0x0001) and len(rec) >= 8:
        return (base, rec[3], rec[4:6].hex(), rec[6:8].hex())
    return (base,)


def _req_ident(rec):
    if len(rec) < 2:
        return ("short", rec.hex())
    base = (rec[0] << 8) | rec[1]
    if base in (0x0100, 0x0001) and len(rec) >= 8:
        return (base, rec[2], rec[3:5].hex(), rec[5:7].hex())
    return (base,)


@pytest.mark.skipif(not (os.path.exists(CAP) and os.path.exists(CPG)),
                    reason="genuine capture / codeplug not present")
def test_genuine_407_read_is_byte_faithful():
    cpg = load_codeplug(CPG, serial_override="407CHT0214")
    srv = VirtualRadioServer(
        cpg,
        firmware_version="R20.50.07",
        codeplug_version="R19.50.01",
        model_override="H46KDF9PW6BN",
        radio_name="XTS 2500",
        uuid_override="d105add323864e539b513a65076458d3",
    )
    data = json.load(open(CAP))
    reqs = _records(data["OUT host->radio"])
    resps = _records(data["IN radio->host"])

    cursor = 0
    object_reads = exact = 0
    failures = []
    for req in reqs:
        want = _req_ident(req)  # the matching response carries this same identity
        got = srv.process_record(req, {"unlocked": False, "challenge_pending": False})
        # locate the matching genuine response
        genuine = None
        j = cursor
        while j < len(resps):
            rid = _resp_ident(resps[j])
            if rid == want or (len(want) == 1 and rid[0] == want[0]):
                genuine, cursor = resps[j], j + 1
                break
            j += 1
        if genuine is None:
            continue
        rid = _req_ident(req)
        is_obj_read = len(rid) == 4 and rid[0] == 0x0100 and rid[1] == 0x80
        obj = int(rid[2], 16) if is_obj_read else None
        if is_obj_read and obj not in KNOWN_METADATA_DIFFS:
            object_reads += 1
            if got == genuine:
                exact += 1
            else:
                failures.append((rid, len(genuine), len(got)))

    # The capture holds 227 distinct 0x80 objects (0x0047 excluded as metadata);
    # sanity-check that the bulk were replayed and paired, then require every one
    # of them to match the radio byte-for-byte.
    assert object_reads >= 215, f"too few object reads replayed: {object_reads}"
    assert not failures, f"{len(failures)} object reads diverged from genuine: {failures[:5]}"
    assert exact == object_reads
