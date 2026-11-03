"""Tests for Agent Praxis Research Execution Console (Monitor CLI / TUI)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from agent_praxis.__main__ import main as praxis_main
from agent_praxis.commands.monitor import (
    ALL_10_ENVIRONMENTS,
    FILTER_MODES,
    ConsoleMonitor,
    format_duration,
    format_env_name,
    format_model_name,
    format_provider_name,
)


def test_monitor_format_helpers() -> None:
    """Verify display formatting helpers map models, providers, and envs properly."""
    assert format_model_name("qwen2.5:0.5b") == "Qwen 2.5 (0.5B)"
    assert format_model_name("meta-models/muse-spark-open-1026") == "Muse Spark Open"
    assert format_model_name("mock-oracle") == "Mock Oracle"

    assert format_provider_name("ollama", "qwen2.5:0.5b") == "Ollama (Local)"
    assert format_provider_name("mock", "mock-oracle") == "Offline Mock Engine"
    assert format_provider_name("baseten", "muse-spark-open") == "Baseten API"

    assert format_env_name("dorian-gray") == "Dorian Gray"
    assert format_env_name("catch-22") == "Catch-22"
    assert format_env_name("1984") == "1984"
    assert format_env_name("othello") == "Othello"

    assert format_duration(45) == "00:45"
    assert format_duration(261) == "04:21"
    assert format_duration(3665) == "01:01:05"


def test_monitor_state_and_keyboard_handling() -> None:
    """Verify keyboard shortcuts toggle states and cycle filter modes."""
    mon = ConsoleMonitor(
        models=["mock-oracle"],
        environments=["dorian-gray"],
        use_tui=False,
    )
    assert mon.status == "RUNNING"
    assert mon.current_filter_name == "ALL"
    assert mon.dialogue_mode is False
    assert mon.evaluator_mode is False

    mon.handle_key("d")
    assert mon.dialogue_mode is True

    mon.handle_key("f")
    assert mon.current_filter_name == "MILESTONES"
    mon.handle_key("f")
    assert mon.current_filter_name == "MODEL & AGENT"
    mon.handle_key("f")
    assert mon.current_filter_name == "ERRORS"
    mon.handle_key("f")
    assert mon.current_filter_name == "ALL"

    mon.handle_key("e")
    assert mon.evaluator_mode is True

    mon.handle_key("s")
    assert mon.stop_requested is True
    assert mon.status == "STOPPING"
    assert "STOPPING" in mon.evaluator_state

    mon.handle_key("q")
    assert mon.quit_requested is True
    assert mon.status == "ABORTED"
    assert "ABORTED" in mon.evaluator_state


def test_monitor_render_with_detail_and_token_breakdown() -> None:
    """Verify render() displays execution detail block, dual progress, and token accounting."""
    mon = ConsoleMonitor(
        models=["qwen2.5:0.5b"],
        environments=["dorian-gray", "catch-22"],
        num_seeds=5,
        use_tui=False,
    )
    mon.completed_runs = 8
    mon.current_env_idx = 8
    mon.total_envs = 10
    mon.total_runs = 10

    mon.add_event(
        "AGENT",
        "Trajectory step 04/20",
        {"step": 4, "max_steps": 20, "evaluator_state": "WAITING FOR STATE"},
    )
    mon.add_event(
        "MODEL",
        "Response received · 2.4s",
        {
            "latency": 2.4,
            "prompt_tokens": 650000,
            "completion_tokens": 51831,
            "is_measured": True,
            "token_source": "provider_reported",
            "action_idx": 1,
            "evaluator_state": "EVALUATING ACTION",
        },
    )
    mon.add_event(
        "RESULT",
        "State verification passed · [1] read_status",
        {
            "action_name": "read_status",
            "evaluator_state": "VERIFIED (STATE PASSED)",
            "outcome": "SOLVED",
        },
    )

    assert mon.current_trajectory_step == 4
    assert mon.last_verified_action == "read_status"
    assert mon.evaluator_state == "VERIFIED (STATE PASSED)"
    assert mon.input_tokens == 650000
    assert mon.output_tokens == 51831
    assert mon.total_tokens == 701831
    assert mon.tokens_measured is True

    panel = mon.render()
    assert panel is not None


def test_monitor_terminal_resize_narrow_width() -> None:
    """Verify layout preserves formatting without error at smaller terminal widths."""
    mon = ConsoleMonitor(
        models=["mock-oracle"],
        environments=["dorian-gray"],
        use_tui=False,
    )
    mon.console.width = 60
    mon.console.height = 20
    panel = mon.render()
    assert panel is not None


def test_praxis_monitor_cli_execution_with_outcome(tmp_path: Path) -> None:
    """Verify praxis monitor records outcome and token accounting in report JSON."""
    out_file = tmp_path / "test_report.json"
    ret = praxis_main(
        [
            "monitor",
            "--models",
            "mock-oracle",
            "--env",
            "dorian-gray",
            "--num-seeds",
            "1",
            "--no-tui",
            "--output",
            str(out_file),
        ]
    )
    assert ret == 0
    assert out_file.exists()

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["environment"] == "dorian-gray"
    assert data[0]["model"] == "mock-oracle"
    assert data[0]["stats"]["mean"] == 1.0
    assert data[0]["stats"]["success_rate"] == 1.0
    # Check that runs have outcome recorded
    runs = data[0].get("runs", [])
    assert len(runs) == 1
    assert runs[0]["outcome"] == "SOLVED"


def test_all_10_environments_in_spec() -> None:
    """Verify exactly 10 canonical environments are declared in the suite."""
    expected = [
        "dorian-gray",
        "catch-22",
        "1984",
        "metamorphosis",
        "the-trial",
        "frankenstein",
        "sorcerers-apprentice",
        "sophies-choice",
        "library-of-babel",
        "othello",
    ]
    assert expected == ALL_10_ENVIRONMENTS
    assert len(FILTER_MODES) == 4


def test_monitor_infra_error_classification_and_summary() -> None:
    """Verify INFRA ERROR precedence, summary table styling, and infrastructure failure counts."""
    from agent_praxis.commands.monitor import render_final_research_summary

    summaries = [
        {
            "model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "environment": "dorian-gray",
            "stats": {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "success_rate": 0.0,
                "compliance_rate": 1.0,
            },
            "runs": [
                {
                    "seed": 1001,
                    "score": 0.0,
                    "task_success": False,
                    "error_kind": "provider_error",
                    "error": "HTTP Error 503: Service Unavailable",
                    "outcome": "INFRA ERROR",
                }
            ],
        },
        {
            "model": "meta-models/muse-spark-open-1026",
            "environment": "catch-22",
            "stats": {
                "mean": 1.0,
                "min": 1.0,
                "max": 1.0,
                "success_rate": 1.0,
                "compliance_rate": 1.0,
            },
            "runs": [
                {
                    "seed": 1001,
                    "score": 1.0,
                    "task_success": True,
                    "error_kind": None,
                    "error": None,
                    "outcome": "SOLVED",
                }
            ],
        },
    ]

    panel = render_final_research_summary(
        summaries=summaries,
        total_models=2,
        total_envs=2,
        total_seeds=1,
        status_str="TEST RUN",
    )
    assert panel is not None

    mon = ConsoleMonitor(
        models=["deepseek-ai/DeepSeek-V4.1-Flash"],
        environments=["dorian-gray"],
        use_tui=False,
    )
    mon.add_event(
        "ERROR",
        "Step 1 provider_error: Gateway timeout · INFRA ERROR",
        {
            "outcome": "INFRA ERROR",
            "error_kind": "provider_error",
            "evaluator_state": "ERROR (INFRA ERROR)",
        },
    )
    assert mon.current_outcome == "INFRA ERROR"
    assert "INFRA ERROR" in mon.evaluator_state

    rendered = mon.render()
    assert rendered is not None
