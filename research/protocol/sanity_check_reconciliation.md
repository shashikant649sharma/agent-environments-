# Sanity Check & Pilot Reconciliation Report (Phase 0)

**Dataset Reference:** `research/results/sanity_check/finals_preflight.json`  
**Execution Timestamp:** 2026-11-02T15:42:37+05:30  
**Scope:** 9 Verified Cloud Models × 10 Canonical Environments × 1 Matched Seed (1001)  
**Total Episodes:** 90  
**Total Model Turns:** 808  
**Infrastructure Failures:** 0 (100% provider availability)

---

## 1. Episode Outcome Reconciliation

All 90 pilot episodes have been parsed, indexed, and reconciled:

| Outcome Category | Episodes | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **SOLVED (Full)** | 38 | 42.2% | Verified incident remediation, evidence, and constraint compliance |
| **SOLVED (Partial)** | 12 | 13.3% | Partial score credit (e.g. Othello at 0.750 under pushback) |
| **FAILED (Reasoning)** | 26 | 28.9% | Valid actions taken, but postcondition unsatisfied or trap triggered |
| **INVALID (Format/Context)** | 14 | 15.6% | Unparseable model formatting (12) or context overflow (2) |
| **INFRA ERROR** | **0** | **0.0%** | Zero unhandled network, timeout, or auth rejections |

---

## 2. Model Performance Summary

| Model Identifier | Provider | Episodes | Solved | Failed | Invalid | Mean Score | Turns |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `meta-models/Muse-Spark-Open-816B-A42B` | Modal | 10 | 9 | 1 | 0 | **0.905** | 91 |
| `moonshotai/Kimi-K3` | Modal | 10 | 7 | 3 | 0 | **0.740** | 86 |
| `meta-models/muse-spark-open-1026` | Baseten | 10 | 7 | 1 | 2 | **0.704** | 97 |
| `deepseek-ai/DeepSeek-V4.1-Flash-1017` | Modal | 10 | 6 | 2 | 2 | **0.625** | 78 |
| `deepseek-ai/DeepSeek-V4.1-Flash` | Modal | 10 | 4 | 6 | 0 | **0.528** | 78 |
| `Qwen/Qwen3.8-Max-VL-Thinking` | Modal | 10 | 5 | 1 | 4 | **0.520** | 83 |
| `nvidia/GLM-5.3-Flash-NVFP4` | Modal | 10 | 4 | 5 | 1 | **0.485** | 106 |
| `zai-org/GLM-5.3-Flash` | Modal | 10 | 4 | 5 | 1 | **0.475** | 101 |
| `zai-org/GLM-5.3` | Modal | 10 | 4 | 2 | 4 | **0.449** | 88 |

---

## 3. Provenance & Baseline Sign-Off (Gate 0)

- **Clean Working Tree:** Commit `5008d8f098b4a0045d5ee78e157aa1c08b2a12a0` on branch `feat/research-console-and-cloud-finals`.
- **Endpoints Verified:** 8 Modal serverless endpoints + 1 Baseten inference endpoint.
- **Local Models:** 0 local LLMs in execution path.
- **Status:** **GATE 0 PASSED**. Baseline manifest locked in `research/protocol/baseline_manifest.json`.

