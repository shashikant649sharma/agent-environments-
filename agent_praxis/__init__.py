"""Agent Praxis.

Python package root for Agent Praxis.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

__version__ = "0.5.1"


def load_praxis_env() -> None:
    """Robustly discover and load .env from current working dir or workspace roots."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path("D:/Shashi/agent-praxis/.env"),
    ]
    seen_keys: set[str] = set()
    for cand in candidates:
        if cand.is_file():
            with contextlib.suppress(Exception), open(cand, encoding="utf-8") as _env_f:
                for line in _env_f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in seen_keys:
                            seen_keys.add(k)
                            if not os.environ.get(k):
                                os.environ[k] = v


load_praxis_env()
