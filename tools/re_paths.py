#!/usr/bin/env python3
"""Resolve reverse-engineering target binaries without hardcoding a machine path.

Shared by every agent (Claude Code, Gemini CLI, Antigravity) and every machine.
Resolution order for the ROOT that holds the ASTRO25 CPS binaries:

  1. $OPENASTRO_RE_ROOT (env var)                      -- authoritative, per machine
  2. re_sources.local.json next to re_sources.json     -- {"root": "<abs path>"} (gitignored)
  3. first existing entry in re_sources.json "fallback_roots" (expanduser)

Logical binary names ("patport", "bytedata10", "nextgen10") map to paths relative
to that root via re_sources.json. These are untrusted vendor binaries: pass the
resolved path to the RE tool as an argument, never execute them.

CLI:
    python tools/re_paths.py                 # print resolved root + every binary
    python tools/re_paths.py patport         # print one resolved path (exit 1 if missing)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # repo root
CONFIG = HERE / "re_sources.json"
LOCAL = HERE / "re_sources.local.json"


def _load_config() -> dict:
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_root(cfg: dict | None = None) -> Path | None:
    """Return the first ROOT that exists, or None if nothing resolves."""
    cfg = cfg or _load_config()

    env = os.environ.get(cfg.get("env_var", "OPENASTRO_RE_ROOT"))
    if env:
        p = Path(os.path.expanduser(env))
        if p.exists():
            return p

    if LOCAL.exists():
        try:
            with open(LOCAL, "r", encoding="utf-8") as f:
                root = json.load(f).get("root")
            if root:
                p = Path(os.path.expanduser(root))
                if p.exists():
                    return p
        except (OSError, ValueError):
            pass

    for cand in cfg.get("fallback_roots", []):
        p = Path(os.path.expanduser(cand))
        if p.exists():
            return p
    return None


def get_binary(name: str, cfg: dict | None = None) -> Path | None:
    """Resolve one logical binary name to an existing path, or None."""
    cfg = cfg or _load_config()
    rel = cfg.get("binaries", {}).get(name)
    if rel is None:
        raise KeyError(f"unknown RE binary '{name}'; known: {list(cfg.get('binaries', {}))}")
    root = resolve_root(cfg)
    if root is None:
        return None
    p = root / rel
    return p if p.exists() else None


def _main(argv: list[str]) -> int:
    cfg = _load_config()
    root = resolve_root(cfg)
    if argv:
        name = argv[0]
        p = get_binary(name, cfg)
        if p is None:
            print(f"[-] '{name}' not resolved (root={root})", file=sys.stderr)
            return 1
        print(str(p))
        return 0

    print(f"RE root: {root if root else '(UNRESOLVED - set OPENASTRO_RE_ROOT)'}")
    for name in cfg.get("binaries", {}):
        p = get_binary(name, cfg)
        print(f"  {name:12s} {'OK  ' if p else 'MISS'} {p if p else ''}")
    return 0 if root else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
