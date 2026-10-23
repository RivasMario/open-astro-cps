"""Assemble an RCMP write session from a source codeplug.

Until now a live write was a verbatim replay of a captured CPS session (plus
per-object `--edit` patches). This module builds the write records from a source
`.cpg` instead, so writing no longer depends on having a matching capture of the
exact codeplug: every object stored in the `.cpg` is re-emitted as a verified
RCMP write record.

What is VERIFIED here (offline, against the real `.cpg` backups):
  * each `.cpg` stream is self-describing -- it decrypts to
    `<tag><instance><len><payload><crc>` where `tag` is the live RCMP object id
    and `instance` the RCMP instance (cross-checked: the tags match the object
    ids in the live read captures),
  * `rcmp.build_write(part, tag, payload, inst)` reproduces that object's CRC
    byte-for-byte -- the write-record encoder and the `.cpg` stream CRC agree,
  * partition 0x82 (tuning/soft-pots) is refused, and only an explicit set of
    partitions is ever emitted.

What is NOT verified and is deliberately NOT synthesized here: the session
framing records around the writes -- the 0103 "prepare" records (and 0104 /
0107 seen in captures), whose field layout (e.g. the 0e0b / 01f4 size/count
fields) cannot be derived without a captured write session. `build_session`
requires those to be supplied verbatim from a capture; it will not invent them.

So this is the offline-verifiable core of the write-session assembler. The
remaining piece (the prepare/commit framing) needs the one captured write
session that currently lives only on the home PC -- see
docs/HANDOFF_RCMP_LIVE.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import rcmp
from ..parsers.cpg_parser import CpgParser

PART_CODEPLUG = 0x80   # plaintext codeplug objects
PART_RC4 = 0x81        # RC4-encrypted streams
PART_TUNING = 0x82     # soft-pot / tuning -- NEVER written (unrecoverable)

# Partitions the assembler is willing to emit writes for. 0x80/0x81 are the
# codeplug; 0x85 is seen in read captures (a small number of objects). 0x82 is
# never allowed. Anything outside this set must be opted in explicitly.
DEFAULT_ALLOWED_PARTS = frozenset({0x80, 0x81, 0x85})

PartMap = Dict[Tuple[int, int], int]   # (obj, inst) -> partition


class WriteSessionError(Exception):
    pass


@dataclass(frozen=True)
class WriteObject:
    """One object to write: its partition, id, instance, and raw payload (the
    payload WITHOUT its CRC -- build_write appends the CRC)."""
    part: int
    obj: int
    inst: int
    payload: bytes

    def record(self) -> bytes:
        """The framed RCMP 0101 write record for this object (CRC appended)."""
        return rcmp.build_write(self.part, self.obj, self.payload, self.inst)


def part_map_from_capture(rcmp_stream: bytes) -> PartMap:
    """Build an (obj, inst) -> partition map from a decoded RCMP request stream
    (reads and/or writes). Read and write records carry the same addressing, so
    a read capture is enough to learn which partition each object lives in."""
    out: PartMap = {}
    for rec in rcmp.iter_records(rcmp_stream):
        if len(rec) < 7:
            continue
        op = int.from_bytes(rec[:2], "big")
        if op in (rcmp.OP_READ, rcmp.OP_WRITE):
            part = rec[2]
            obj = int.from_bytes(rec[3:5], "big")
            inst = int.from_bytes(rec[5:7], "big")
            out[(obj, inst)] = part
    return out


class CpgWriteAssembler:
    """Turn a source codeplug into the ordered RCMP write records / session."""

    def __init__(self, objects: List[WriteObject], *,
                 allowed_parts=DEFAULT_ALLOWED_PARTS):
        self.objects = list(objects)
        self.allowed_parts = set(allowed_parts)

    @classmethod
    def from_cpg(cls, path: str, part_map: Optional[PartMap] = None,
                 default_part: int = PART_CODEPLUG, *, require_crc: bool = True,
                 allowed_parts=DEFAULT_ALLOWED_PARTS) -> "CpgWriteAssembler":
        """Load every object from a `.cpg`. Each object's partition comes from
        `part_map[(obj, inst)]` if supplied (e.g. from part_map_from_capture),
        else `default_part`. With `require_crc` (default) a stream that fails its
        CRC aborts assembly -- we never write a corrupt object."""
        parser = CpgParser(path)
        objs: List[WriteObject] = []
        try:
            for o in parser.objects():
                if require_crc and not o["crc_ok"]:
                    raise WriteSessionError(
                        f"{o['name']} (tag {o['tag']}) failed its CRC; refusing "
                        f"to assemble a write from a corrupt object")
                key = (o["tag"], o["instance"])
                part = (part_map or {}).get(key, default_part)
                objs.append(WriteObject(part, o["tag"], o["instance"], o["payload"]))
        finally:
            parser.close()
        return cls(objs, allowed_parts=allowed_parts)

    def _guard(self) -> None:
        for w in self.objects:
            if w.part == PART_TUNING:
                raise WriteSessionError(
                    f"object {w.obj}/{w.inst} targets partition 0x82 "
                    f"(tuning/soft-pots): refusing -- unrecoverable if corrupted")
            if w.part not in self.allowed_parts:
                raise WriteSessionError(
                    f"object {w.obj}/{w.inst} targets unapproved partition "
                    f"0x{w.part:02x}; add it to allowed_parts to permit it")

    def write_records(self) -> List[bytes]:
        """The framed 0101 write records, one per object, partition-guarded."""
        self._guard()
        return [w.record() for w in self.objects]

    def build_session(self, prepare_records: Optional[List[bytes]] = None, *,
                      allow_without_prepare: bool = False) -> bytes:
        """Assemble the full write-session byte stream:

            0106 00 (open) -> [prepare_records verbatim] -> 0101 writes
                           -> 0106 01 (commit)

        `prepare_records` (framed 0103/0104/0107 records) MUST come verbatim from
        a captured write session -- their layout is unverified and this method
        will not synthesize them. Omitting them raises unless
        `allow_without_prepare=True`, which produces a structurally-incomplete
        stream suitable for OFFLINE assembly/validation only (never to drive a
        radio)."""
        self._guard()
        if prepare_records is None and not allow_without_prepare:
            raise WriteSessionError(
                "no prepare records supplied: the 0103/0104 prepare layout is "
                "unverified without a captured write session. Pass captured "
                "prepare_records, or allow_without_prepare=True for offline "
                "assembly only.")
        out = bytearray()
        out += rcmp.frame(bytes([0x01, 0x06, 0x00]))      # session open
        for pr in (prepare_records or []):
            out += pr
        for w in self.objects:
            out += w.record()
        out += rcmp.frame(bytes([0x01, 0x06, 0x01]))      # commit / finalize
        return bytes(out)
