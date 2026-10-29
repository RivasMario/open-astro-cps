"""
OpenAstro Web GUI package (Epic 4.4).

A real browser-based front end for the OpenAstro library, served by a small
FastAPI backend that wraps the EXISTING offline/read-only library calls:

    * decode a .cpg into typed JSON (open_astro.parsers.cpg_decode)
    * compute an offline FLASHcode feature upgrade (open_astro.models.flashcode)
    * export a codeplug to SDR tooling (open_astro.exporters.sdr_export)
    * list decoded conventional personalities

v1 is READ-ONLY / OFFLINE-COMPUTE ONLY. There are deliberately NO radio-write
endpoints here: writing a radio is irreversible and is gated by the CLI replay
harness, not the web UI. Nothing in this package transmits to a radio.

``app`` is only importable when FastAPI is installed. Import it lazily so that
``import open_astro.web`` never crashes on a machine without the web deps;
``python -m open_astro.web`` prints a clean ``pip install`` hint instead.
"""

__all__ = ["get_app"]


def get_app():
    """Return the FastAPI ``app`` (imported lazily so missing deps don't crash)."""
    from .app import app
    return app
