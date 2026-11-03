# Phase 0 Baseline Audit & Inventory

**Audit Date:** 2026-11-03  
**Target Release:** v0.5.1  
**Audited Head Commit:** `33d45d9945361dff7addc87ff8344b7ed639549e`  
**Base Branches:** `origin/main` (`1318110`), `origin/test` (`33d45d9`)  
**Active Working Branch:** `test`  
**Working Tree Status:** Clean baseline (initial untracked artifact: `results/finals_full.json`, size: 19,717,511 bytes)  

---

## 1. README Visual Asset & Badge Inventory

The current `README.md` contains the following image, logo, and badge references:

| Reference | Type | Location / Target | Status |
| :--- | :--- | :--- | :--- |
| `logo.png` | Local Image | Root repository (`logo.png`) | Present |
| CI Status Badge | Shields.io Badge | `actions/workflows/ci.yml/badge.svg` | Remote dynamic |
| Python 3.11+ Badge | Shields.io Badge | `https://img.shields.io/badge/Python-3.11%2B-blue.svg` | Remote static |
| MIT License Badge | Shields.io Badge | `https://img.shields.io/badge/License-MIT-yellow.svg` | Remote static |
| Tests Passed Badge | Shields.io Badge | `https://img.shields.io/badge/tests-882%20passed-success.svg` | Stale (prior v0.5.0 milestone) |
| Version Badge | Shields.io Badge | `https://img.shields.io/badge/version-0.5.0-orange.svg` | Stale (upgrading to v0.5.1) |
| Environments Badge | Shields.io Badge | `https://img.shields.io/badge/environments-10%20adversarial-purple.svg` | Active (10 environments) |

*README Overhaul Requirement:* In the new README, all figures must be reproducible SVGs residing in `assets/readme/`. Visual artwork (hero, architecture, environments) reserves explicit image placeholders (`<!-- IMAGE PLACEHOLDER: ... -->`).

---

## 2. Benchmark Artifacts Inventory (JSON & CSV)

The complete inventory of empirical benchmark data across `results/` encompasses:

### 2.1 Primary & Frontier Model Artifacts
- **`results/finals_full.json`** (19,717,511 bytes, SHA-256: `f615a97c76037faa29c64b492e996f4d5d3b1128da253f9ce6109f2270498e0f`):
  2,160 total trajectories across 8 models (`meta-models/Muse-Spark-Open-816B-A42B`, `deepseek-ai/DeepSeek-V4.1-Flash`, `deepseek-ai/DeepSeek-V4.1-Flash-1017`, `moonshotai/Kimi-K3`, `zai-org/GLM-5.3`, `zai-org/GLM-5.3-Flash`, `nvidia/GLM-5.3-Flash-NVFP4`, `Qwen/Qwen3.8-Max-VL-Thinking`).
- **`results/muse_spark_open_10env_benchmark.json`** (64,120 bytes, SHA-256: `af27bf97f2aa78f6ddaa44bb31491453e958bab97c0fd49a1db6d9552e9be54a`):
  10 canonical episodes for `meta-models/muse-spark-open-1026` on live Baseten inference. Provenance reconciled in `be6c6d4`.
- **`results/groq_qwen27b_benchmark.json`** (42,000 bytes, SHA-256: `c77d91587254138f51119ee9c2e79d9ab92481bf27fa1951f89e4e70869685e3`):
  10 episodes for `qwen/qwen3.8-27b` via Groq.
- **`results/gemma2_9b_10env_benchmark.json`** (44,483 bytes, SHA-256: `67feac66bce294a3187bfa8c88f98e7e892d0467a14df50e91a057e2c54d5a38`):
  10 episodes for `gemma2:9b`.

### 2.2 Canonical Baseline & Validation Artifacts
- **`results/baselines/baseline_v050_canonical_300runs.json`** (215,178 bytes, SHA-256: `69aadd554f94cda0d74e06cf577b551bbdf9e7c9dcea24002620a923700bfc7b`):
  300 canonical baseline policy ladder runs (10 environments $\times$ 6 policies $\times$ 5 canonical seeds).
- **`results/baselines/baseline_v050_development_180runs.json`** (133,874 bytes, SHA-256: `9769faae011c17418201fac07ae4ad8cd48a2e2fa8fae4c04ab5b18fba83d07f`):
  Development split partition (seeds 1–3, $N=180$).
- **`results/baselines/baseline_v050_held_out_120runs.json`** (93,275 bytes, SHA-256: `63368ea76a106cf9101ae5d68df96451273525047da3b479a9555a7dc174e4ef`):
  Held-out split partition (seeds 4–5, $N=120$).
- **`results/p2_pilot/p2_pilot_420_runs.json`** (353,890 bytes, SHA-256: `dc8fef0d1bbe8287a6bf0b1af50dc7be09f5988fee1f2e33efa287af27cd003e`):
  420 paired runs across standard and counterfactual control conditions.

---

## 3. Version and Test-Count Audit

- **Package Version**:
  - `pyproject.toml`: `0.5.0` -> Requires update to `0.5.1`.
  - `agent_praxis/__init__.py`: dynamically resolved or declared.
  - `agent_praxis/commands/demo.py`: Hardcoded `[Agent Praxis v0.5.0]` banners -> Update to read dynamically or `v0.5.1`.
- **Test Count**:
  - `README.md` badge: `882 passed`.
  - `RESULTS.md` header: `882 passed`.
  - Full current pytest run on branch `test`:
    - **987 passed**, **1 skipped** (Starlette/HTTPX optional compatibility test), **0 failed** in 8.71s.

---

## 4. Documentation Classification

### Generated Artifacts
- Model benchmark summary Markdown tables.
- SVG graphs in `assets/readme/`.
- Provenance manifests.

### Manually Maintained Documentation
- `docs/HACKATHON_REPORT.md` (Research context and methodology).
- `CHANGELOG.md` (Release history).
- `CITATION.cff` (Citation metadata).
- `TODO.md` (Future technical backlog).
