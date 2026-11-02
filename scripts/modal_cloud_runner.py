"""Modal Cloud Runner for Agent Praxis 30-Seed Finals Benchmark.

Executes the entire 30-seed, 10-environment, 9-model research benchmark
(2,700 episodes) entirely in Modal cloud infrastructure with a persistent
Modal Volume.

Usage:
    # 1. Run detached in Modal cloud (you can close your PC immediately):
    modal run --detach scripts/modal_cloud_runner.py

    # 2. Check logs at any time from any device:
    modal app list

    # 3. Retrieve completed results and WAL checkpoints to local disk:
    modal volume get praxis-research-volume thirty_seed research/results/
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import modal

# Initialize Modal App & persistent Volume
app = modal.App("agent-praxis-cloud-finals")
results_volume = modal.Volume.from_name("praxis-research-volume", create_if_missing=True)


def _resolve_host_git_commit() -> str:
    """Resolve current local git commit to inject into headless container."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        sha = res.stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "-uno"], capture_output=True, text=True)
        if status.returncode == 0 and status.stdout.strip():
            return f"{sha}-dirty"
        return sha
    except Exception:
        return "5008d8f098b4a0045d5ee78e157aa1c08b2a12a0"


GIT_COMMIT_SHA = _resolve_host_git_commit()

# Build Debian Slim image with Agent Praxis package and dependencies
benchmark_image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"PRAXIS_GIT_COMMIT": GIT_COMMIT_SHA})
    .pip_install(
        "httpx>=0.25",
        "numpy>=1.24",
        "pydantic>=2.0",
        "gymnasium>=0.29",
        "rich>=13.0",
    )
    .add_local_python_source("agent_praxis")
    .add_local_file("benchmark_models.py", "/root/benchmark_models.py")
    .add_local_file(".env", "/root/.env")
)


@app.function(
    image=benchmark_image,
    volumes={"/root/research_volume": results_volume},
    timeout=86400,  # 24-hour maximum execution timeout
    cpu=2.0,
    memory=2048,
)
def run_cloud_benchmark(cycles: int = 5, env: str = "", model: str = "", output_name: str = "") -> int:
    """Execute the benchmark in Modal cloud with persistent volume storage."""
    print(f"=== Starting Agent Praxis Cloud Benchmark on Modal ({cycles} cycles) ===", flush=True)
    os.chdir("/root")

    if output_name:
        seed_dir = "custom"
        out_file = output_name
    elif cycles == 5:
        seed_dir = "five_seed"
        out_file = "finals_5seed.json"
    elif cycles == 30:
        seed_dir = "thirty_seed"
        out_file = "finals_full.json"
    else:
        seed_dir = f"{cycles}_seed"
        out_file = f"finals_{cycles}seed.json"

    out_dir = Path(f"/root/research_volume/{seed_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    output_json = out_dir / out_file

    cmd = [
        sys.executable,
        "/root/benchmark_models.py",
        "--matched-seeds",
        "--interleaved",
        "--cycles", str(cycles),
        "--monitor",
        "--no-tui",
        "--output", str(output_json),
    ]

    if model:
        cmd.extend(["--models", model])
    else:
        cmd.append("--finals")

    if env:
        cmd.extend(["--env", env])
    else:
        cmd.append("--all-envs")

    print(f"Executing: {' '.join(cmd)}", flush=True)
    print(f"Persisting results to Modal Volume: {seed_dir}/{out_file}", flush=True)
    env_vars = os.environ.copy()
    if not env_vars.get("PRAXIS_GIT_COMMIT"):
        env_vars["PRAXIS_GIT_COMMIT"] = GIT_COMMIT_SHA

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env_vars,
    )

    line_count = 0
    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            print(line, end="", flush=True)
            line_count += 1
            # Commit results volume on milestones
            if "Cycle" in line or "Completed episode" in line or line_count % 50 == 0:
                results_volume.commit()

    proc.wait()
    results_volume.commit()
    print(f"\n=== Benchmark finished with exit code {proc.returncode} ===", flush=True)
    return proc.returncode


@app.local_entrypoint()
def main(cycles: int = 5, env: str = "", model: str = "", output_name: str = "") -> None:
    """Trigger the cloud execution."""
    target_desc = f"env={env or 'all'}, model={model or 'finals'}, cycles={cycles}"
    print(f"Triggering cloud benchmark on Modal ({target_desc})...")
    exit_code = run_cloud_benchmark.remote(cycles=cycles, env=env, model=model, output_name=output_name)
    print(f"Cloud execution completed with exit code: {exit_code}")
