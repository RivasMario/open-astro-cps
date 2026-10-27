"""
Launch the OpenAstro Web GUI:

    python -m open_astro.web                 # 127.0.0.1:8080
    python -m open_astro.web --port 9000
    python -m open_astro.web --host 0.0.0.0 --port 8080

Binds to loopback by default -- this is an offline, read-only tool with no
auth; do not expose it to a network you do not trust. If FastAPI/uvicorn are
not installed, print a clear pip hint and exit 1 (no traceback).
"""
from __future__ import annotations

import argparse
import sys


def _missing_deps_hint(exc: ImportError) -> int:
    sys.stderr.write(
        "OpenAstro Web GUI needs FastAPI and uvicorn, which are not installed.\n"
        f"  (import failed: {exc})\n\n"
        "Install them (user scope, no sudo):\n"
        "  pip install --user fastapi uvicorn\n\n"
        "Then re-run:  python -m open_astro.web\n"
    )
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m open_astro.web",
        description="Serve the OpenAstro Web GUI (offline / read-only; no radio writes).",
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind host (default: 127.0.0.1 / loopback)")
    parser.add_argument("--port", type=int, default=8080,
                        help="Bind port (default: 8080)")
    parser.add_argument("--reload", action="store_true",
                        help="Enable auto-reload (development)")
    args = parser.parse_args(argv)

    # Import heavy/optional deps only after args parse so --help always works.
    try:
        import uvicorn  # noqa: F401
        from .app import app
    except ImportError as exc:
        return _missing_deps_hint(exc)

    sys.stderr.write(
        f"OpenAstro Web GUI (read-only) -> http://{args.host}:{args.port}\n"
    )
    if args.reload:
        uvicorn.run("open_astro.web.app:app", host=args.host, port=args.port, reload=True)
    else:
        uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
