"""Schemas and data models for benchmark results processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FailureClass(StrEnum):
    """Deterministic failure precedence hierarchy."""

    PROVIDER_ERROR = "provider_error"
    CONTEXT_OVERFLOW = "context_overflow"
    PARSE_FAILURE = "parse_failure"
    INVALID_ACTION = "invalid_action"
    TASK_FAILURE = "task_failure"
    SUCCESS = "success"


@dataclass
class EpisodeRecord:
    """Normalized representation of a single benchmark trajectory."""

    model: str
    environment: str
    seed: int
    variant: str
    score: float
    task_success: bool
    constraint_compliance: bool
    steps: int = 0
    failure_class: FailureClass = FailureClass.TASK_FAILURE
    error: str | None = None
    error_kind: str | None = None
    parse_failures: int = 0
    raw_responses: list[Any] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Valid evaluation episode (excludes infrastructure failures)."""
        return self.failure_class != FailureClass.PROVIDER_ERROR


@dataclass
class ModelMetrics:
    """Aggregated evaluation metrics for a model configuration."""

    model: str
    total_episodes: int
    valid_episodes: int
    provider_errors: int
    provider_failure_rate: float
    mean_score: float
    median_score: float
    score_min: float
    score_max: float
    task_success_count: int
    task_success_rate: float
    compliance_count: int
    compliance_rate: float
    wilson_ci_low: float
    wilson_ci_high: float
    mean_ci_low: float
    mean_ci_high: float
    per_environment: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class BaselineEnvironmentMetrics:
    """Aggregated metrics for a single environment across canonical policies."""

    environment: str
    noop: float
    read_only: float
    random_mean: float
    random_ci_low: float
    random_ci_high: float
    ordinal: float
    blind_search: float
    oracle: float
