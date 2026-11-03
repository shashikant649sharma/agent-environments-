"""Validation and deterministic failure classification hierarchy."""

from __future__ import annotations

from typing import Any

from tools.readme_results.schemas import EpisodeRecord, FailureClass


def classify_run_failure(run: dict[str, Any]) -> FailureClass:
    """Classify episode failure using strict precedence hierarchy:

    provider_error -> context_overflow -> parse_failure -> invalid_action -> task_failure -> success
    """
    error = str(run.get("error") or "").strip()
    error_kind = str(run.get("error_kind") or "").strip().lower()
    task_success = bool(run.get("task_success", False))
    score = float(run.get("score", 0.0))

    # 1. Provider infrastructure error (network, rate limit HTTP 429, authentication, timeout)
    if error_kind == "provider_error":
        return FailureClass.PROVIDER_ERROR
    if any(
        kw in error.lower()
        for kw in (
            "provider_error",
            "provider error",
            "requires baseten_api_key",
            "api key not provided",
            "rate limit",
            "connection refused",
            "remote disconnected",
            "http 429",
            "http 500",
            "http 502",
            "http 503",
        )
    ):
        return FailureClass.PROVIDER_ERROR

    # 2. Context overflow (mandatory prompt exceeds model budget)
    if error_kind == "context_overflow" or "context budget" in error.lower():
        return FailureClass.CONTEXT_OVERFLOW

    # 3. Parse failure (unparseable action response)
    if (
        error_kind == "parse_failure"
        or "parse failure" in error.lower()
        or "could not be parsed" in error.lower()
    ):
        return FailureClass.PARSE_FAILURE

    # 4. Invalid action (index out of range or illegal parameter)
    if error_kind == "invalid_action" or "invalid action" in error.lower():
        return FailureClass.INVALID_ACTION

    # 5. Success vs Task Failure
    if task_success and score >= 0.9999:
        return FailureClass.SUCCESS

    return FailureClass.TASK_FAILURE


def normalize_record(raw: dict[str, Any]) -> EpisodeRecord:
    """Validate and convert raw dict into a validated EpisodeRecord."""
    fail_cls = classify_run_failure(raw)
    return EpisodeRecord(
        model=str(raw.get("model", "unknown")),
        environment=str(raw.get("environment", "unknown")),
        seed=int(raw.get("seed", 0)),
        variant=str(raw.get("variant", "standard")),
        score=float(raw.get("score", 0.0)),
        task_success=bool(raw.get("task_success", False)),
        constraint_compliance=bool(raw.get("constraint_compliance", False)),
        steps=int(raw.get("steps", len(raw.get("path", [])))),
        failure_class=fail_cls,
        error=raw.get("error"),
        error_kind=raw.get("error_kind"),
        parse_failures=int(raw.get("parse_failures", 0)),
        raw_responses=raw.get("raw_responses", []),
        provenance=raw.get("provenance", {}),
    )


def partition_valid_observations(
    records: list[EpisodeRecord],
) -> tuple[list[EpisodeRecord], list[EpisodeRecord]]:
    """Separate valid model observations from infrastructure failures."""
    valid: list[EpisodeRecord] = []
    invalid: list[EpisodeRecord] = []
    for r in records:
        if r.is_valid:
            valid.append(r)
        else:
            invalid.append(r)
    return valid, invalid
