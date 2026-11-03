"""Artifact loading and cryptographic hash calculation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def calculate_sha256(path: Path | str) -> str:
    """Compute normalized SHA-256 hash of an artifact."""
    p = Path(path)
    data = p.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_raw_artifact(path: Path | str) -> tuple[list[dict[str, Any]], str]:
    """Load runs from arbitrary JSON artifact structure and return (runs, sha256).

    Handles:
    - Flat list of runs: [run1, run2, ...]
    - Nested document: {"runs": [run1, run2, ...]}
    - Multi-environment summary list: [{"model": "...", "runs": [...]}, ...]
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Artifact not found: {p}")

    digest = calculate_sha256(p)
    raw = json.loads(p.read_text(encoding="utf-8"))

    runs: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            if "runs" in item and isinstance(item["runs"], list):
                # Inherit top-level model/environment/variant if missing in run
                parent_model = item.get("model")
                parent_env = item.get("environment")
                parent_var = item.get("variant", "standard")
                for r in item["runs"]:
                    if isinstance(r, dict):
                        r_copy = dict(r)
                        if "model" not in r_copy and parent_model:
                            r_copy["model"] = parent_model
                        if "environment" not in r_copy and parent_env:
                            r_copy["environment"] = parent_env
                        if "variant" not in r_copy:
                            r_copy["variant"] = parent_var
                        runs.append(r_copy)
            else:
                runs.append(item)
    elif isinstance(raw, dict):
        if "runs" in raw and isinstance(raw["runs"], list):
            for r in raw["runs"]:
                if isinstance(r, dict):
                    runs.append(r)
        else:
            runs.append(raw)

    return runs, digest
