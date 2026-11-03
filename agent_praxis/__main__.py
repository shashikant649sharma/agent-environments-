"""Agent Praxis main entry point."""

from __future__ import annotations

import argparse
import sys

from agent_praxis.commands import demo, environment, monitor, validate
from agent_praxis.registry import ENVIRONMENT_NAMES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="praxis", description="Agent Praxis — reproducible agent environments."
    )
    sub = parser.add_subparsers(dest="command")

    demo_parser = sub.add_parser(
        "demo",
        help="Display side-by-side baseline policy comparisons or execute live demonstrations.",
    )
    demo_parser.add_argument(
        "--live",
        action="store_true",
        help="Execute policies live in-memory instead of displaying cached canonical summary.",
    )
    demo_parser.add_argument(
        "--env",
        choices=list(ENVIRONMENT_NAMES) + ["all"],
        default=None,
        help="Target environment (default: all for summary, '1984' for live)",
    )
    demo_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic seed for live execution (default: 42)",
    )
    demo_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output results as JSON",
    )
    demo_parser.add_argument(
        "--markdown",
        action="store_true",
        help="Format output as a Markdown table",
    )
    demo_parser.set_defaults(func=lambda args: demo.main_args(args))

    ALL_ENVS = list(ENVIRONMENT_NAMES)
    env_parser = sub.add_parser("environment", help="Manage an environment.")
    env_parser.add_argument("environment_name", choices=ALL_ENVS, help="Environment name.")
    env_sub = env_parser.add_subparsers(dest="action")
    for action in ("setup", "run", "reset", "evaluate"):
        p = env_sub.add_parser(action)
        p.add_argument("--seed", type=int, default=None, help="Deterministic seed")
    env_parser.set_defaults(
        func=lambda args: environment.main(
            [args.environment_name, args.action, "--seed", str(args.seed)]
            if args.seed is not None
            else [args.environment_name, args.action]
        )
    )

    val_parser = sub.add_parser("validate", help="Validate an environment.")
    val_parser.add_argument("environment", choices=ALL_ENVS, help="Environment to validate.")
    val_parser.add_argument("--seed", type=int, default=None, help="Deterministic seed")
    val_parser.set_defaults(
        func=lambda args: validate.main(
            [args.environment, "--seed", str(args.seed)]
            if args.seed is not None
            else [args.environment]
        )
    )

    # Research Execution Console Monitor
    mon_parser = sub.add_parser(
        "monitor",
        help="Launch interactive Research Execution Console monitor for benchmark runs.",
    )
    mon_parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Model identifiers to evaluate (default: local Ollama model qwen2.5:0.5b)",
    )
    mon_parser.add_argument(
        "--provider",
        choices=["auto", "ollama", "groq", "meta", "baseten", "openai", "modal", "mock", "offline"],
        default="auto",
        help="Inference provider (default: auto)",
    )
    mon_parser.add_argument(
        "--finals",
        action="store_true",
        help="Run all finals competition models across environments in one go",
    )
    mon_parser.add_argument(
        "--mode",
        choices=["standard", "controls", "ablation", "all"],
        default="standard",
        help="Evaluation mode: standard (primary 4500 episodes), controls (oracle/decoy/random), ablation, or all",
    )
    mon_parser.add_argument(
        "--matched-seeds",
        action="store_true",
        help="Use published matched seed manifest (Seed 01: 1001 .. Seed 30: 1030)",
    )
    mon_parser.add_argument(
        "--interleaved",
        action="store_true",
        default=True,
        help="Execute in interleaved cycle order (Cycle 01: Seed 1001 across all models, Cycle 02: Seed 1002...)",
    )
    mon_parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Number of matched seed cycles (e.g. 30)",
    )
    mon_parser.add_argument(
        "--modal-token",
        type=str,
        default=None,
        help="Modal Bearer Token (defaults to MODAL_TOKEN environment variable)",
    )
    mon_parser.add_argument(
        "--modal-key",
        type=str,
        default=None,
        help="Modal Key ID (defaults to MODAL_KEY environment variable)",
    )
    mon_parser.add_argument(
        "--modal-secret",
        type=str,
        default=None,
        help="Modal Secret Key (defaults to MODAL_SECRET environment variable)",
    )
    mon_parser.add_argument(
        "--modal-api-url",
        type=str,
        default=None,
        help="Modal API URL override",
    )
    mon_parser.add_argument(
        "--env",
        choices=ALL_ENVS + ["all"],
        default=None,
        help="Target environment, or 'all' for all 10 environments (default: all)",
    )
    mon_parser.add_argument(
        "--all-envs",
        action="store_true",
        help="Run benchmark across all 10 environments in one go",
    )
    mon_parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Explicit seeds to evaluate",
    )
    mon_parser.add_argument(
        "--num-seeds",
        type=int,
        default=1,
        help="Number of seeds to run per environment (default: 1)",
    )
    mon_parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum trajectory steps per episode (default: 20)",
    )
    mon_parser.add_argument(
        "--variant",
        type=str,
        default="standard",
        help="Environment variant (default: standard)",
    )
    mon_parser.add_argument(
        "--output",
        type=str,
        default="benchmark_results.json",
        help="Path for saving benchmark results JSON",
    )
    mon_parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable interactive TUI and use streaming plain text output",
    )
    mon_parser.set_defaults(func=lambda args: monitor.main_args(args))

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        ret = args.func(args)
        return int(ret) if isinstance(ret, int) else 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"agent_praxis failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
