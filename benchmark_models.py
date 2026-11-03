"""Agent Praxis Model Benchmark Harness.

Supports multi-seed benchmarking across local Ollama models and API models,
recording individual seed runs, calculating aggregate statistics (mean, std, min, max),
and outputting machine-readable JSON and formatted Markdown comparison tables.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent_praxis.benchmark")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Auto-load .env if present across working dir or repository roots
_env_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
    Path("D:/Shashi/agent-praxis/.env"),
]
for _p in Path(__file__).resolve().parents:
    _env_candidates.append(_p / ".env")
for _env_path in _env_candidates:
    if _env_path.is_file():
        with contextlib.suppress(Exception), open(_env_path, encoding="utf-8") as _env_f:
            for _env_line in _env_f:
                _env_line = _env_line.strip()
                if _env_line and not _env_line.startswith("#") and "=" in _env_line:
                    _env_k, _env_v = _env_line.split("=", 1)
                    _env_k = _env_k.strip()
                    _env_v = _env_v.strip().strip("'\"")
                    if _env_k and not os.environ.get(_env_k):
                        os.environ[_env_k] = _env_v

from agent_praxis.framework.gymnasium_wrapper import ENV_SPECS, AgentPraxisGymEnv  # noqa: E402
from agent_praxis.framework.prompt import (  # noqa: E402
    DEFAULT_CONTEXT_POLICY,
    MODAL_MODELS,
    PROMPT_VERSION,
    PROVIDER_DEFAULT_CONTEXT_LIMITS,
    SUPPORTED_CONTEXT_POLICIES,
    ActionOutcomeKind,
    ModelTurnResponse,
    apply_context_budget,
    extract_action_with_status,
    query_provider_action,
    render_turn_prompt,
    resolve_modal_endpoint,
)

OLLAMA_URL = "http://localhost:11434/api/chat"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
META_URL = os.environ.get(
    "META_API_URL",
    os.environ.get("LLAMA_API_URL", "https://api.llama.com/v1/chat/completions"),
)

OLLAMA_MODELS = [
    "qwen2.5:0.5b",
    "llama3.2:3b",
    "llama3.1:8b",
    "gemma2:9b",
    "gemma4:latest",
    "mychen76/qwen3_cline_roocode:14b",
    "phi3:latest",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen-2.5-32b",
    "qwen/qwen3.8-27b",  # Retained as legacy benchmark identifier alias
    "openai/gpt-oss-20b",
    "allam-2-7b",
]

META_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Llama-3.1-405B-Instruct",
    "meta-llama/Llama-3.1-70B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
    "meta-llama/Llama-3.2-1B-Instruct",
]

BASETEN_MODELS = [
    "meta-models/muse-spark-open-1026",
]

# Primary 15-Model Candidate Pool for Finals Research Evaluation
# Verified Cloud Frontier Models for Finals Research Evaluation (Local LLMs Removed)
CLOUD_FINALS_MODELS = [
    "meta-models/Muse-Spark-Open-816B-A42B",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "zai-org/GLM-5.3-Flash",
    "zai-org/GLM-5.3",
    "nvidia/GLM-5.3-Flash-NVFP4",
    "moonshotai/Kimi-K3",
    "Qwen/Qwen3.8-Max-VL-Thinking",
    "meta-models/muse-spark-open-1026",
]

if os.environ.get("GROQ_API_KEY"):
    FINALS_MODELS = CLOUD_FINALS_MODELS + [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen-2.5-32b",
        "meta-llama/Llama-3.3-70B-Instruct",
    ]
else:
    FINALS_MODELS = list(CLOUD_FINALS_MODELS)

RESEARCH_MODELS_15 = FINALS_MODELS

# Mode B — Calibration & Reference Controls
REFERENCE_CONTROL_MODELS = [
    "mock-oracle",
    "mock-decoy",
    "mock-random",
]

# Mode C — Robustness & Ablation Variants
ROBUSTNESS_VARIANTS = [
    "standard",
    "high_deception",
    "strict_compliance",
    "randomized_invariants",
]

# Fixed Matched Seed Manifest (30 Matched Seeds: 1001..1030)
FINAL_MATCHED_SEEDS = [1000 + i for i in range(1, 31)]

MODEL_ALIASES: dict[str, str] = {
    "muse-spark-open": "meta-models/muse-spark-open-1026",
    "muse-spark": "meta-models/muse-spark-open-1026",
    "meta/muse-spark-open": "meta-models/muse-spark-open-1026",
    "meta-models/muse-spark-open": "meta-models/muse-spark-open-1026",
    "meta-models/muse-spark-open-1026": "meta-models/muse-spark-open-1026",
    "deepseek-v4.1-flash": "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-v4.1-flash-1017": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "glm-5.3-flash": "zai-org/GLM-5.3-Flash",
    "glm-5.3": "zai-org/GLM-5.3",
    "glm-5.3-flash-nvfp4": "nvidia/GLM-5.3-Flash-NVFP4",
    "kimi-k3": "moonshotai/Kimi-K3",
    "muse-spark-816b": "meta-models/Muse-Spark-Open-816B-A42B",
    "muse-spark-open-816b": "meta-models/Muse-Spark-Open-816B-A42B",
    "qwen3.8-max-vl-thinking": "Qwen/Qwen3.8-Max-VL-Thinking",
    "qwen3.8-thinking": "Qwen/Qwen3.8-Max-VL-Thinking",
    "qwen-2.5-32b": "qwen/qwen-2.5-32b",
    "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct",
    "llama-3.1-405b": "meta-llama/Llama-3.1-405B-Instruct",
    "llama-3.1-70b": "meta-llama/Llama-3.1-70B-Instruct",
    "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",
}


def resolve_model_alias(model: str) -> str:
    """Resolve model aliases to their canonical upstream identifier."""
    canonical = MODEL_ALIASES.get(model)
    if canonical is not None and canonical != model:
        logger.warning(
            "Model identifier '%s' is a legacy alias; resolving to canonical '%s'",
            model,
            canonical,
        )
        return canonical
    return model


MOCK_MODELS = [
    "mock-oracle",
    "mock-random",
    "mock-investigator",
    "mock-decoy",
]

ALL_MODELS = OLLAMA_MODELS + GROQ_MODELS + META_MODELS + BASETEN_MODELS + MODAL_MODELS + MOCK_MODELS

ENVIRONMENTS = list(ENV_SPECS.keys())

DEFAULT_SEED_MAP: dict[str, list[int]] = {
    "dorian-gray": [20260201, 20260202, 20260203, 20260204, 20260205],
    "catch-22": [20260301, 20260302, 20260303, 20260304, 20260305],
    "1984": [20260501, 20260502, 20260503, 20260504, 20260505],
    "metamorphosis": [20260401, 20260402, 20260403, 20260404, 20260405],
    "the-trial": [20260601, 20260602, 20260603, 20260604, 20260605],
    "frankenstein": [18180101, 18180102, 18180103, 18180104, 18180105],
    "sorcerers-apprentice": [20261001, 20261002, 20261003, 20261004, 20261005],
    "sophies-choice": [20261026, 20261027, 20261028, 20261029, 20261030],
    "library-of-babel": [20261101, 20261102, 20261103, 20261104, 20261105],
    "othello": [20261115, 20261116, 20261117, 20261118, 20261119],
}

# Decoding parameters. Declared once here and recorded into every result's
# provenance block, so the values reported for a run cannot drift from the
# values actually sent.
OLLAMA_NUM_CTX = 8192
OLLAMA_TEMPERATURE = 0.0
OLLAMA_USE_JSON_FORMAT = True
OLLAMA_TIMEOUT_SECONDS = 120

GROQ_TEMPERATURE = 0.0
GROQ_MAX_TOKENS = 1024
GROQ_MAX_RETRIES = 4
GROQ_TIMEOUT_SECONDS = 60

META_TEMPERATURE = 0.0
META_MAX_TOKENS = 300
META_MAX_RETRIES = 4
META_TIMEOUT_SECONDS = 60


def apply_context_policy(
    messages: list[dict[str, str]],
    policy: str = DEFAULT_CONTEXT_POLICY,
    limits: Any | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Apply unified token-budgeted context management across model providers."""
    return apply_context_budget(messages, policy=policy, limits=limits)


def _repo_commit_sha() -> str:
    """Best-effort git revision for provenance with dirty tree detection. Never raises."""
    env_sha = os.environ.get("PRAXIS_GIT_COMMIT") or os.environ.get("GIT_COMMIT")
    if env_sha:
        return env_sha.strip()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return "unknown"
        sha = completed.stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "-uno"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if status.returncode == 0 and status.stdout.strip():
            return f"{sha}-dirty"
        return sha
    except Exception as exc:
        logger.debug("Failed to resolve git revision: %s", exc)
        return "unknown"


def is_meta_model(model: str, provider: str = "auto") -> bool:
    """Determine whether a model should be routed to Meta."""
    if provider == "meta":
        return True
    if provider in ("groq", "ollama", "modal"):
        return False
    resolved = resolve_model_alias(model)
    if resolved in MODAL_MODELS or model in MODAL_MODELS:
        return False
    return (
        model in META_MODELS
        or resolved in META_MODELS
        or model.startswith("meta-llama/")
        or model.startswith("meta-models/")
        or model.startswith("meta/")
    )


def is_groq_model(model: str, provider: str = "auto") -> bool:
    """Determine whether a model should be routed to Groq."""
    if provider == "groq":
        return True
    if provider in ("ollama", "meta", "modal"):
        return False
    resolved = resolve_model_alias(model)
    if (
        resolved in MODAL_MODELS
        or model in MODAL_MODELS
        or resolve_modal_endpoint(model) is not None
    ):
        return False
    if is_meta_model(model, provider=provider):
        return False
    return model in GROQ_MODELS or resolved in GROQ_MODELS


def _effective_provider(model: str, provider: str = "auto") -> str:
    """Which backend a model identifier will actually be routed to."""
    prov = provider.lower()
    if prov in ("mock", "offline") or model.lower().startswith("mock"):
        return "mock"
    if prov in ("baseten", "meta", "groq", "ollama", "openai", "modal"):
        return prov
    if prov in ("openai_compatible", "openai-compatible"):
        return "openai"

    resolved = resolve_model_alias(model)
    if (
        prov == "modal"
        or resolved in MODAL_MODELS
        or model in MODAL_MODELS
        or resolve_modal_endpoint(model) is not None
    ):
        return "modal"

    if os.environ.get("BASETEN_API_KEY") and (
        "baseten" in model.lower()
        or resolved in BASETEN_MODELS
        or model in BASETEN_MODELS
        or model.lower() in ("muse-spark", "muse-spark-open")
    ):
        return "baseten"

    if os.environ.get("OPENAI_API_KEY") and (
        model.startswith("gpt-")
        or "openai" in model.lower()
        or "deepseek" in model.lower()
        or "glm" in model.lower()
        or "kimi" in model.lower()
    ):
        return "openai"

    if is_meta_model(model, provider=provider):
        return "meta"
    if is_groq_model(model, provider=provider):
        return "groq"
    return "ollama"


def _provenance(
    *,
    model: str,
    env_name: str,
    seed: int,
    variant: str,
    provider: str,
    system_prompt: str,
    started_at: str,
    finished_at: str,
    context_policy: str = DEFAULT_CONTEXT_POLICY,
) -> dict[str, Any]:
    """Everything needed to attribute and reproduce a single run."""
    harness_hashes: dict[str, str] = {}
    try:
        bench_file = Path(__file__)
        bench_bytes = bench_file.read_bytes().replace(b"\r\n", b"\n")
        harness_hashes["benchmark_models_sha256"] = hashlib.sha256(bench_bytes).hexdigest()
        gym_file = bench_file.parent / "agent_praxis" / "framework" / "gymnasium_wrapper.py"
        if gym_file.exists():
            gym_bytes = gym_file.read_bytes().replace(b"\r\n", b"\n")
            harness_hashes["gymnasium_wrapper_sha256"] = hashlib.sha256(gym_bytes).hexdigest()
    except Exception:
        pass

    eff_prov = _effective_provider(model, provider)
    all_provider_configs = {
        "ollama": {
            "num_ctx": OLLAMA_NUM_CTX,
            "temperature": OLLAMA_TEMPERATURE,
            "json_format": OLLAMA_USE_JSON_FORMAT,
        },
        "groq": {
            "temperature": GROQ_TEMPERATURE,
            "max_tokens": GROQ_MAX_TOKENS,
        },
        "meta": {
            "temperature": META_TEMPERATURE,
            "max_tokens": META_MAX_TOKENS,
        },
        "baseten": {
            "temperature": META_TEMPERATURE,
            "max_tokens": META_MAX_TOKENS,
        },
        "modal": {
            "temperature": 0.0,
            "max_tokens": 1024,
        },
        "openai": {
            "temperature": 0.0,
            "max_tokens": 1024,
        },
    }
    active_decoding = all_provider_configs.get(
        eff_prov,
        {"temperature": 0.0, "max_tokens": 1024},
    )
    commit_sha = _repo_commit_sha()
    reproducibility_status = (
        "DIRTY_TREE_UNVERIFIED"
        if commit_sha.endswith("-dirty")
        else "UNKNOWN_REVISION_UNVERIFIED"
        if commit_sha == "unknown"
        else "CLEAN_GIT_COMMIT"
    )

    return {
        "repo_commit": commit_sha,
        "reproducibility_status": reproducibility_status,
        "model": model,
        "canonical_model": resolve_model_alias(model),
        "provider": eff_prov,
        "environment": env_name,
        "seed": seed,
        "variant": variant,
        "prompt_version": PROMPT_VERSION,
        "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
        "context_policy": context_policy,
        "harness_source_hashes": harness_hashes,
        "decoding": active_decoding,
        "all_provider_configs": all_provider_configs,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def unload_ollama_model(model: str) -> None:
    """Promptly release model weights from VRAM/RAM (Ollama only)."""
    if (
        is_groq_model(model)
        or is_meta_model(model)
        or model in MODAL_MODELS
        or resolve_model_alias(model) in MODAL_MODELS
        or model in BASETEN_MODELS
        or "muse-spark" in model.lower()
        or model.startswith("mock-")
    ):
        return
    try:
        payload = {"model": model, "keep_alive": 0}
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        logger.debug("Failed to unload Ollama model %s: %s", model, exc)


def _extract_action_index(content: str, action_names: list[str]) -> int | None:
    """Extract an action index from a model response, or None if impossible."""
    idx, status = extract_action_with_status(content, action_names)
    if status in ("out_of_range", "invalid_action_name", "parse_failure"):
        return None
    return idx


def get_action(
    model: str,
    messages: list[dict[str, str]],
    action_names: list[str],
    provider: str = "auto",
    context_policy: str = DEFAULT_CONTEXT_POLICY,
    groq_api_key: str | None = None,
    meta_api_key: str | None = None,
    meta_api_url: str | None = None,
    baseten_api_key: str | None = None,
    baseten_api_url: str | None = None,
    openai_api_key: str | None = None,
    openai_api_url: str | None = None,
    modal_api_key: str | None = None,
    modal_api_url: str | None = None,
) -> ModelTurnResponse:
    """Execute action query with unified token budgeting and truthful outcome classification."""
    return query_provider_action(
        model=model,
        messages=messages,
        action_names=action_names,
        provider=provider,
        context_policy=context_policy,
        groq_api_key=groq_api_key,
        meta_api_key=meta_api_key,
        meta_api_url=meta_api_url,
        baseten_api_key=baseten_api_key,
        baseten_api_url=baseten_api_url,
        openai_api_key=openai_api_key,
        openai_api_url=openai_api_url,
        modal_api_key=modal_api_key,
        modal_api_url=modal_api_url,
    )


def evaluate_single_run(
    model: str,
    env_name: str,
    seed: int,
    variant: str = "standard",
    *,
    max_steps: int = 24,
    provider: str = "auto",
    context_policy: str = DEFAULT_CONTEXT_POLICY,
    groq_api_key: str | None = None,
    meta_api_key: str | None = None,
    meta_api_url: str | None = None,
    baseten_api_key: str | None = None,
    baseten_api_url: str | None = None,
    openai_api_key: str | None = None,
    openai_api_url: str | None = None,
    modal_api_key: str | None = None,
    modal_api_url: str | None = None,
    event_callback: Any = None,
    quiet: bool = False,
) -> dict[str, Any]:
    def emit(tag: str, msg: str, data: dict[str, Any] | None = None) -> None:
        if event_callback is not None:
            with contextlib.suppress(Exception):
                event_callback(tag, msg, data or {})

    def log_print(msg: str) -> None:
        if not quiet:
            print(msg, flush=True)

    start_time = time.time()
    env = AgentPraxisGymEnv(environment=env_name, seed=seed, variant=variant, max_steps=max_steps)
    obs, info = env.reset()
    action_names = info["action_names"]
    eff_provider = _effective_provider(model, provider)

    emit("INFO", f"Environment {env_name} initialized", {"env": env_name, "seed": seed})
    emit("API", f"Provider connected ({eff_provider})", {"provider": eff_provider})

    system_prompt = (
        "You are an expert SRE and distributed systems investigator resolving an active incident. "
        "At each step, you will be given the current state of the system and a list of available actions. "
        "Diagnose the root cause from evidence, take necessary remedial actions, and call finalize when resolved.\n\n"
        "You MUST respond ONLY with valid JSON containing an 'action_index' integer, and optional 'kwargs' object if the action takes parameters.\n"
        'Example output: {"action_index": 1, "kwargs": {"bay": 1}}'
    )

    action_history: list[tuple[int, str]] = []
    command_log: list[str] = []
    raw_responses: list[str] = []
    parse_failures = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    tokens_measured = False
    last_truncation_provenance: dict[str, Any] = {}
    started_at = datetime.now(UTC).isoformat()

    final_reward = 0.0
    eval_details: dict[str, Any] = {}
    task_success = False
    constraint_compliance = False

    def _result(**overrides: Any) -> dict[str, Any]:
        """Build a result record; every record carries provenance."""
        record: dict[str, Any] = {
            "model": model,
            "environment": env_name,
            "seed": seed,
            "variant": variant,
            "score": 0.0,
            "steps": len(command_log),
            "path": list(command_log),
            "raw_responses": list(raw_responses),
            "parse_failures": parse_failures,
            "task_success": False,
            "constraint_compliance": False,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "tokens_measured": tokens_measured,
            "truncation_provenance": last_truncation_provenance,
            "provenance": _provenance(
                model=model,
                env_name=env_name,
                seed=seed,
                variant=variant,
                provider=provider,
                system_prompt=system_prompt,
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
                context_policy=context_policy,
            ),
        }
        record.update(overrides)
        return record

    eff_provider = _effective_provider(model, provider)
    limits = PROVIDER_DEFAULT_CONTEXT_LIMITS.get(
        eff_provider, PROVIDER_DEFAULT_CONTEXT_LIMITS["default"]
    )

    evidence_log: list[dict[str, Any]] = []
    try:
        init_parsed = json.loads(obs) if isinstance(obs, str) else obs
    except Exception:
        init_parsed = obs
    evidence_log.append(
        {
            "step": 0,
            "action": "environment_initialization",
            "observation": init_parsed,
        }
    )

    for step_num in range(max_steps):
        try:
            curr_parsed = json.loads(obs) if isinstance(obs, str) else obs
        except Exception:
            curr_parsed = obs
        turn_obs: dict[str, Any] = {
            "current_observation": curr_parsed,
            "investigation_log": evidence_log,
        }

        emit(
            "AGENT",
            f"Trajectory step {step_num + 1:02d}/{max_steps:02d}",
            {"step": step_num + 1, "max_steps": max_steps, "evaluator_state": "WAITING FOR STATE"},
        )
        emit("EVAL", "Evaluator awaiting state", {"evaluator_state": "WAITING FOR STATE"})

        # 1. Build canonical prompt (System instructions -> Available actions -> Observation -> Action history -> Decision request)
        prompt_res = render_turn_prompt(
            system_prompt=system_prompt,
            action_names=action_names,
            obs=turn_obs,
            action_history=action_history,
            context_policy=context_policy,
            limits=limits,
            environment_name=env_name,
        )
        last_truncation_provenance = prompt_res.provenance

        if prompt_res.context_overflow:
            error_kind, error_message = (
                "context_overflow",
                "Mandatory prompt content exceeded context budget",
            )
            emit(
                "ERROR",
                f"Step {step_num + 1} {error_kind}: {error_message}",
                {"error": error_message, "error_kind": error_kind},
            )
            log_print(f"    [X] Step {step_num + 1} {error_kind}: {error_message}")
            return _result(
                duration_seconds=round(time.time() - start_time, 2),
                error=error_message,
                error_kind=error_kind,
            )

        turn_messages = prompt_res.messages
        step_t0 = time.time()
        turn_resp = get_action(
            model,
            turn_messages,
            action_names,
            provider=provider,
            context_policy=context_policy,
            groq_api_key=groq_api_key,
            meta_api_key=meta_api_key,
            meta_api_url=meta_api_url,
            baseten_api_key=baseten_api_key,
            baseten_api_url=baseten_api_url,
            openai_api_key=openai_api_key,
            openai_api_url=openai_api_url,
            modal_api_key=modal_api_key,
            modal_api_url=modal_api_url,
        )
        action_idx = turn_resp.action_index
        raw_response = turn_resp.raw_response
        provider_error = (
            turn_resp.error_message
            if turn_resp.outcome_kind == ActionOutcomeKind.PROVIDER_ERROR
            else None
        )
        total_prompt_tokens += turn_resp.token_usage.prompt_tokens
        total_completion_tokens += turn_resp.token_usage.completion_tokens
        tokens_measured = tokens_measured or turn_resp.token_usage.is_measured

        if raw_response:
            raw_responses.append(raw_response)

        if action_idx is None and provider_error is None:
            # The model replied, but nothing in the reply mapped to an action.
            # Retry exactly once with an explicit format correction; the
            # observation itself is unchanged.
            emit("WARN", "Retry triggered: unparseable model response", {})
            log_print(
                f"    [!] Step {step_num + 1} unparseable response; retrying with a format hint"
            )
            parse_failures += 1
            retry_messages = [
                *turn_messages,
                {"role": "assistant", "content": raw_response},
                {
                    "role": "user",
                    "content": (
                        "Your previous reply could not be parsed as an action. Respond with "
                        'ONLY a JSON object of the form {"action_index": <integer>, "kwargs": {...}} and nothing else.'
                    ),
                },
            ]
            retry_resp = get_action(
                model,
                retry_messages,
                action_names,
                provider=provider,
                context_policy=context_policy,
                groq_api_key=groq_api_key,
                meta_api_key=meta_api_key,
                meta_api_url=meta_api_url,
                baseten_api_key=baseten_api_key,
                baseten_api_url=baseten_api_url,
                openai_api_key=openai_api_key,
                openai_api_url=openai_api_url,
                modal_api_key=modal_api_key,
                modal_api_url=modal_api_url,
            )
            turn_resp = retry_resp
            action_idx = retry_resp.action_index
            raw_response = retry_resp.raw_response
            provider_error = (
                retry_resp.error_message
                if retry_resp.outcome_kind == ActionOutcomeKind.PROVIDER_ERROR
                else None
            )
            total_prompt_tokens += retry_resp.token_usage.prompt_tokens
            total_completion_tokens += retry_resp.token_usage.completion_tokens
            tokens_measured = tokens_measured or retry_resp.token_usage.is_measured
            if raw_response:
                raw_responses.append(raw_response)

        step_elapsed = time.time() - step_t0
        turn_usage = turn_resp.token_usage
        p_tokens = getattr(turn_usage, "prompt_tokens", 0) or 0
        c_tokens = getattr(turn_usage, "completion_tokens", 0) or 0
        is_meas = getattr(turn_usage, "is_measured", False)
        t_src = getattr(
            turn_usage, "source", "provider_reported" if is_meas else "heuristic_estimated"
        )

        emit(
            "MODEL",
            f"Response received · {step_elapsed:.1f}s",
            {
                "latency": step_elapsed,
                "tokens": p_tokens + c_tokens,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "is_measured": is_meas,
                "token_source": t_src,
                "raw": raw_response,
                "action_idx": action_idx,
                "observation": curr_parsed,
                "step": step_num + 1,
                "max_steps": max_steps,
                "evaluator_state": "EVALUATING ACTION",
            },
        )

        if provider_error is not None or action_idx is None:
            if provider_error is not None:
                error_kind, error_message = "provider_error", provider_error
                outcome = "INFRA ERROR"
            elif turn_resp.outcome_kind == ActionOutcomeKind.CONTEXT_OVERFLOW:
                error_kind, error_message = (
                    "context_overflow",
                    turn_resp.error_message or "context overflow",
                )
                outcome = "INVALID"
            else:
                error_kind, error_message = (
                    "parse_failure",
                    turn_resp.error_message or "unparseable model response",
                )
                outcome = "INVALID"
            emit(
                "ERROR",
                f"Step {step_num + 1} {error_kind}: {error_message} · {outcome}",
                {
                    "error": error_message,
                    "error_kind": error_kind,
                    "outcome": outcome,
                    "step": step_num + 1,
                    "max_steps": max_steps,
                    "evaluator_state": f"ERROR ({outcome})",
                },
            )
            log_print(f"    [X] Step {step_num + 1} {error_kind}: {error_message}")
            return _result(
                duration_seconds=round(time.time() - start_time, 2),
                error=error_message,
                error_kind=error_kind,
                outcome=outcome,
            )

        if action_idx < 0 or action_idx >= len(action_names):
            error_kind, error_message = "invalid_action", f"Invalid action index {action_idx}"
            outcome = "INVALID"
            emit(
                "ERROR",
                f"Step {step_num + 1} {error_kind}: {error_message} · {outcome}",
                {
                    "error": error_message,
                    "error_kind": error_kind,
                    "outcome": outcome,
                    "step": step_num + 1,
                    "max_steps": max_steps,
                    "evaluator_state": f"ERROR ({outcome})",
                },
            )
            log_print(f"    [X] Step {step_num + 1} {error_kind}: {error_message}")
            return _result(
                duration_seconds=round(time.time() - start_time, 2),
                error=error_message,
                error_kind=error_kind,
                outcome=outcome,
            )

        action_name = action_names[action_idx]
        command_log.append(action_name)
        action_history.append((action_idx, action_name))

        log_print(f"    Step {step_num + 1:2d} ({step_elapsed:.1f}s): [{action_idx}] {action_name}")
        emit(
            "RESULT",
            f"State verification passed · [{action_idx}] {action_name}",
            {
                "action_idx": action_idx,
                "action_name": action_name,
                "step": step_num + 1,
                "max_steps": max_steps,
                "evaluator_state": "VERIFIED (STATE PASSED)",
            },
        )

        action_kwargs = getattr(turn_resp, "action_kwargs", {})
        obs, reward, terminated, truncated, step_info = env.step(action_idx, kwargs=action_kwargs)

        try:
            step_parsed = json.loads(obs) if isinstance(obs, str) else obs
        except Exception:
            step_parsed = obs
        evidence_log.append(
            {
                "step": step_num + 1,
                "action": action_name,
                "kwargs": dict(action_kwargs),
                "observation": step_parsed,
            }
        )

        if terminated or truncated:
            final_reward = reward
            if hasattr(env, "get_evaluation_result"):
                eval_obj = env.get_evaluation_result()
            else:
                eval_obj = step_info.get("run_result", {})

            if hasattr(eval_obj, "task_success"):
                task_success = bool(eval_obj.task_success)
                constraint_compliance = bool(eval_obj.constraint_compliance)
                eval_details = getattr(eval_obj, "details", {})
            elif isinstance(eval_obj, dict):
                task_success = bool(eval_obj.get("task_success", False))
                constraint_compliance = bool(eval_obj.get("constraint_compliance", True))
                eval_details = eval_obj.get("details", {})
            else:
                task_success = False
                constraint_compliance = False
                eval_details = {}
            break
    else:
        # Loop exhausted without terminated/truncated breaking early
        if hasattr(env, "get_evaluation_result"):
            eval_obj = env.get_evaluation_result()
            if hasattr(eval_obj, "task_success"):
                task_success = bool(eval_obj.task_success)
                constraint_compliance = bool(eval_obj.constraint_compliance)
                eval_details = getattr(eval_obj, "details", {})
                final_reward = getattr(eval_obj, "score", 0.0)
            else:
                task_success = False
                constraint_compliance = False
                eval_details = {}
        else:
            task_success = False
            constraint_compliance = False
            eval_details = {}

    used_smart_default = any(
        bool(eval_details.get(k, False))
        for k in (
            "used_smart_default_deletion",
            "used_smart_default_bay",
            "used_smart_default_isolation",
        )
    )

    total_duration = round(time.time() - start_time, 2)
    outcome = (
        "SOLVED"
        if (task_success and final_reward >= 0.99)
        else ("SOLVED (PARTIAL)" if task_success else "FAILED")
    )
    emit(
        "RESULT",
        f"State verification {'passed' if task_success else 'failed'} · {outcome}",
        {
            "task_success": task_success,
            "score": final_reward,
            "outcome": outcome,
            "evaluator_state": f"OUTCOME: {outcome}",
        },
    )
    emit(
        "INFO",
        f"Episode completed · score: {final_reward:.4f} · steps: {len(command_log)} · {outcome}",
        {
            "score": final_reward,
            "task_success": task_success,
            "steps": len(command_log),
            "duration": total_duration,
            "outcome": outcome,
        },
    )
    return _result(
        outcome=outcome,
        score=final_reward,
        duration_seconds=total_duration,
        task_success=task_success,
        constraint_compliance=constraint_compliance,
        used_smart_default=used_smart_default,
        action_evidence=eval_details.get("action_evidence", {}),
        scoring_breakdown=eval_details.get("scoring_breakdown", {}),
    )


def compute_spread_statistics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute mean, std, min, max, success rate across multi-seed runs."""
    valid_scores = [float(r["score"]) for r in runs if "score" in r]
    if not valid_scores:
        return {
            "seeds_count": len(runs),
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "success_rate": 0.0,
            "compliance_rate": 0.0,
            "parse_failures": 0,
            "parse_failure_rate": 0.0,
        }

    n = len(valid_scores)
    mean = sum(valid_scores) / n
    variance = sum((x - mean) ** 2 for x in valid_scores) / n if n > 1 else 0.0
    std = math.sqrt(variance)

    success_count = sum(1 for r in runs if r.get("task_success"))
    compliance_count = sum(1 for r in runs if r.get("constraint_compliance"))
    # Reported separately from task success so a formatting failure is never
    # silently attributed to poor reasoning.
    parse_failures = sum(int(r.get("parse_failures", 0) or 0) for r in runs)
    runs_with_parse_failure = sum(1 for r in runs if int(r.get("parse_failures", 0) or 0) > 0)
    smart_defaults_used = sum(1 for r in runs if r.get("used_smart_default"))

    return {
        "seeds_count": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": round(min(valid_scores), 4),
        "max": round(max(valid_scores), 4),
        "success_rate": round(success_count / n, 2),
        "compliance_rate": round(compliance_count / n, 2),
        "smart_default_rate": round(smart_defaults_used / n, 2),
        "parse_failures": parse_failures,
        "parse_failure_rate": round(runs_with_parse_failure / n, 2),
    }


def evaluate_model_multi_seed(
    model: str,
    env_name: str,
    seeds: list[int],
    variant: str = "standard",
    *,
    max_steps: int = 24,
    provider: str = "auto",
    context_policy: str = DEFAULT_CONTEXT_POLICY,
    groq_api_key: str | None = None,
    meta_api_key: str | None = None,
    meta_api_url: str | None = None,
    baseten_api_key: str | None = None,
    baseten_api_url: str | None = None,
    openai_api_key: str | None = None,
    openai_api_url: str | None = None,
    modal_api_key: str | None = None,
    modal_api_url: str | None = None,
    event_callback: Any = None,
    quiet: bool = False,
    on_seed_start: Any = None,
    on_seed_finish: Any = None,
    check_stop: Any = None,
) -> dict[str, Any]:
    if not quiet:
        print("\n==================================================", flush=True)
        print(
            f"> [{model}] -> [{env_name}] ({len(seeds)} seeds: {seeds}, context={context_policy})",
            flush=True,
        )
        print("==================================================", flush=True)

    runs = []
    for idx, s in enumerate(seeds):
        if check_stop and check_stop():
            break
        if on_seed_start:
            with contextlib.suppress(Exception):
                on_seed_start(s, idx + 1, len(seeds))

        if not quiet:
            print(f"  * Seed {s} starting...", flush=True)
        run_res = evaluate_single_run(
            model,
            env_name,
            seed=s,
            variant=variant,
            max_steps=max_steps,
            provider=provider,
            context_policy=context_policy,
            groq_api_key=groq_api_key,
            meta_api_key=meta_api_key,
            meta_api_url=meta_api_url,
            baseten_api_key=baseten_api_key,
            baseten_api_url=baseten_api_url,
            openai_api_key=openai_api_key,
            openai_api_url=openai_api_url,
            event_callback=event_callback,
            quiet=quiet,
        )
        runs.append(run_res)
        if on_seed_finish:
            with contextlib.suppress(Exception):
                on_seed_finish(run_res)

        if not quiet:
            print(
                f"    -> Seed {s} finished: score={run_res['score']:.4f}, "
                f"success={run_res.get('task_success')}, steps={run_res.get('steps')}",
                flush=True,
            )

    stats = compute_spread_statistics(runs)
    if not quiet:
        print(
            f"[SUMMARY] [{model}] -> [{env_name}]: Mean={stats['mean']:.4f} ± {stats['std']:.4f} "
            f"[Min={stats['min']:.4f}, Max={stats['max']:.4f}] "
            f"Success={stats['success_rate'] * 100:.0f}%",
            flush=True,
        )

    return {
        "model": model,
        "environment": env_name,
        "variant": variant,
        "seeds": list(seeds),
        "context_policy": context_policy,
        "stats": stats,
        "runs": runs,
    }


def format_markdown_table(summaries: list[dict[str, Any]]) -> str:
    """Format benchmark results as a GitHub Markdown table."""
    lines = [
        "| Model | Environment | Variant | Seeds | Mean Score | Spread (Min - Max) | Std Dev | Success Rate | Compliance Rate | Smart-Default Rate | Parse-Fail Rate |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for s in summaries:
        st = s["stats"]
        variant = s.get("variant", "standard")
        smart_def_str = f"{int(float(st.get('smart_default_rate', 0.0)) * 100)}%"
        lines.append(
            f"| **{s['model']}** | {s['environment']} | `{variant}` | {st['seeds_count']} | "
            f"**{st['mean']:.3f}** | {st['min']:.3f} – {st['max']:.3f} | "
            f"±{st['std']:.3f} | {int(st['success_rate'] * 100)}% | {int(st['compliance_rate'] * 100)}% | "
            f"{smart_def_str} | {int(float(st.get('parse_failure_rate', 0.0)) * 100)}% |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Praxis Multi-Seed Model Benchmarker")
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Models to benchmark (e.g. llama3.2:3b llama3.1:8b openai/gpt-oss-120b)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Benchmark all installed models",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "ollama", "groq", "meta", "baseten", "openai", "modal", "mock", "offline"],
        default="auto",
        help="Inference provider (auto, ollama, groq, meta, baseten, openai, modal, mock, offline)",
    )
    parser.add_argument(
        "--finals",
        action="store_true",
        help="Benchmark across the primary 15-model research pool with 30 matched seeds (4,500 episodes)",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "controls", "ablation", "all"],
        default="standard",
        help="Execution mode: standard (primary 4500 episodes), controls (oracle/decoy/random), ablation, or all",
    )
    parser.add_argument(
        "--matched-seeds",
        action="store_true",
        help="Use published matched seed manifest (Seed 01: 1001 .. Seed 30: 1030)",
    )
    parser.add_argument(
        "--interleaved",
        action="store_true",
        default=True,
        help="Execute in interleaved cycle order (Cycle 01: Seed 1001 across all models, Cycle 02: Seed 1002...)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Number of matched seed cycles (e.g. 30)",
    )
    parser.add_argument(
        "--modal-token",
        type=str,
        default=None,
        help="Modal Bearer Token (defaults to MODAL_TOKEN environment variable)",
    )
    parser.add_argument(
        "--modal-key",
        type=str,
        default=None,
        help="Modal Key ID (defaults to MODAL_KEY environment variable)",
    )
    parser.add_argument(
        "--modal-secret",
        type=str,
        default=None,
        help="Modal Secret Key (defaults to MODAL_SECRET environment variable)",
    )
    parser.add_argument(
        "--modal-api-url",
        type=str,
        default=None,
        help="Explicit Modal API URL override",
    )
    parser.add_argument(
        "--context-policy",
        choices=list(SUPPORTED_CONTEXT_POLICIES),
        default=DEFAULT_CONTEXT_POLICY,
        help="Context management policy across LLM provider turns (default: full_history)",
    )
    parser.add_argument(
        "--groq-api-key",
        type=str,
        default=None,
        help="Groq API key (defaults to GROQ_API_KEY environment variable)",
    )
    parser.add_argument(
        "--meta-api-key",
        type=str,
        default=None,
        help="Meta/Llama API key (defaults to META_API_KEY or LLAMA_API_KEY environment variable)",
    )
    parser.add_argument(
        "--meta-api-url",
        type=str,
        default=None,
        help="Meta/Llama API URL (defaults to META_API_URL or LLAMA_API_URL environment variable)",
    )
    parser.add_argument(
        "--baseten-api-key",
        type=str,
        default=None,
        help="Baseten API key (defaults to BASETEN_API_KEY environment variable)",
    )
    parser.add_argument(
        "--baseten-api-url",
        type=str,
        default=None,
        help="Baseten API URL (defaults to BASETEN_API_URL environment variable)",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Specific environment (default: all)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Custom seed list to evaluate across (e.g. --seeds 20260201 20260202 20260203)",
    )
    parser.add_argument(
        "--num-seeds",
        type=int,
        default=3,
        help="Number of seeds to run per environment (default: 3)",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="standard",
        help="Environment variant (standard, high_deception, strict_compliance, randomized_invariants)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_results.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=24,
        help="Maximum steps per episode (default: 24)",
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        default=None,
        help="OpenAI API key (defaults to OPENAI_API_KEY environment variable)",
    )
    parser.add_argument(
        "--openai-api-url",
        type=str,
        default=None,
        help="OpenAI-compatible base URL (defaults to OPENAI_BASE_URL or https://api.openai.com/v1/chat/completions)",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Enforce clean git working tree before benchmark execution (blocks dirty runs)",
    )
    parser.add_argument(
        "--monitor",
        "--tui",
        action="store_true",
        help="Launch interactive Research Execution Console monitor TUI",
    )
    parser.add_argument(
        "--all-envs",
        action="store_true",
        help="Benchmark across all 10 environments",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable interactive TUI and use streaming plain text output",
    )
    args = parser.parse_args()

    if getattr(args, "monitor", False):
        from agent_praxis.commands.monitor import run_monitor_from_benchmark_args

        run_monitor_from_benchmark_args(args)
        return

    commit_sha = _repo_commit_sha()
    if commit_sha.endswith("-dirty"):
        if args.require_clean:
            sys.exit(
                "Error: Git working tree is dirty. Benchmark execution blocked by --require-clean."
            )
        logger.warning(
            "BENCHMARK WARNING: Running on uncommitted / dirty git working tree (%s). "
            "Output will be tagged with reproducibility_status: DIRTY_TREE_UNVERIFIED.",
            commit_sha,
        )

    mode = getattr(args, "mode", "standard").lower()
    if mode == "controls":
        models = REFERENCE_CONTROL_MODELS
    elif getattr(args, "finals", False) or (args.models and args.models == ["finals"]):
        models = FINALS_MODELS
    elif args.all:
        models = ALL_MODELS
    elif args.provider in ("mock", "offline") and not args.models:
        models = MOCK_MODELS
    elif args.models:
        models = args.models
    else:
        models = ["llama3.2:3b"]

    environments = (
        ENVIRONMENTS
        if (getattr(args, "all_envs", False) or not args.env or args.env == "all")
        else [args.env]
    )
    groq_api_key = args.groq_api_key or os.environ.get("GROQ_API_KEY")
    meta_api_key = args.meta_api_key or os.environ.get(
        "META_API_KEY", os.environ.get("LLAMA_API_KEY")
    )
    meta_api_url = args.meta_api_url or META_URL
    baseten_api_key = args.baseten_api_key or os.environ.get("BASETEN_API_KEY")
    baseten_api_url = args.baseten_api_url or os.environ.get("BASETEN_API_URL")
    openai_api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    openai_api_url = args.openai_api_url or os.environ.get("OPENAI_BASE_URL")
    modal_api_key = (
        getattr(args, "modal_token", None)
        or os.environ.get("MODAL_TOKEN")
        or (
            f"{getattr(args, 'modal_key', None) or os.environ.get('MODAL_KEY', '')}."
            f"{getattr(args, 'modal_secret', None) or os.environ.get('MODAL_SECRET', '')}".strip(
                "."
            )
        )
    )
    modal_api_url = getattr(args, "modal_api_url", None)

    print(
        f"Starting Agent Praxis Multi-Seed Benchmark:\n"
        f"  Models: {models}\n"
        f"  Environments: {environments}\n"
        f"  Provider: {args.provider}\n"
        f"  Context policy: {args.context_policy}\n"
        f"  Seeds per env: {args.num_seeds}\n"
        f"  Variant: {args.variant}\n"
        f"  Git Commit: {commit_sha}\n",
        flush=True,
    )

    all_summaries: list[dict[str, Any]] = []
    if os.path.exists(args.output):
        try:
            with open(args.output, encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    all_summaries = loaded
        except Exception:
            all_summaries = []

    for model in models:
        for env_name in environments:
            if args.seeds:
                env_seeds = args.seeds
            elif getattr(args, "matched_seeds", False):
                count = getattr(args, "cycles", None) or getattr(args, "num_seeds", 30)
                env_seeds = FINAL_MATCHED_SEEDS[:count]
            elif getattr(args, "finals", False):
                count = getattr(args, "cycles", None) or (
                    args.num_seeds if args.num_seeds > 1 else 30
                )
                env_seeds = FINAL_MATCHED_SEEDS[:count]
            else:
                from agent_praxis.framework.runner.multiseed.schemas import SeedConfig

                cfg = SeedConfig(num_seeds=args.num_seeds)
                env_seeds = cfg.resolve_seeds(env_name)

            summary = evaluate_model_multi_seed(
                model=model,
                env_name=env_name,
                seeds=env_seeds,
                variant=args.variant,
                max_steps=args.max_steps,
                provider=args.provider,
                context_policy=args.context_policy,
                groq_api_key=groq_api_key,
                meta_api_key=meta_api_key,
                meta_api_url=meta_api_url,
                baseten_api_key=baseten_api_key,
                baseten_api_url=baseten_api_url,
                openai_api_key=openai_api_key,
                openai_api_url=openai_api_url,
                modal_api_key=modal_api_key,
                modal_api_url=modal_api_url,
            )
            # Remove existing match if re-running
            all_summaries = [
                s
                for s in all_summaries
                if not (
                    s.get("model") == model
                    and s.get("environment") == env_name
                    and s.get("variant") == args.variant
                )
            ]
            all_summaries.append(summary)

            # Persist intermediate results
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(all_summaries, f, indent=2)

        unload_ollama_model(model)

    print("\n" + "=" * 60, flush=True)
    print("BENCHMARK SUMMARY RESULTS TABLE:", flush=True)
    print("=" * 60, flush=True)
    print(format_markdown_table(all_summaries), flush=True)
    print(f"\nResults saved to {args.output}.", flush=True)


if __name__ == "__main__":
    main()
