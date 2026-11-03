"""Generate all README visual assets, data tables, and provenance manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from tools.readme_results.aggregate_baselines import (  # noqa: E402
    load_canonical_baseline_summary,
)
from tools.readme_results.aggregate_models import (  # noqa: E402
    aggregate_model_episodes,
)
from tools.readme_results.generate_svgs import (  # noqa: E402
    generate_architecture_svg,
    generate_baseline_comparison_svg,
    generate_environment_matrix_svg,
    generate_frontier_model_scores_svg,
    generate_reliability_svg,
    generate_scoring_rubric_svg,
    generate_task_success_svg,
)
from tools.readme_results.generate_tables import (  # noqa: E402
    generate_baseline_table,
    generate_environment_matrix_table,
    generate_frontier_model_table,
    generate_scoring_rubric_table,
)
from tools.readme_results.load_results import (  # noqa: E402
    calculate_sha256,
    load_raw_artifact,
)
from tools.readme_results.validate_results import normalize_record  # noqa: E402


def generate_all_assets() -> dict[str, Any]:
    """Execute complete asset and data generation workflow."""
    root_dir = Path(__file__).resolve().parent.parent
    assets_dir = root_dir / "assets" / "readme"
    docs_dir = root_dir / "docs" / "readme_overhaul"
    assets_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load artifacts
    finals_path = root_dir / "results" / "finals_full.json"
    muse_path = root_dir / "results" / "muse_spark_open_10env_benchmark.json"
    baseline_path = root_dir / "results" / "baselines" / "baseline_v050_canonical_300runs.json"

    manifest_artifacts: dict[str, Any] = {}

    runs_finals, sha_finals = load_raw_artifact(finals_path)
    manifest_artifacts["finals_full"] = {
        "path": "results/finals_full.json",
        "sha256": sha_finals,
        "runs": len(runs_finals),
    }

    runs_muse, sha_muse = load_raw_artifact(muse_path)
    manifest_artifacts["muse_spark_open_1026"] = {
        "path": "results/muse_spark_open_10env_benchmark.json",
        "sha256": sha_muse,
        "runs": len(runs_muse),
    }

    manifest_artifacts["baseline_canonical_300"] = {
        "path": "results/baselines/baseline_v050_canonical_300runs.json",
        "sha256": calculate_sha256(baseline_path),
        "runs": 300,
    }

    # Group runs by model
    all_runs = runs_finals + runs_muse
    by_model: dict[str, list[Any]] = {}
    for r in all_runs:
        m = r.get("model", "unknown")
        by_model.setdefault(m, []).append(normalize_record(r))

    models_metrics = [aggregate_model_episodes(m, recs) for m, recs in sorted(by_model.items())]

    baselines, base_meta = load_canonical_baseline_summary(baseline_path)

    # 2. Generate SVGs only if explicitly requested
    if "--svg" in sys.argv:
        generate_architecture_svg(assets_dir / "architecture.svg")
        generate_frontier_model_scores_svg(models_metrics, assets_dir / "frontier-model-scores.svg")
        generate_task_success_svg(models_metrics, assets_dir / "task-success.svg")
        generate_reliability_svg(models_metrics, assets_dir / "infrastructure-reliability.svg")
        generate_baseline_comparison_svg(baselines, assets_dir / "baseline-comparison.svg")
        generate_environment_matrix_svg(assets_dir / "environment-matrix.svg")
        generate_scoring_rubric_svg(assets_dir / "scoring-rubric.svg")

    # 3. Generate Markdown tables
    model_table_md = generate_frontier_model_table(models_metrics)
    baseline_table_md = generate_baseline_table(baselines)
    env_matrix_md = generate_environment_matrix_table()
    rubric_md = generate_scoring_rubric_table()

    (docs_dir / "model_table.md").write_text(model_table_md, encoding="utf-8")
    (docs_dir / "baseline_table.md").write_text(baseline_table_md, encoding="utf-8")
    (docs_dir / "environment_matrix.md").write_text(env_matrix_md, encoding="utf-8")
    (docs_dir / "scoring_rubric.md").write_text(rubric_md, encoding="utf-8")

    # 4. Save Model Summary JSON
    summary_data = {
        "models_count": len(models_metrics),
        "models": [
            {
                "model": m.model,
                "total_episodes": m.total_episodes,
                "valid_episodes": m.valid_episodes,
                "provider_errors": m.provider_errors,
                "provider_failure_rate": m.provider_failure_rate,
                "mean_score": m.mean_score,
                "mean_ci": [m.mean_ci_low, m.mean_ci_high],
                "median_score": m.median_score,
                "task_success_count": m.task_success_count,
                "task_success_rate": m.task_success_rate,
                "wilson_ci": [m.wilson_ci_low, m.wilson_ci_high],
                "compliance_rate": m.compliance_rate,
                "score_range": [m.score_min, m.score_max],
            }
            for m in models_metrics
        ],
    }
    (docs_dir / "model_summary.json").write_text(
        json.dumps(summary_data, indent=2), encoding="utf-8"
    )

    # 5. Save Data Provenance Manifest JSON
    manifest = {
        "version": "0.5.1",
        "artifacts": manifest_artifacts,
        "production_assets": [
            "assets/readme/agent-praxis-experimental-workflow.png",
            "assets/readme/security-architecture.png",
            "assets/readme/bidirectional-environment-evaluation.png",
            "assets/readme/model-configurations-outcomes.png",
            "assets/readme/model-performance-heatmap.png",
            "assets/readme/episode-status-breakdown.png",
            "assets/readme/iconic-literary-environments-grid.png",
            "assets/readme/weighted-evaluation-rubric.png",
            "assets/readme/traceable-benchmark-workflow.png",
        ],
    }
    (docs_dir / "data_provenance_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    if "--svg" in sys.argv:
        print(f"Generated 7 SVG figures in {assets_dir}")
    print(f"Generated tables and manifests in {docs_dir}")
    return summary_data


if __name__ == "__main__":
    generate_all_assets()
