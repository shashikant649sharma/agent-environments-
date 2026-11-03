"""Baseline policy aggregation and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.readme_results.schemas import BaselineEnvironmentMetrics


def load_canonical_baseline_summary(
    path: Path | str = "results/baselines/baseline_v050_canonical_300runs.json",
) -> tuple[dict[str, BaselineEnvironmentMetrics], dict[str, Any]]:
    """Load and aggregate canonical baseline policy ladder results across 10 environments."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Canonical baseline artifact not found: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    summary = raw.get("summary", {})

    results: dict[str, BaselineEnvironmentMetrics] = {}
    for env, vals in summary.items():
        cis = vals.get("confidence_intervals", {})
        rand_ci = cis.get("random", {})
        results[env] = BaselineEnvironmentMetrics(
            environment=env,
            noop=float(vals.get("noop", 0.0)),
            read_only=float(vals.get("read_only", 0.0)),
            random_mean=float(vals.get("random", 0.0)),
            random_ci_low=float(rand_ci.get("lower", 0.0)),
            random_ci_high=float(rand_ci.get("upper", 0.0)),
            ordinal=float(vals.get("ordinal", 0.0)),
            blind_search=float(vals.get("blind_search", 0.0)),
            oracle=float(vals.get("oracle", 1.0)),
        )

    return results, raw.get("metadata", {})
