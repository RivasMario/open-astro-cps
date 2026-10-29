#!/usr/bin/env python3
"""Start noVNC websockify using os.fork() context (Python 3.14 + WSL1 fix)."""
import multiprocessing
import os
import sys

from websockify import websockifyserver
from websockify.websocketproxy import websockify_init

_fork_ctx = multiprocessing.get_context("fork")
websockifyserver.multiprocessing.Process = _fork_ctx.Process
websockifyserver.multiprocessing.active_children = _fork_ctx.active_children

os.chdir("/usr/share/novnc")
sys.argv = ["websockify", "--web=/usr/share/novnc/", "6080", "localhost:5900"]
websockify_init()
