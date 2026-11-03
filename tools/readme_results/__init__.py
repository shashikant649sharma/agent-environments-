"""Agent Praxis README Results Extraction and Statistical Aggregation Pipeline."""

from __future__ import annotations

from tools.readme_results.aggregate_baselines import load_canonical_baseline_summary
from tools.readme_results.aggregate_models import aggregate_model_episodes
from tools.readme_results.generate_tables import (
    generate_baseline_table,
    generate_environment_matrix_table,
    generate_frontier_model_table,
    generate_scoring_rubric_table,
)
from tools.readme_results.load_results import calculate_sha256, load_raw_artifact
from tools.readme_results.schemas import (
    BaselineEnvironmentMetrics,
    EpisodeRecord,
    FailureClass,
    ModelMetrics,
)
from tools.readme_results.validate_results import (
    classify_run_failure,
    normalize_record,
    partition_valid_observations,
)

__all__ = [
    "BaselineEnvironmentMetrics",
    "EpisodeRecord",
    "FailureClass",
    "ModelMetrics",
    "aggregate_model_episodes",
    "calculate_sha256",
    "classify_run_failure",
    "generate_baseline_table",
    "generate_environment_matrix_table",
    "generate_frontier_model_table",
    "generate_scoring_rubric_table",
    "load_canonical_baseline_summary",
    "load_raw_artifact",
    "normalize_record",
    "partition_valid_observations",
]
