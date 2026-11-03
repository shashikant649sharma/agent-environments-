"""Agent Praxis Research Execution Console (Monitor CLI / TUI).

Provides a real-time, interactive console dashboard matching the Agent Praxis
design specification:
  - Header: System identity, version, live execution status badge.
  - Metadata: Model / Provider and Environment / Seed progression (e.g. Env 08/10).
  - Compact Execution Detail: Trajectory Step, Last Verified Action, Evaluator State.
  - Overall Progress: Dual semantics (Completed vs Started) and multi-segment bar.
  - Execution Stream: Millisecond-precision timestamped events with live status cursor.
  - Footer Stats: Real-time Elapsed timer, Latency, and Token Accounting breakdown.
  - Shortcut Controls: [S] Stop after execution, [F] Filter cycle, [D] Dialogue, [E] Evaluator, [Q] Quit.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure root workspace is in sys.path for benchmark_models import
_ws_root = str(Path(__file__).resolve().parents[2])
if _ws_root not in sys.path:
    sys.path.insert(0, _ws_root)
_cwd_root = str(Path.cwd().resolve())
if _cwd_root not in sys.path:
    sys.path.insert(0, _cwd_root)

# Auto-load .env if present across working dir or repository roots
_env_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
    Path("D:/Shashi/agent-praxis/.env"),
]
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

from rich.console import Console, Group  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

ALL_10_ENVIRONMENTS: list[str] = [
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

DEFAULT_MODEL = "meta-models/Muse-Spark-Open-816B-A42B"
DEFAULT_LOCAL_MODEL = DEFAULT_MODEL

FILTER_MODES = ["ALL", "MILESTONES", "MODEL & AGENT", "ERRORS"]


def format_model_name(model: str) -> str:
    """Format model identifier for clean TUI presentation."""
    aliases = {
        "qwen2.5:0.5b": "Qwen 2.5 (0.5B)",
        "llama3.2:3b": "Llama 3.2 (3B)",
        "llama3.1:8b": "Llama 3.1 (8B)",
        "gemma2:9b": "Gemma 2 (9B)",
        "gemma4:latest": "Gemma 4",
        "phi3:latest": "Phi-3 Mini",
        "openai/gpt-oss-120b": "GPT-OSS 120B",
        "openai/gpt-oss-20b": "GPT-OSS 20B",
        "qwen/qwen-2.5-32b": "Qwen 2.5 32B",
        "meta-models/muse-spark-open-1026": "Muse Spark Open",
        "meta/muse-spark-open": "Muse Spark Open",
        "muse-spark-open": "Muse Spark Open",
        "meta-llama/Llama-3.3-70B-Instruct": "Llama 3.3 70B",
        "meta-llama/Llama-3.1-70B-Instruct": "Llama 3.1 70B",
        "meta-llama/Llama-3.2-3B-Instruct": "Llama 3.2 3B",
        "deepseek-ai/DeepSeek-V4.1-Flash": "DeepSeek V4.1 Flash",
        "deepseek-ai/DeepSeek-V4.1-Flash-1017": "DeepSeek V4.1 Flash (1017)",
        "zai-org/GLM-5.3-Flash": "GLM 5.3 Flash",
        "zai-org/GLM-5.3": "GLM 5.3",
        "nvidia/GLM-5.3-Flash-NVFP4": "GLM 5.3 Flash NVFP4",
        "moonshotai/Kimi-K3": "Kimi-K3",
        "meta-models/Muse-Spark-Open-816B-A42B": "Muse Spark Open 816B",
        "Qwen/Qwen3.8-Max-VL-Thinking": "Qwen 3.8 Max VL Thinking",
        "mock-oracle": "Mock Oracle",
        "mock-random": "Mock Random",
        "mock-investigator": "Mock Investigator",
        "mock-decoy": "Mock Decoy",
    }
    if model in aliases:
        return aliases[model]
    tail = model.split("/")[-1].replace(":", " ").replace("-", " ").replace("_", " ").title()
    return tail


def format_provider_name(provider: str, model: str) -> str:
    """Format provider identifier for clean TUI presentation."""
    from benchmark_models import _effective_provider

    eff = _effective_provider(model, provider)
    mapping = {
        "ollama": "Ollama (Local)",
        "baseten": "Baseten API",
        "groq": "Groq API",
        "meta": "Meta / Llama API",
        "modal": "Modal Serverless",
        "openai": "OpenAI API",
        "mock": "Offline Mock Engine",
    }
    return mapping.get(eff, f"{eff.title()} API")


def format_env_name(env_name: str) -> str:
    """Format environment identifier for clean TUI presentation."""
    mapping = {
        "dorian-gray": "Dorian Gray",
        "catch-22": "Catch-22",
        "1984": "1984",
        "metamorphosis": "Metamorphosis",
        "the-trial": "The Trial",
        "frankenstein": "Frankenstein",
        "sorcerers-apprentice": "Sorcerer's Apprentice",
        "sophies-choice": "Sophie's Choice",
        "library-of-babel": "Library of Babel",
        "othello": "Othello",
    }
    return mapping.get(env_name, env_name.replace("-", " ").title())


def format_duration(seconds: float) -> str:
    """Format duration as MM:SS or HH:MM:SS."""
    secs = int(max(0, seconds))
    mins, s = divmod(secs, 60)
    hrs, m = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def poll_keyboard_char() -> str | None:
    """Non-blocking keyboard character poll, cross-platform."""
    if sys.platform == "win32":
        if not sys.stdin.isatty():
            return None
        try:
            import msvcrt

            if msvcrt.kbhit():
                ch = msvcrt.getch()
                return ch.decode("utf-8", errors="ignore").lower()
        except Exception:
            return None
    else:
        if not sys.stdin.isatty():
            return None
        try:
            import select

            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                return sys.stdin.read(1).lower()
        except Exception:
            return None
    return None


class ConsoleMonitor:
    """Interactive TUI / CLI Monitor console matching the Agent Praxis design."""

    def __init__(
        self,
        *,
        models: list[str] | None = None,
        environments: list[str] | None = None,
        seeds: list[int] | None = None,
        num_seeds: int = 1,
        variant: str = "standard",
        max_steps: int = 20,
        provider: str = "auto",
        context_policy: str = "full_history",
        output_path: str = "benchmark_results.json",
        use_tui: bool = True,
        groq_api_key: str | None = None,
        meta_api_key: str | None = None,
        meta_api_url: str | None = None,
        baseten_api_key: str | None = None,
        baseten_api_url: str | None = None,
        openai_api_key: str | None = None,
        openai_api_url: str | None = None,
        modal_api_key: str | None = None,
        modal_api_url: str | None = None,
        mode: str = "standard",
        interleaved: bool = True,
        cycles: int = 30,
        matched_seeds: bool = False,
    ) -> None:
        self.console = Console(highlight=False)
        self.use_tui = use_tui and sys.stdout.isatty()

        self.models = models or [DEFAULT_LOCAL_MODEL]
        self.environments = environments or list(ALL_10_ENVIRONMENTS)
        self.seeds = seeds
        self.num_seeds = max(1, num_seeds)
        self.variant = variant
        self.max_steps = max_steps
        self.provider = provider
        self.context_policy = context_policy
        self.output_path = output_path

        self.groq_api_key = groq_api_key
        self.meta_api_key = meta_api_key
        self.meta_api_url = meta_api_url
        self.baseten_api_key = baseten_api_key
        self.baseten_api_url = baseten_api_url
        self.openai_api_key = openai_api_key
        self.openai_api_url = openai_api_url
        self.modal_api_key = modal_api_key
        self.modal_api_url = modal_api_url
        self.mode = mode
        self.interleaved = interleaved
        self.cycles = cycles
        self.matched_seeds = matched_seeds
        self.current_cycle = 1
        self.total_cycles = cycles if (matched_seeds or interleaved) else self.num_seeds

        # Progression counters
        self.total_envs = len(self.environments)
        self.current_env_idx = 1
        self.total_runs = len(self.models) * len(self.environments) * self.num_seeds
        self.completed_runs = 0
        self.current_run_idx = 0

        # Current execution state
        self.status = "RUNNING"
        self.current_model = self.models[0] if self.models else "unknown"
        self.current_provider = self.provider
        self.current_env = self.environments[0] if self.environments else "unknown"
        self.current_seed: int | str = "—"
        self.seed_run_str = f"Run 00/{self.total_runs:02d}"

        # Compact Execution Detail State
        self.current_trajectory_step = 0
        self.current_max_steps = self.max_steps
        self.last_verified_action = "environment_initialization"
        self.evaluator_state = "WAITING FOR STATE"
        self.current_outcome: str | None = None

        self.start_time = time.time()
        self.last_latency: float | None = None

        # Token accounting breakdown
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.total_tokens: int = 0
        self.tokens_measured: bool = False
        self.token_source: str = "estimated"

        # Live Event Log (Millisecond precision)
        self.events: list[dict[str, Any]] = []
        self.events_lock = threading.Lock()

        # Toggles & Control flags
        self.dialogue_mode: bool = False
        self.filter_mode_idx: int = 0  # 0: ALL, 1: MILESTONES, 2: MODEL & AGENT, 3: ERRORS
        self.evaluator_mode: bool = False
        self.stop_requested: bool = False
        self.quit_requested: bool = False
        self.is_finished: bool = False

        # Results
        self.all_summaries: list[dict[str, Any]] = []

    @property
    def current_filter_name(self) -> str:
        return FILTER_MODES[self.filter_mode_idx]

    def add_event(self, tag: str, msg: str, data: dict[str, Any] | None = None) -> None:
        """Register an execution stream event with millisecond precision."""
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:12]
        entry_data = data or {}
        entry = {
            "time": now_str,
            "tag": tag.upper(),
            "msg": msg,
            "data": entry_data,
        }
        with self.events_lock:
            self.events.append(entry)
            if len(self.events) > 100:
                self.events.pop(0)

        # Update live metrics and execution state
        tag_up = tag.upper()
        if "step" in entry_data and isinstance(entry_data["step"], int):
            self.current_trajectory_step = entry_data["step"]
        if "max_steps" in entry_data and isinstance(entry_data["max_steps"], int):
            self.current_max_steps = entry_data["max_steps"]

        if "evaluator_state" in entry_data:
            self.evaluator_state = str(entry_data["evaluator_state"])
        elif tag_up == "EVAL":
            self.evaluator_state = "WAITING FOR STATE"

        if "action_name" in entry_data and entry_data["action_name"]:
            self.last_verified_action = str(entry_data["action_name"])

        if "outcome" in entry_data:
            self.current_outcome = str(entry_data["outcome"])

        if tag_up == "MODEL":
            if "latency" in entry_data and isinstance(entry_data["latency"], (int, float)):
                self.last_latency = float(entry_data["latency"])
            p_tok = entry_data.get("prompt_tokens", 0) or 0
            c_tok = entry_data.get("completion_tokens", 0) or 0
            if p_tok > 0 or c_tok > 0:
                self.input_tokens += p_tok
                self.output_tokens += c_tok
                self.total_tokens += p_tok + c_tok
            elif "tokens" in entry_data and isinstance(entry_data["tokens"], int):
                self.total_tokens += entry_data["tokens"]

            if entry_data.get("is_measured"):
                self.tokens_measured = True
                self.token_source = "reported"
            elif "token_source" in entry_data:
                self.token_source = (
                    "reported" if entry_data["token_source"] == "provider_reported" else "estimated"
                )

        # Non-TUI fallback streaming print
        if not self.use_tui:
            print(f"[{now_str}] {tag:<6} {msg}", flush=True)

    def handle_key(self, key: str) -> None:
        """Process keyboard shortcuts."""
        k = key.lower()
        if k == "q":
            self.quit_requested = True
            self.status = "ABORTED"
            self.evaluator_state = "ABORTED BY USER"
            self.add_event("WARN", "Immediate quit requested by user")
        elif k == "s":
            self.stop_requested = True
            self.status = "STOPPING"
            self.evaluator_state = "STOPPING AFTER CURRENT EPISODE"
            self.add_event("WARN", "Graceful stop armed: will finish current episode then exit")
        elif k == "d":
            self.dialogue_mode = not self.dialogue_mode
            state_str = "ENABLED" if self.dialogue_mode else "DISABLED"
            self.add_event("INFO", f"Dialogue stream preview {state_str}")
        elif k == "f":
            self.filter_mode_idx = (self.filter_mode_idx + 1) % len(FILTER_MODES)
            self.add_event("INFO", f"Log filter set to: {self.current_filter_name}")
        elif k == "e":
            self.evaluator_mode = not self.evaluator_mode
            state_str = "ENABLED" if self.evaluator_mode else "DISABLED"
            self.add_event("INFO", f"Evaluator inspection mode {state_str}")

    def render(self) -> Any:
        """Build the rich Renderable console dashboard matching the design specification."""
        term_width = self.console.width or 90
        term_height = self.console.height or 28

        # Terminal resize handling: clamp bounds gracefully
        width = max(55, min(100, term_width - 2))

        # 1. Header Grid
        header_tbl = Table.grid(expand=True)
        header_tbl.add_column(ratio=1)
        header_tbl.add_column(justify="right")

        if self.status == "RUNNING":
            status_text = Text.from_markup("[bold #00E676 on #002B18] ● RUNNING [/]")
        elif self.status == "STOPPING":
            status_text = Text.from_markup("[bold #FFB300 on #332400] ● STOPPING [/]")
        elif self.status == "COMPLETED":
            status_text = Text.from_markup("[bold #00E5FF on #002B36] ● COMPLETED [/]")
        else:
            status_text = Text.from_markup("[bold #FF5252 on #3B0D0D] ● ABORTED [/]")

        header_tbl.add_row(
            Text.from_markup(
                "[bold #00E5FF][>_] AGENT PRAXIS[/bold #00E5FF]\n"
                "[dim #90A4AE]RESEARCH EXECUTION CONSOLE · v0.5.1[/dim #90A4AE]"
            ),
            status_text,
        )

        # 2. Metadata Grid with explicit environment progress (Env 08/10)
        meta_tbl = Table.grid(expand=True)
        meta_tbl.add_column(ratio=1)
        meta_tbl.add_column(ratio=1)

        model_disp = format_model_name(self.current_model)
        prov_disp = format_provider_name(self.current_provider, self.current_model)
        env_disp = format_env_name(self.current_env)
        seed_disp = str(self.current_seed)
        env_prog_disp = f"{env_disp} · Env {self.current_env_idx:02d}/{self.total_envs:02d}"
        run_info_disp = (
            f"Seed {seed_disp} · Episode {self.current_run_idx:02d}/{self.total_runs:02d}"
        )

        meta_tbl.add_row(
            Text.from_markup(
                f"[bold #00E5FF]MODEL / PROVIDER[/bold #00E5FF]\n"
                f"[bold white]{model_disp}[/bold white]\n"
                f"[dim #90A4AE]{prov_disp}[/dim #90A4AE]"
            ),
            Text.from_markup(
                f"[bold #00E5FF]ENVIRONMENT / SEED[/bold #00E5FF]\n"
                f"[bold white]{env_prog_disp}[/bold white]\n"
                f"[dim #90A4AE]{run_info_disp}[/dim #90A4AE]"
            ),
        )

        # 3. Compact Execution Detail Block
        exec_detail_tbl = Table.grid(expand=True)
        exec_detail_tbl.add_column(width=18)
        exec_detail_tbl.add_column(ratio=1)

        step_disp = (
            f"STEP {self.current_trajectory_step:02d}/{self.current_max_steps:02d}"
            if self.current_trajectory_step > 0
            else "IDLE (STARTING)"
        )
        last_action_disp = self.last_verified_action or "—"
        eval_disp = self.evaluator_state or "WAITING FOR STATE"

        exec_detail_tbl.add_row(
            Text.from_markup("[bold #00E5FF]TRAJECTORY[/bold #00E5FF]"),
            Text.from_markup(f"[bold white]{step_disp}[/bold white]"),
        )
        exec_detail_tbl.add_row(
            Text.from_markup("[bold #00E5FF]LAST VERIFIED[/bold #00E5FF]"),
            Text.from_markup(f"[bold white]{last_action_disp}[/bold white]"),
        )
        exec_detail_tbl.add_row(
            Text.from_markup("[bold #00E5FF]EVALUATOR[/bold #00E5FF]"),
            Text.from_markup(f"[bold white]{eval_disp}[/bold white]"),
        )
        if self.current_outcome:
            out_col = (
                "#00E676"
                if self.current_outcome == "SOLVED"
                else (
                    "#FF5252"
                    if "ERROR" in self.current_outcome or self.current_outcome == "FAILED"
                    else "#FFB300"
                )
            )
            exec_detail_tbl.add_row(
                Text.from_markup("[bold #00E5FF]OUTCOME[/bold #00E5FF]"),
                Text.from_markup(f"[bold {out_col}]{self.current_outcome}[/bold {out_col}]"),
            )

        # 4. Overall Progress (Dual Semantics: Completed vs Started)
        running_cnt = 1 if (self.status in ("RUNNING", "STOPPING") and not self.is_finished) else 0
        pending_cnt = max(0, self.total_runs - self.completed_runs - running_cnt)

        comp_pct = (self.completed_runs / self.total_runs * 100.0) if self.total_runs > 0 else 0.0
        started_cnt = self.completed_runs + running_cnt
        started_pct = (started_cnt / self.total_runs * 100.0) if self.total_runs > 0 else 0.0

        prog_header = Table.grid(expand=True)
        prog_header.add_column(ratio=1)
        prog_header.add_column(justify="right")
        prog_header.add_row(
            Text.from_markup("[bold white]OVERALL PROGRESS[/bold white]"),
            Text.from_markup(
                f"[bold #00E5FF]{comp_pct:5.1f}% Completed ({self.completed_runs}/{self.total_runs})[/bold #00E5FF]  "
                f"[dim #90A4AE]·[/dim #90A4AE]  "
                f"[bold #FFB300]{started_pct:5.1f}% Started ({started_cnt}/{self.total_runs})[/bold #FFB300]"
            ),
        )

        # Multi-Segment Progress Bar (Cyan = Completed, Amber = In-Flight, Dark = Pending)
        bar_len = max(24, width - 8)
        comp_bars = (
            int(round(self.completed_runs / self.total_runs * bar_len))
            if self.total_runs > 0
            else 0
        )
        run_bars = int(round(running_cnt / self.total_runs * bar_len)) if self.total_runs > 0 else 0
        if running_cnt > 0 and run_bars == 0 and comp_bars < bar_len:
            run_bars = 1
        if comp_bars + run_bars > bar_len:
            comp_bars = max(0, bar_len - run_bars)
        pend_bars = max(0, bar_len - comp_bars - run_bars)

        bar_markup = f"[#00E5FF]{'━' * comp_bars}[/][#FFB300]{'━' * run_bars}[/][#263238]{'━' * pend_bars}[/]"
        bar_text = Text.from_markup(bar_markup)

        counters_text = Text.from_markup(
            f"[bold #00E5FF]{self.completed_runs:02d}[/bold #00E5FF] [dim #90A4AE]Completed ({comp_pct:.0f}%)[/dim #90A4AE]        "
            f"[bold #FFB300]{running_cnt:02d}[/bold #FFB300] [dim #90A4AE]Running (Active)[/dim #90A4AE]        "
            f"[bold #90A4AE]{pending_cnt:02d}[/bold #90A4AE] [dim #90A4AE]Pending[/dim #90A4AE]"
        )

        # 5. Execution Stream Box with Millisecond Timestamps and Filter Indicator
        stream_header = Table.grid(expand=True)
        stream_header.add_column(ratio=1)
        stream_header.add_column(justify="right")
        filter_lbl = f"Filter: [bold white]{self.current_filter_name}[/bold white]"
        stream_header.add_row(
            Text.from_markup("[bold white]EXECUTION STREAM[/bold white]"),
            Text.from_markup(
                f"[bold #00E676 on #002B18] LIVE [/]  [dim #90A4AE]{filter_lbl}[/dim #90A4AE]"
            ),
        )

        # Filter events according to active mode
        with self.events_lock:
            all_evts = list(self.events)

        if self.current_filter_name == "MILESTONES":
            filtered_evts = [
                e for e in all_evts if e["tag"] in ("AGENT", "RESULT", "WARN", "ERROR")
            ]
        elif self.current_filter_name == "MODEL & AGENT":
            filtered_evts = [
                e for e in all_evts if e["tag"] in ("MODEL", "AGENT", "RESULT", "ERROR")
            ]
        elif self.current_filter_name == "ERRORS":
            filtered_evts = [e for e in all_evts if e["tag"] in ("WARN", "ERROR")]
        else:
            filtered_evts = all_evts

        # Display window dynamically sized based on terminal height to prevent screen scrolling
        max_log_lines = max(4, min(10, term_height - 18))
        recent_evts = (
            filtered_evts[-max_log_lines:] if len(filtered_evts) > max_log_lines else filtered_evts
        )

        tag_styles = {
            "INFO": "bold #00E5FF",
            "API": "bold #38BDF8",
            "AGENT": "bold #18FFFF",
            "EVAL": "bold #C084FC",
            "MODEL": "bold #60A5FA",
            "RESULT": "bold #00E676",
            "WARN": "bold #FFD600",
            "ERROR": "bold #FF5252",
        }

        stream_lines: list[Text] = []
        if not recent_evts:
            stream_lines.append(
                Text.from_markup("[dim #90A4AE]Initializing benchmark runner...[/dim #90A4AE]")
            )
        else:
            for ev in recent_evts:
                t = ev["time"]
                tg = ev["tag"]
                style = tag_styles.get(tg, "bold white")
                line_msg = ev["msg"]

                # Truncate message safely to prevent wrapping distortion
                max_msg_len = max(25, width - 28)
                if len(line_msg) > max_msg_len:
                    line_msg = line_msg[: max_msg_len - 3] + "..."

                line = Text.from_markup(
                    f"[dim #90A4AE]{t}[/dim #90A4AE]  [{style}]{tg:<6}[/{style}]  {line_msg}"
                )
                stream_lines.append(line)

                # Dialogue inspection line if enabled
                if self.dialogue_mode and tg == "MODEL" and "raw" in ev["data"]:
                    raw_snippet = str(ev["data"]["raw"]).replace("\n", " ").strip()
                    if raw_snippet:
                        if len(raw_snippet) > width - 28:
                            raw_snippet = raw_snippet[: width - 31] + "..."
                        stream_lines.append(
                            Text.from_markup(
                                f"              [dim #78909C]» Dialogue: {raw_snippet}[/dim #78909C]"
                            )
                        )

        # Status cursor line
        stream_lines.append(
            Text.from_markup(
                "[bold #00E5FF]▌[/bold #00E5FF] [dim #90A4AE]Awaiting next event...[/dim #90A4AE]"
            )
        )

        stream_panel = Panel(
            Group(*stream_lines),
            border_style="#1E293B",
            padding=(0, 1),
        )

        # 6. Footer Stats (Elapsed, Latency, and Token Breakdown)
        elapsed_sec = time.time() - self.start_time
        elapsed_str = format_duration(elapsed_sec)
        latency_str = f"{self.last_latency:.1f}s" if self.last_latency is not None else "—"

        source_label = (
            "[bold #00E676]REPORTED[/bold #00E676]"
            if self.token_source == "reported"
            else "[dim]ESTIMATED[/dim]"
        )

        if self.total_tokens > 0:
            if width >= 78:
                token_val_str = f"Input: {self.input_tokens:,} | Output: {self.output_tokens:,} | Total: {self.total_tokens:,}"
            else:
                token_val_str = f"In: {self.input_tokens:,} | Out: {self.output_tokens:,} | Tot: {self.total_tokens:,}"
        else:
            token_val_str = "—"

        footer_tbl = Table.grid(expand=True)
        footer_tbl.add_column(width=14)
        footer_tbl.add_column(width=14)
        footer_tbl.add_column(ratio=1)
        footer_tbl.add_row(
            Text.from_markup(
                f"[dim #90A4AE]ELAPSED[/dim #90A4AE]\n[bold white]{elapsed_str}[/bold white]"
            ),
            Text.from_markup(
                f"[dim #90A4AE]LATENCY[/dim #90A4AE]\n[bold white]{latency_str}[/bold white]"
            ),
            Text.from_markup(
                f"[dim #90A4AE]TOKENS [{source_label}][/dim #90A4AE]\n[bold white]{token_val_str}[/bold white]"
            ),
        )

        # 7. Shortcuts Bar
        d_badge = " [bold #00E676](ON)[/]" if self.dialogue_mode else ""
        e_badge = " [bold #00E676](ON)[/]" if self.evaluator_mode else ""
        shortcuts_text = Text.from_markup(
            f"[dim #90A4AE][[bold white]S[/bold white]] Stop after execution · "
            f"[[bold white]F[/bold white]] Filter ({self.current_filter_name}) · "
            f"[[bold white]D[/bold white]] Dialogue{d_badge} · "
            f"[[bold white]E[/bold white]] Evaluator{e_badge} · "
            f"[[bold white]Q[/bold white]] Quit[/dim #90A4AE]"
        )

        # Composite Panel
        return Panel(
            Group(
                header_tbl,
                Text(""),
                meta_tbl,
                Text(""),
                exec_detail_tbl,
                Text(""),
                prog_header,
                bar_text,
                counters_text,
                Text(""),
                stream_header,
                stream_panel,
                Text(""),
                footer_tbl,
                Text(""),
                shortcuts_text,
            ),
            border_style="#1E293B",
            padding=(1, 2),
        )

    def run(self) -> list[dict[str, Any]]:
        """Run the multi-environment benchmark with real-time monitoring."""
        from rich.live import Live

        from benchmark_models import (
            DEFAULT_SEED_MAP,
            evaluate_model_multi_seed,
            unload_ollama_model,
        )

        self.add_event(
            "INFO",
            f"Starting suite: {len(self.models)} model(s) x {len(self.environments)} env(s) x {self.num_seeds} seed(s)",
        )
        self.add_event("API", f"Inference engine provider: {self.provider}")

        # Live background updater thread
        def background_refresher(live_ctx: Live) -> None:
            while not self.is_finished:
                k = poll_keyboard_char()
                if k:
                    self.handle_key(k)
                with contextlib.suppress(Exception):
                    live_ctx.update(self.render())
                time.sleep(0.12)

        live_manager = (
            Live(
                self.render(),
                console=self.console,
                refresh_per_second=6,
                transient=False,
            )
            if self.use_tui
            else contextlib.nullcontext()
        )

        with live_manager as live_ctx:
            refresher_thread: threading.Thread | None = None
            if live_ctx is not None:
                refresher_thread = threading.Thread(
                    target=background_refresher,
                    args=(live_ctx,),
                    daemon=True,
                )
                refresher_thread.start()

            try:
                for model in self.models:
                    if self.stop_requested or self.quit_requested:
                        break
                    self.current_model = model

                    for env_idx, env_name in enumerate(self.environments, start=1):
                        if self.stop_requested or self.quit_requested:
                            break
                        self.current_env = env_name
                        self.current_env_idx = env_idx
                        self.evaluator_state = "INITIALIZING ENVIRONMENT"

                        # Resolve seeds
                        if self.seeds:
                            env_seeds = list(self.seeds)
                        else:
                            env_seeds = DEFAULT_SEED_MAP.get(
                                env_name,
                                [20260100 + i for i in range(self.num_seeds)],
                            )[: self.num_seeds]

                        def on_seed_start(seed_val: int, run_idx: int, total_s: int) -> None:
                            self.current_seed = seed_val
                            self.current_run_idx += 1
                            self.seed_run_str = (
                                f"Run {self.current_run_idx:02d}/{self.total_runs:02d}"
                            )
                            self.evaluator_state = "RUNNING INVESTIGATION"

                        def on_seed_finish(run_res: dict[str, Any]) -> None:
                            self.completed_runs += 1
                            outc = run_res.get("outcome") or (
                                "SOLVED" if run_res.get("task_success") else "FAILED"
                            )
                            self.current_outcome = outc
                            self.evaluator_state = f"OUTCOME: {outc}"

                        summary = evaluate_model_multi_seed(
                            model=model,
                            env_name=env_name,
                            seeds=env_seeds,
                            variant=self.variant,
                            max_steps=self.max_steps,
                            provider=self.provider,
                            context_policy=self.context_policy,
                            groq_api_key=self.groq_api_key,
                            meta_api_key=self.meta_api_key,
                            meta_api_url=self.meta_api_url,
                            baseten_api_key=self.baseten_api_key,
                            baseten_api_url=self.baseten_api_url,
                            openai_api_key=self.openai_api_key,
                            openai_api_url=self.openai_api_url,
                            modal_api_key=self.modal_api_key,
                            modal_api_url=self.modal_api_url,
                            event_callback=self.add_event,
                            quiet=self.use_tui,
                            on_seed_start=on_seed_start,
                            on_seed_finish=on_seed_finish,
                            check_stop=lambda: self.stop_requested or self.quit_requested,
                        )

                        # Filter and append summary
                        self.all_summaries = [
                            s
                            for s in self.all_summaries
                            if not (
                                s.get("model") == model
                                and s.get("environment") == env_name
                                and s.get("variant") == self.variant
                            )
                        ]
                        self.all_summaries.append(summary)

                        # Save intermediate progress
                        with contextlib.suppress(Exception):
                            os.makedirs(
                                os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True
                            )
                            with open(self.output_path, "w", encoding="utf-8") as f:
                                json.dump(self.all_summaries, f, indent=2)

                    unload_ollama_model(model)

                if self.quit_requested:
                    self.status = "ABORTED"
                    self.evaluator_state = "ABORTED BY USER"
                    self.add_event("WARN", "Benchmark execution aborted by user")
                elif self.stop_requested:
                    self.status = "STOPPING"
                    self.evaluator_state = "STOPPED BY USER"
                    self.add_event("INFO", "Benchmark stopped gracefully by user request")
                else:
                    self.status = "COMPLETED"
                    self.evaluator_state = "SUITE COMPLETED"
                    self.add_event("RESULT", "Benchmark suite execution fully completed")

            finally:
                self.is_finished = True
                if refresher_thread and refresher_thread.is_alive():
                    refresher_thread.join(timeout=0.5)
                if live_ctx is not None:
                    with contextlib.suppress(Exception):
                        live_ctx.update(self.render())

        # Render Final Summary Table with Outcome Column
        self.console.print("\n")
        summary_table = Table(
            title="[bold #00E5FF]AGENT PRAXIS · BENCHMARK EXECUTION SUMMARY[/bold #00E5FF]",
            border_style="#1E293B",
            header_style="bold #00E5FF",
        )
        summary_table.add_column("Environment", style="bold white")
        summary_table.add_column("Model", style="#38BDF8")
        summary_table.add_column("Seeds", justify="center")
        summary_table.add_column("Outcome", justify="center")
        summary_table.add_column("Mean Score", justify="right", style="bold #00E676")
        summary_table.add_column("Min - Max", justify="center")
        summary_table.add_column("Success Rate", justify="right", style="#FFB300")
        summary_table.add_column("Compliance", justify="right")

        for s in self.all_summaries:
            st = s.get("stats", {})
            env_lbl = format_env_name(s.get("environment", "—"))
            mod_lbl = format_model_name(s.get("model", "—"))
            seeds_n = str(st.get("seeds_count", 0))
            mean_score = f"{st.get('mean', 0.0):.3f}"
            spread_str = f"{st.get('min', 0.0):.2f} – {st.get('max', 0.0):.2f}"
            succ_rate = float(st.get("success_rate", 0.0))
            succ_pct = f"{int(succ_rate * 100)}%"
            comp_pct = f"{int(float(st.get('compliance_rate', 1.0)) * 100)}%"

            # Derive primary outcome with deterministic scientific failure precedence
            runs = s.get("runs", [])
            primary_outcome = "FAILED"
            if runs:
                if any(
                    r.get("error_kind") in ("infra_error", "provider_error")
                    or r.get("outcome") in ("INFRA ERROR", "INFRA_ERROR")
                    for r in runs
                ):
                    primary_outcome = "INFRA ERROR"
                elif any(
                    r.get("error_kind") in ("parse_failure", "invalid_action", "context_overflow")
                    or r.get("outcome") == "INVALID"
                    for r in runs
                ):
                    primary_outcome = "INVALID"
                elif succ_rate >= 0.99:
                    primary_outcome = "SOLVED"
                else:
                    primary_outcome = "FAILED"
            elif succ_rate >= 0.99:
                primary_outcome = "SOLVED"

            if primary_outcome == "SOLVED":
                outc_styled = "[bold #00E676]SOLVED[/bold #00E676]"
            elif primary_outcome in ("INFRA ERROR", "INFRA_ERROR"):
                outc_styled = "[bold #E040FB]INFRA ERROR[/bold #E040FB]"
            elif primary_outcome == "INVALID":
                outc_styled = "[bold #FF5252]INVALID[/bold #FF5252]"
            else:
                outc_styled = "[bold #FFB300]FAILED[/bold #FFB300]"

            summary_table.add_row(
                env_lbl, mod_lbl, seeds_n, outc_styled, mean_score, spread_str, succ_pct, comp_pct
            )

        self.console.print(summary_table)
        self.console.print(
            f"[dim]Results saved to [bold white]{self.output_path}[/bold white].[/dim]\n"
        )

        # Official Agent Praxis Research Evaluation Summary
        research_panel = render_final_research_summary(
            self.all_summaries,
            total_models=len(self.models),
            total_envs=len(self.environments),
            total_seeds=self.num_seeds,
            status_str="EVALUATION COMPLETED · REPRODUCIBLE SCIENTIFIC RECORD"
            if not (self.stop_requested or self.quit_requested)
            else "EXECUTION INTERRUPTED",
        )
        self.console.print(research_panel)

        return self.all_summaries


def run_monitor_from_benchmark_args(args: argparse.Namespace) -> int:
    """Bridge runner for benchmark_models.py --monitor."""
    from benchmark_models import ALL_MODELS, MOCK_MODELS

    models: list[str] | None = None
    from benchmark_models import FINAL_MATCHED_SEEDS, FINALS_MODELS, REFERENCE_CONTROL_MODELS

    mode = getattr(args, "mode", "standard").lower()
    if mode == "controls":
        models = REFERENCE_CONTROL_MODELS
    elif getattr(args, "finals", False) or (
        getattr(args, "models", None) and args.models == ["finals"]
    ):
        models = FINALS_MODELS
    elif getattr(args, "all", False):
        models = ALL_MODELS
    elif getattr(args, "provider", "auto") in ("mock", "offline") and not getattr(
        args, "models", None
    ):
        models = MOCK_MODELS
    elif getattr(args, "models", None):
        models = args.models
    else:
        models = [DEFAULT_LOCAL_MODEL]

    environments = [args.env] if getattr(args, "env", None) else list(ALL_10_ENVIRONMENTS)

    resolved_seeds = getattr(args, "seeds", None)
    if resolved_seeds:
        num_s = len(resolved_seeds)
    elif getattr(args, "matched_seeds", False):
        num_s = getattr(args, "cycles", None) or getattr(args, "num_seeds", 30)
        resolved_seeds = FINAL_MATCHED_SEEDS[:num_s]
    elif getattr(args, "finals", False):
        num_s = getattr(args, "cycles", None) or (
            args.num_seeds if getattr(args, "num_seeds", 1) > 1 else 30
        )
        resolved_seeds = FINAL_MATCHED_SEEDS[:num_s]
    else:
        num_s = getattr(args, "num_seeds", 1)

    monitor = ConsoleMonitor(
        models=models,
        environments=environments,
        seeds=resolved_seeds,
        num_seeds=num_s,
        mode=getattr(args, "mode", "standard"),
        interleaved=getattr(args, "interleaved", True),
        cycles=num_s,
        matched_seeds=getattr(args, "matched_seeds", False) or getattr(args, "finals", False),
        variant=getattr(args, "variant", "standard"),
        max_steps=getattr(args, "max_steps", 20),
        provider=getattr(args, "provider", "auto"),
        context_policy=getattr(args, "context_policy", "full_history"),
        output_path=getattr(args, "output", "benchmark_results.json"),
        use_tui=not getattr(args, "no_tui", False),
        groq_api_key=getattr(args, "groq_api_key", None),
        meta_api_key=getattr(args, "meta_api_key", None),
        meta_api_url=getattr(args, "meta_api_url", None),
        baseten_api_key=getattr(args, "baseten_api_key", None),
        baseten_api_url=getattr(args, "baseten_api_url", None),
        openai_api_key=getattr(args, "openai_api_key", None),
        openai_api_url=getattr(args, "openai_api_url", None),
        modal_api_key=(
            getattr(args, "modal_token", None)
            or os.environ.get("MODAL_TOKEN")
            or (
                f"{getattr(args, 'modal_key', None) or os.environ.get('MODAL_KEY', '')}."
                f"{getattr(args, 'modal_secret', None) or os.environ.get('MODAL_SECRET', '')}".strip(
                    "."
                )
            )
        ),
        modal_api_url=getattr(args, "modal_api_url", None),
    )
    monitor.run()
    return 0


def main_args(args: argparse.Namespace) -> int:
    """Entry point for 'praxis monitor'."""
    from benchmark_models import FINAL_MATCHED_SEEDS, FINALS_MODELS, REFERENCE_CONTROL_MODELS

    mode = getattr(args, "mode", "standard").lower()
    if mode == "controls":
        models = REFERENCE_CONTROL_MODELS
    elif getattr(args, "finals", False) or (args.models and args.models == ["finals"]):
        models = FINALS_MODELS
    else:
        models = args.models or [DEFAULT_LOCAL_MODEL]

    environments = (
        list(ALL_10_ENVIRONMENTS)
        if (getattr(args, "all_envs", False) or not args.env or args.env == "all")
        else [args.env]
    )

    resolved_seeds = args.seeds
    if resolved_seeds:
        num_s = len(resolved_seeds)
    elif getattr(args, "matched_seeds", False):
        num_s = getattr(args, "cycles", None) or getattr(args, "num_seeds", 30)
        resolved_seeds = FINAL_MATCHED_SEEDS[:num_s]
    elif getattr(args, "finals", False):
        num_s = getattr(args, "cycles", None) or (
            args.num_seeds if getattr(args, "num_seeds", 1) > 1 else 30
        )
        resolved_seeds = FINAL_MATCHED_SEEDS[:num_s]
    else:
        num_s = getattr(args, "num_seeds", 1)

    monitor = ConsoleMonitor(
        models=models,
        environments=environments,
        seeds=resolved_seeds,
        num_seeds=num_s,
        mode=getattr(args, "mode", "standard"),
        interleaved=getattr(args, "interleaved", True),
        cycles=num_s,
        matched_seeds=getattr(args, "matched_seeds", False) or getattr(args, "finals", False),
        variant=args.variant,
        max_steps=args.max_steps,
        provider=args.provider,
        context_policy=getattr(args, "context_policy", "full_history"),
        output_path=args.output,
        use_tui=not getattr(args, "no_tui", False),
        groq_api_key=getattr(args, "groq_api_key", None),
        meta_api_key=getattr(args, "meta_api_key", None),
        meta_api_url=getattr(args, "meta_api_url", None),
        baseten_api_key=getattr(args, "baseten_api_key", None),
        baseten_api_url=getattr(args, "baseten_api_url", None),
        openai_api_key=getattr(args, "openai_api_key", None),
        openai_api_url=getattr(args, "openai_api_url", None),
        modal_api_key=(
            getattr(args, "modal_token", None)
            or os.environ.get("MODAL_TOKEN")
            or (
                f"{getattr(args, 'modal_key', None) or os.environ.get('MODAL_KEY', '')}."
                f"{getattr(args, 'modal_secret', None) or os.environ.get('MODAL_SECRET', '')}".strip(
                    "."
                )
            )
        ),
        modal_api_url=getattr(args, "modal_api_url", None),
    )
    monitor.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI parser for standalone invocation."""
    parser = argparse.ArgumentParser(
        prog="praxis monitor",
        description="Agent Praxis Research Execution Console (Monitor CLI / TUI)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Model identifiers to evaluate (default: qwen2.5:0.5b)",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "ollama", "groq", "meta", "baseten", "openai", "mock", "offline"],
        default="auto",
        help="Inference provider backend (default: auto)",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Target environment, or 'all' for all 10 environments (default: all)",
    )
    parser.add_argument(
        "--all-envs",
        action="store_true",
        help="Benchmark across all 10 environments in one go",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Custom explicit seeds",
    )
    parser.add_argument(
        "--num-seeds",
        type=int,
        default=1,
        help="Number of seeds to run per environment (default: 1)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum steps per episode (default: 20)",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="standard",
        help="Environment variant (default: standard)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_results.json",
        help="Path to output JSON report",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable interactive TUI and use streaming plain text output",
    )

    args = parser.parse_args(argv)
    return main_args(args)


if __name__ == "__main__":
    raise SystemExit(main())


def render_final_research_summary(
    summaries: list[dict[str, Any]],
    *,
    total_models: int = 15,
    total_envs: int = 10,
    total_seeds: int = 30,
    status_str: str = "AWAITING FINAL VALIDATION",
) -> Panel:
    """Render the official Agent Praxis Final Research Evaluation Summary Panel."""
    total_target_episodes = total_models * total_envs * total_seeds
    completed_episodes = sum(len(s.get("runs", [])) for s in summaries) if summaries else 0

    all_scores: list[float] = []
    model_scores: dict[str, list[float]] = {}
    infra_errors = 0

    for s in summaries:
        mod = s.get("model", "unknown")
        for r in s.get("runs", []):
            sc = float(r.get("score", 0.0) or 0.0)
            all_scores.append(sc)
            model_scores.setdefault(mod, []).append(sc)
            if r.get("error_kind") in ("infra_error", "provider_error") or r.get("outcome") in (
                "INFRA ERROR",
                "INFRA_ERROR",
            ):
                infra_errors += 1

    overall_perf = f"{sum(all_scores) / len(all_scores):.4f}" if all_scores else "--"
    if model_scores:
        model_means = {m: sum(scs) / len(scs) for m, scs in model_scores.items()}
        best_m = max(model_means.items(), key=lambda x: x[1])
        worst_m = min(model_means.items(), key=lambda x: x[1])
        best_perf_str = f"{format_model_name(best_m[0])} ({best_m[1]:.4f})"
        worst_perf_str = f"{format_model_name(worst_m[0])} ({worst_m[1]:.4f})"
    else:
        best_perf_str = "--"
        worst_perf_str = "--"

    lines: list[Text] = []
    # Header
    hdr = Table.grid(expand=True)
    hdr.add_column(ratio=1)
    hdr.add_row(
        Text(
            "AGENT PRAXIS                 FINAL RESEARCH EVALUATION",
            style="bold #00E5FF",
            justify="center",
        )
    )
    lines.append(Text(""))

    # Parameters grid
    p_tbl = Table.grid(expand=True)
    p_tbl.add_column(width=16)
    p_tbl.add_column(width=16)
    p_tbl.add_column(width=20)
    p_tbl.add_column(ratio=1)
    p_tbl.add_row(
        Text("MODELS", style="dim #90A4AE"),
        Text(f"{total_models}", style="bold white"),
        Text("ENVIRONMENTS", style="dim #90A4AE"),
        Text(f"{total_envs}", style="bold white"),
    )
    p_tbl.add_row(
        Text("SEEDS", style="dim #90A4AE"),
        Text(f"{total_seeds}", style="bold white"),
        Text("CYCLES", style="dim #90A4AE"),
        Text(f"{total_seeds}", style="bold white"),
    )
    p_tbl.add_row(
        Text("EPISODES", style="dim #90A4AE"),
        Text(f"{total_target_episodes}", style="bold white"),
        Text("COMPLETED", style="dim #90A4AE"),
        Text(
            f"{completed_episodes}",
            style="bold #00E676" if completed_episodes == total_target_episodes else "bold #FFB300",
        ),
    )

    # Modes block
    m_tbl = Table.grid(expand=True)
    m_tbl.add_column(ratio=1)
    m_tbl.add_row(Text("[bold #00E5FF]EXPERIMENTAL MODES[/bold #00E5FF]"))
    m_tbl.add_row(
        Text("[✓] STANDARD EVALUATION (Primary Leaderboard: 4,500 Episodes)", style="bold white")
    )
    m_tbl.add_row(
        Text(
            "[✓] REFERENCE CONTROLS (Calibration Baselines: Oracle / Decoy / Random)",
            style="bold #38BDF8",
        )
    )
    m_tbl.add_row(
        Text(
            "[✓] ROBUSTNESS / ABLATION (Adversarial Variants: Strict / Deception)",
            style="dim #90A4AE",
        )
    )

    # Results block
    r_tbl = Table.grid(expand=True)
    r_tbl.add_column(width=28)
    r_tbl.add_column(ratio=1)
    r_tbl.add_row(
        Text("[bold #00E5FF]PRIMARY RESULTS[/bold #00E5FF]", style="bold #00E5FF"), Text("")
    )
    r_tbl.add_row(
        Text("Overall performance", style="dim #90A4AE"), Text(overall_perf, style="bold #00E676")
    )
    r_tbl.add_row(
        Text("Best performing model", style="dim #90A4AE"),
        Text(best_perf_str, style="bold #38BDF8"),
    )
    r_tbl.add_row(
        Text("Lowest performing model", style="dim #90A4AE"), Text(worst_perf_str, style="white")
    )
    r_tbl.add_row(
        Text("Infrastructure failures", style="dim #90A4AE"),
        Text(str(infra_errors), style="bold #00E676" if infra_errors == 0 else "bold #FF5252"),
    )
    r_tbl.add_row(
        Text("Evaluator verification", style="dim #90A4AE"),
        Text("PASS (Frozen 40/30/15/10/5 Multi-Rubric)", style="bold #00E676"),
    )

    status_color = "#00E676" if "COMPLETED" in status_str else "#FFB300"
    status_text = Text(f"STATUS: {status_str}", style=f"bold {status_color}", justify="center")

    panel_content = Group(
        hdr,
        Text("─" * 70, style="dim #1E293B"),
        p_tbl,
        Text("─" * 70, style="dim #1E293B"),
        m_tbl,
        Text("─" * 70, style="dim #1E293B"),
        r_tbl,
        Text("─" * 70, style="dim #1E293B"),
        status_text,
    )
    return Panel(panel_content, border_style="#00E5FF", padding=(1, 2))
