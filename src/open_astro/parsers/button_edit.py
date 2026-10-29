"""Offline button-assignment editing for ASTRO 25 conventional codeplugs.

Patches the conventional button FUNCTION tables:
  * 0x0016:0  Conventional Short Press
  * 0x0017:0  Conventional Long Press

Each is a `CcgIshListField` array: an 8-byte header (u32 stride = 0x00000001,
u16 field-type = 0x0010, u16 count) followed by `count` one-byte function tokens,
one per physical control index.

NOTE: this supersedes the stale "0x003C:0 / 13-byte stride" note in older
roadmap/memory text. The verified tables (docs/depot_controls_analysis.md,
reconstructed from PatPortDepot.exe and confirmed on hardware via the
flash_radio_adp.py payload `2c1e2b291c1a8e`) are 0x0016:0 / 0x0017:0 with
1-byte entries. Rotary/toggle switch tables (0x0020:0 / 0x0022:0) are a
separate structure and out of scope here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TAG_BTN_SHORT = 0x0016
TAG_BTN_LONG = 0x0017
HEADER_LEN = 8  # u32 stride + u16 field-type + u16 count

# Function tokens (hex values), reverse-engineered from PatPortDepot.exe
# (0x553800-0x554000 / 0x56d670-0x56da00); see docs/depot_controls_analysis.md.
# These are the ON-WIRE byte values written into the token array (NOT the UI
# dropdown ordinals an older roadmap note listed, e.g. "Light=6").
FUNCTION_TOKENS: Dict[str, int] = {
    "unprogrammed": 0x26,
    "blank": 0x18,
    "light": 0x2c,
    "monitor": 0x2b,
    "tx-low-power": 0x29,
    "emergency": 0x48,
    "scan": 0x1e,
    "zone-up": 0x01,
    "zone-down": 0x02,
    "call-response": 0x1c,
    "cursor-right": 0x1a,
    "nuisance-delete": 0x8e,
    "scan-list-program": 0x37,
    "power-switch": 0x19,
}
TOKEN_NAMES: Dict[int, str] = {v: k for k, v in FUNCTION_TOKENS.items()}

# Physical control slug -> (index into the 0x0016/0x0017 token array, description).
BUTTON_POSITIONS: Dict[str, Tuple[int, str]] = {
    "side1": (0, "Side Button 1 (Purple)"),
    "side2": (1, "Side Button 2 (1-Dot)"),
    "side3": (2, "Side Button 3 (2-Dot)"),
    "orange": (3, "Top Orange/Red Button"),
    "front-left": (4, "Front Keypad Left Arrow"),
    "front-right": (5, "Front Keypad Right Arrow"),
    "front-select": (6, "Front Keypad Select / Home"),
}
BUTTON_ALIASES = {"top": "orange", "purple": "side1", "red": "orange"}

# Remapping the purple side button is suppressed by the LCD controller on
# Model III radios (hardwired to the display backlight) -- warn, don't block.
BACKLIGHT_SUPPRESSED = {"side1"}


class ButtonPatchError(Exception):
    pass


def resolve_function(name_or_value: str) -> int:
    """Map a function name ('monitor') or hex byte ('0x2b' / '2b') to a token int."""
    key = str(name_or_value).strip().lower()
    if key in FUNCTION_TOKENS:
        return FUNCTION_TOKENS[key]
    try:
        val = int(key, 16) if (key.startswith("0x") or any(c in "abcdef" for c in key)) else int(key, 0)
    except ValueError:
        raise ButtonPatchError(
            f"unknown function '{name_or_value}' (use a name like 'monitor' or a hex byte like 0x2b)")
    if not (0 <= val <= 0xFF):
        raise ButtonPatchError(f"function token 0x{val:x} out of byte range")
    return val


def resolve_position(slug: str) -> Tuple[str, int, str]:
    """Return (canonical_slug, index, description) for a button position slug/alias."""
    key = str(slug).strip().lower()
    key = BUTTON_ALIASES.get(key, key)
    if key not in BUTTON_POSITIONS:
        raise ButtonPatchError(f"unknown button '{slug}' (see --list-buttons)")
    idx, desc = BUTTON_POSITIONS[key]
    return key, idx, desc


def function_label(token: int) -> str:
    name = TOKEN_NAMES.get(token)
    return f"{name} (0x{token:02x})" if name else f"0x{token:02x} (unknown)"


class ButtonPatcher:
    """Patch conventional button function tables (0x0016 / 0x0017) in object lists."""

    def __init__(self, objects: List[Dict[str, Any]]):
        # objects: list of dicts with keys tag, instance, partition, payload(bytes)
        self.objects = [dict(o) for o in objects]
        self._original_objects = [
            {
                **o,
                "payload": bytes(o["payload"]) if isinstance(o.get("payload"), (bytes, bytearray)) else o.get("payload")
            }
            for o in objects
        ]

    @classmethod
    def from_file(cls, path: str) -> "ButtonPatcher":
        """Load codeplug objects from a .cpg file or structural JSON dump."""
        import json
        import os
        from .cpg_parser import CpgParser

        if not os.path.exists(path):
            raise ButtonPatchError(f"file not found: {path}")

        if path.lower().endswith(".cpg"):
            parser = CpgParser(path)
            try:
                objs = parser.objects()
            finally:
                parser.close()
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            objs = data.get("objects", data)
            if not isinstance(objs, list):
                raise ButtonPatchError("invalid JSON dump: expected 'objects' list")
            for o in objs:
                if isinstance(o.get("payload"), str):
                    o["payload"] = bytes.fromhex(o["payload"])

        return cls(objs)

    def save_json(self, path: str) -> None:
        """Save patched objects to a structural JSON file."""
        import json
        serializable = []
        for o in self.objects:
            entry = dict(o)
            if isinstance(entry.get("payload"), (bytes, bytearray)):
                entry["payload"] = entry["payload"].hex()
            serializable.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"objects": serializable}, f, indent=2)

    def _find(self, tag: int, instance: int = 0) -> Optional[Dict[str, Any]]:
        for o in self.objects:
            if o.get("tag") == tag and o.get("instance", 0) == instance:
                return o
        return None

    def button_count(self) -> int:
        obj = self._find(TAG_BTN_SHORT) or self._find(TAG_BTN_LONG)
        if not obj:
            raise ButtonPatchError("no button table (0x0016/0x0017) present in objects")
        pl = obj["payload"]
        if len(pl) < HEADER_LEN:
            raise ButtonPatchError("button table too short to hold a header")
        return int.from_bytes(pl[6:8], "big")

    def current_tokens(self, press: str = "short") -> List[int]:
        tag = TAG_BTN_SHORT if press == "short" else TAG_BTN_LONG
        obj = self._find(tag)
        if not obj:
            return []
        pl = obj["payload"]
        count = int.from_bytes(pl[6:8], "big")
        return list(pl[HEADER_LEN:HEADER_LEN + count])

    def set_button(self, position: str, function: str, long_press: bool = False) -> List[str]:
        """Set button assignment for short or long press."""
        press = "long" if long_press else "short"
        return self.patch_button(position, function, press=press)

    def patch_button(self, position: str, function: str, press: str = "short") -> List[str]:
        """Set `position` to `function` for short/long/both press. Returns note strings."""
        slug, idx, desc = resolve_position(position)
        token = resolve_function(function)
        presses = ["short", "long"] if press == "both" else [press]
        if any(p not in ("short", "long") for p in presses):
            raise ButtonPatchError("press must be 'short', 'long', or 'both'")

        notes: List[str] = []
        touched = False
        for p in presses:
            tag = TAG_BTN_SHORT if p == "short" else TAG_BTN_LONG
            obj = self._find(tag)
            if not obj:
                notes.append(f"no {p}-press table (0x{tag:04x}) present; skipped")
                continue
            pl = bytearray(obj["payload"])
            count = int.from_bytes(pl[6:8], "big")
            if idx >= count:
                raise ButtonPatchError(
                    f"{slug} is index {idx} but the {p}-press table has only {count} entries")
            pl[HEADER_LEN + idx] = token
            obj["payload"] = bytes(pl)
            touched = True
        if not touched:
            raise ButtonPatchError("no button table was present to patch")
        if slug in BACKLIGHT_SUPPRESSED:
            notes.append(
                f"{desc} is hardwired to the LCD backlight on Model III radios; the LCD "
                f"controller may suppress this remap (software change still written).")
        return notes

    def generate_edits(self, original_objects: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Emit `--edit PART:TAG:INST:HEX` strings for objects that changed."""
        if original_objects is None:
            original_objects = getattr(self, "_original_objects", [])
        orig = {(o.get("tag"), o.get("instance", 0)): o.get("payload") for o in original_objects}
        edits: List[str] = []
        for o in self.objects:
            key = (o.get("tag"), o.get("instance", 0))
            if key[0] not in (TAG_BTN_SHORT, TAG_BTN_LONG):
                continue
            if orig.get(key) is not None and orig[key] != o.get("payload"):
                part = o.get("partition", 0x80)
                edits.append(f"{part:02x}:{o['tag']:04x}:{o.get('instance', 0):x}:{o['payload'].hex()}")
        return edits
