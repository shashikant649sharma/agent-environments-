"""Model aggregation and statistical interval estimation."""

from __future__ import annotations

import math
from typing import Any

from tools.readme_results.schemas import EpisodeRecord, FailureClass, ModelMetrics


def wilson_score_interval(
    successes: int, total: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Calculate Wilson score interval for binomial proportion."""
    if total <= 0:
        return 0.0, 0.0

    z = 1.959963984540054  # 95% normal quantile
    p = successes / total
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / total) + ((z**2) / (4 * (total**2))))

    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return round(low, 4), round(high, 4)


def continuous_mean_interval(scores: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Calculate confidence interval for continuous scores using Student-t distribution approximation."""
    n = len(scores)
    if n <= 1:
        val = scores[0] if n == 1 else 0.0
        return round(val, 4), round(val, 4)

    mean_val = sum(scores) / n
    variance = sum((x - mean_val) ** 2 for x in scores) / (n - 1)
    std_err = math.sqrt(variance / n)

    # Approximate t critical values for 95%
    if n < 5:
        t_crit = 3.182
    elif n < 10:
        t_crit = 2.262
    elif n < 20:
        t_crit = 2.093
    elif n < 30:
        t_crit = 2.045
    elif n < 100:
        t_crit = 1.984
    else:
        t_crit = 1.960

    margin = t_crit * std_err
    return round(max(0.0, mean_val - margin), 4), round(min(1.0, mean_val + margin), 4)


def aggregate_model_episodes(model_name: str, records: list[EpisodeRecord]) -> ModelMetrics:
    """Aggregate records for a single model configuration using strict failure accounting."""
    total = len(records)
    provider_errors = sum(1 for r in records if r.failure_class == FailureClass.PROVIDER_ERROR)
    valid_records = [r for r in records if r.is_valid]
    valid_count = len(valid_records)

    prov_fail_rate = round(provider_errors / total, 4) if total > 0 else 0.0

    if valid_count > 0:
        scores = [r.score for r in valid_records]
        sorted_scores = sorted(scores)
        mean_s = round(sum(scores) / valid_count, 4)
        med_s = round(
            sorted_scores[valid_count // 2]
            if valid_count % 2 == 1
            else (sorted_scores[valid_count // 2 - 1] + sorted_scores[valid_count // 2]) / 2.0,
            4,
        )
        score_min = round(min(scores), 4)
        score_max = round(max(scores), 4)
        successes = sum(1 for r in valid_records if r.task_success)
        compliances = sum(1 for r in valid_records if r.constraint_compliance)
        task_succ_rate = round(successes / valid_count, 4)
        comp_rate = round(compliances / valid_count, 4)
        wilson_low, wilson_high = wilson_score_interval(successes, valid_count)
        mean_low, mean_high = continuous_mean_interval(scores)

        # Parse failure and clean-run discrimination
        pf_records = [
            r
            for r in valid_records
            if r.parse_failures > 0
            or r.failure_class == FailureClass.PARSE_FAILURE
            or "parse" in (r.error or "").lower()
        ]
        pf_count = len(pf_records)
        hard_pf_count = sum(
            1
            for r in pf_records
            if r.failure_class == FailureClass.PARSE_FAILURE or r.error_kind == "parse_failure"
        )
        clean_records = [r for r in valid_records if r not in pf_records]
        clean_count = len(clean_records)
        if clean_count > 0:
            c_scores = [r.score for r in clean_records]
            clean_mean = round(sum(c_scores) / clean_count, 4)
            clean_low, clean_high = continuous_mean_interval(c_scores)
        else:
            clean_mean = 0.0
            clean_low, clean_high = 0.0, 0.0
    else:
        mean_s = 0.0
        med_s = 0.0
        score_min = 0.0
        score_max = 0.0
        successes = 0
        compliances = 0
        task_succ_rate = 0.0
        comp_rate = 0.0
        wilson_low, wilson_high = 0.0, 0.0
        mean_low, mean_high = 0.0, 0.0
        pf_count = 0
        hard_pf_count = 0
        clean_count = 0
        clean_mean = 0.0
        clean_low, clean_high = 0.0, 0.0

    # Per-environment breakdowns
    per_env: dict[str, dict[str, Any]] = {}
    env_groups: dict[str, list[EpisodeRecord]] = {}
    for r in valid_records:
        env_groups.setdefault(r.environment, []).append(r)

    for env_id, env_runs in sorted(env_groups.items()):
        e_scores = [r.score for r in env_runs]
        e_succ = sum(1 for r in env_runs if r.task_success)
        e_comp = sum(1 for r in env_runs if r.constraint_compliance)
        e_count = len(env_runs)
        per_env[env_id] = {
            "valid_runs": e_count,
            "mean_score": round(sum(e_scores) / e_count, 4),
            "task_success_rate": round(e_succ / e_count, 4),
            "compliance_rate": round(e_comp / e_count, 4),
        }

    return ModelMetrics(
        model=model_name,
        total_episodes=total,
        valid_episodes=valid_count,
        provider_errors=provider_errors,
        provider_failure_rate=prov_fail_rate,
        mean_score=mean_s,
        median_score=med_s,
        score_min=score_min,
        score_max=score_max,
        task_success_count=successes,
        task_success_rate=task_succ_rate,
        compliance_count=compliances,
        compliance_rate=comp_rate,
        wilson_ci_low=wilson_low,
        wilson_ci_high=wilson_high,
        mean_ci_low=mean_low,
        mean_ci_high=mean_high,
        parse_fail_episodes=pf_count,
        hard_parse_fail_episodes=hard_pf_count,
        clean_episodes=clean_count,
        clean_mean_score=clean_mean,
        clean_mean_ci_low=clean_low,
        clean_mean_ci_high=clean_high,
        per_environment=per_env,
    )
