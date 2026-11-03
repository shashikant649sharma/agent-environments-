"""Unit tests verifying competition finals model routing, endpoints, and providers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from agent_praxis.commands.monitor import (
    format_model_name,
    format_provider_name,
    render_final_research_summary,
)
from agent_praxis.framework.prompt import (
    MODAL_MODEL_ENDPOINTS,
    MODAL_MODELS,
    ActionOutcomeKind,
    ModelTurnResponse,
    TokenUsage,
    query_provider_action,
    resolve_modal_endpoint,
)
from benchmark_models import (
    BASETEN_MODELS,
    FINAL_MATCHED_SEEDS,
    FINALS_MODELS,
    REFERENCE_CONTROL_MODELS,
    RESEARCH_MODELS_15,
    ROBUSTNESS_VARIANTS,
    _effective_provider,
)


def test_finals_models_list_and_endpoints() -> None:
    """Verify all 8 Modal models and 1 Baseten model are registered in Finals models."""
    assert len(MODAL_MODELS) == 8
    assert len(BASETEN_MODELS) == 1
    assert "meta-models/muse-spark-open-1026" in BASETEN_MODELS
    assert len(RESEARCH_MODELS_15) == len(FINALS_MODELS)
    assert len(FINALS_MODELS) >= 9
    # Verify all local Ollama tag-based models are removed from finals execution
    assert all(":" not in m for m in FINALS_MODELS)
    assert len(REFERENCE_CONTROL_MODELS) == 3
    assert len(ROBUSTNESS_VARIANTS) == 4
    assert len(FINAL_MATCHED_SEEDS) == 30
    assert FINAL_MATCHED_SEEDS[0] == 1001
    assert FINAL_MATCHED_SEEDS[-1] == 1030

    expected_modal = [
        "deepseek-ai/DeepSeek-V4.1-Flash",
        "deepseek-ai/DeepSeek-V4.1-Flash-1017",
        "zai-org/GLM-5.3-Flash",
        "zai-org/GLM-5.3",
        "nvidia/GLM-5.3-Flash-NVFP4",
        "moonshotai/Kimi-K3",
        "meta-models/Muse-Spark-Open-816B-A42B",
        "Qwen/Qwen3.8-Max-VL-Thinking",
    ]
    for m in expected_modal:
        assert m in MODAL_MODELS
        assert m in MODAL_MODEL_ENDPOINTS
        res = resolve_modal_endpoint(m)
        assert res is not None
        assert res[0] == m
        assert "modal.direct" in res[1]


def test_modal_endpoint_alias_resolution() -> None:
    """Verify short aliases correctly resolve to upstream canonical identifiers."""
    aliases = {
        "deepseek-v4.1-flash": "deepseek-ai/DeepSeek-V4.1-Flash",
        "glm-5.3-flash": "zai-org/GLM-5.3-Flash",
        "kimi-k3": "moonshotai/Kimi-K3",
        "muse-spark-816b": "meta-models/Muse-Spark-Open-816B-A42B",
        "qwen3.8-max-vl-thinking": "Qwen/Qwen3.8-Max-VL-Thinking",
    }
    for alias, canonical in aliases.items():
        res = resolve_modal_endpoint(alias)
        assert res is not None
        assert res[0] == canonical


def test_effective_provider_classification() -> None:
    """Verify _effective_provider routes correctly without ambiguous fallbacks."""
    # Modal models
    assert _effective_provider("deepseek-ai/DeepSeek-V4.1-Flash") == "modal"
    assert _effective_provider("zai-org/GLM-5.3-Flash") == "modal"
    assert _effective_provider("moonshotai/Kimi-K3") == "modal"
    assert _effective_provider("meta-models/Muse-Spark-Open-816B-A42B") == "modal"
    assert _effective_provider("Qwen/Qwen3.8-Max-VL-Thinking") == "modal"

    # Aliases
    assert _effective_provider("deepseek-v4.1-flash") == "modal"
    assert _effective_provider("glm-5.3-flash") == "modal"
    assert _effective_provider("kimi-k3") == "modal"

    # Baseten Muse Spark
    with patch.dict(os.environ, {"BASETEN_API_KEY": "dummy_key"}):
        assert _effective_provider("meta-models/muse-spark-open-1026") == "baseten"
        assert _effective_provider("muse-spark-open") == "baseten"

    # Groq & Ollama models in 15-model pool
    assert _effective_provider("openai/gpt-oss-120b") == "groq"
    assert _effective_provider("openai/gpt-oss-20b") == "groq"
    assert _effective_provider("qwen/qwen-2.5-32b") == "groq"
    assert _effective_provider("llama3.1:8b") == "ollama"
    assert _effective_provider("qwen2.5:0.5b") == "ollama"

    # Reference controls
    assert _effective_provider("mock-oracle") == "mock"
    assert _effective_provider("mock-decoy") == "mock"
    assert _effective_provider("mock-random") == "mock"

    # Explicit provider override
    assert _effective_provider("any-model", provider="modal") == "modal"
    assert _effective_provider("any-model", provider="baseten") == "baseten"
    assert _effective_provider("any-model", provider="mock") == "mock"


def test_format_display_helpers_for_finals() -> None:
    """Verify TUI friendly display aliases for finals models."""
    assert format_model_name("deepseek-ai/DeepSeek-V4.1-Flash") == "DeepSeek V4.1 Flash"
    assert format_model_name("zai-org/GLM-5.3-Flash") == "GLM 5.3 Flash"
    assert format_model_name("moonshotai/Kimi-K3") == "Kimi-K3"
    assert format_model_name("meta-models/Muse-Spark-Open-816B-A42B") == "Muse Spark Open 816B"
    assert format_model_name("Qwen/Qwen3.8-Max-VL-Thinking") == "Qwen 3.8 Max VL Thinking"
    assert format_model_name("meta-models/muse-spark-open-1026") == "Muse Spark Open"

    assert format_provider_name("modal", "deepseek-ai/DeepSeek-V4.1-Flash") == "Modal Serverless"
    assert format_provider_name("baseten", "meta-models/muse-spark-open-1026") == "Baseten API"


def test_render_final_research_summary_panel() -> None:
    """Verify the Section 7 research evaluation console summary panel renders cleanly."""
    mock_summaries = [
        {
            "model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "environment": "dorian-gray",
            "runs": [{"score": 0.85, "outcome": "SOLVED"}, {"score": 0.90, "outcome": "SOLVED"}],
        },
        {
            "model": "meta-models/muse-spark-open-1026",
            "environment": "dorian-gray",
            "runs": [{"score": 0.70, "outcome": "SOLVED"}, {"score": 0.75, "outcome": "SOLVED"}],
        },
    ]
    panel = render_final_research_summary(
        mock_summaries,
        total_models=15,
        total_envs=10,
        total_seeds=30,
        status_str="EVALUATION COMPLETED",
    )
    assert panel is not None


@patch("agent_praxis.framework.prompt.get_action_from_openai")
def test_query_provider_action_routes_to_modal(mock_openai: MagicMock) -> None:
    """Verify query_provider_action calls get_action_from_openai with Modal token and endpoint."""
    mock_openai.return_value = ModelTurnResponse(
        outcome_kind=ActionOutcomeKind.VALID_ACTION,
        action_index=0,
        action_name="read_status",
        raw_response='{"action_index": 0}',
        error_message=None,
        parse_status="clean_json",
        token_usage=TokenUsage(prompt_tokens=50, completion_tokens=10, is_measured=True),
    )

    with patch.dict(os.environ, {"MODAL_TOKEN": "test_modal_token_123"}):
        res = query_provider_action(
            model="deepseek-ai/DeepSeek-V4.1-Flash",
            messages=[{"role": "user", "content": "test"}],
            action_names=["read_status", "finalize"],
        )
        assert res.outcome_kind == ActionOutcomeKind.VALID_ACTION
        assert res.action_index == 0

        # Verify get_action_from_openai call arguments
        mock_openai.assert_called_once()
        _, kwargs = mock_openai.call_args
        assert kwargs["model"] == "deepseek-ai/DeepSeek-V4.1-Flash"
        assert kwargs["api_key"] == "test_modal_token_123"
        assert "shashikant649--ep-deepseek-v4-1-flash" in kwargs["url"]
        assert kwargs["max_tokens"] == 1024
