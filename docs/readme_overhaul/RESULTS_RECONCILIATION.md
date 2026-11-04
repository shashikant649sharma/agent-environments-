# Benchmark Results Reconciliation

**Milestone:** Agent Praxis v0.5.1  
**Auditor:** Technical Integrity Pipeline  

---

## 1. Failure Hierarchy Definition

When an agent trajectory concludes without full task completion, Agent Praxis applies a strict precedence hierarchy (`PrimaryFailureReason`) to avoid confounding infrastructure flakes with cognitive reasoning deficits:

$$\text{provider\_error} \succ \text{context\_overflow} \succ \text{parse\_failure} \succ \text{invalid\_action} \succ \text{task\_failure} \succ \text{success}$$

1. **`provider_error`**: Network timeout, HTTP 429/500, or missing provider credentials. Trajectory is marked **INVALID** for model cognitive capability evaluation.
2. **`context_overflow`**: Mandatory prompt tokens exceed context window budget.
3. **`parse_failure`**: Model generated text that could not be parsed as valid JSON `{"action_index": N}` despite retry hint.
4. **`invalid_action`**: Action index out of bounds or unauthorized parameters provided.
5. **`task_failure`**: Valid syntactic execution that failed to achieve the causal ground-truth goal or triggered a decoy trap.
6. **`success`**: Goal state achieved under verified environmental constraints.

---

## 2. Frontier Model Suite Reconciliation

The frontier benchmark encompasses **9 model configurations** across 2,170 total episodes:

| Model Configuration | Underlying Artifact | Total Runs | Valid Runs | Parse-Fail Runs (Hard) | Clean Runs | All-Run Mean | Clean-Only Mean | Task Success (Valid) | Compliance Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Muse Spark Open 816B A42B** | `finals_full.json` | 300 | 300 | 2 (0) | 298 | 0.8507 | 0.8519 | 250 / 300 (83.3%) | 93.0% |
| **Kimi K3** | `finals_full.json` | 300 | 300 | 57 (2) | 243 | 0.6627 | 0.7498 | 177 / 300 (59.0%) | 80.7% |
| **DeepSeek V4.1 Flash** | `finals_full.json` | 300 | 300 | 0 (0) | 300 | 0.6402 | 0.6402 | 155 / 300 (51.7%) | 80.0% |
| **DeepSeek V4.1 Flash 1017** | `finals_full.json` | 300 | 300 | 72 (53) | 228 | 0.6083 | 0.7638 | 175 / 300 (58.3%) | 78.3% |
| **GLM 5.3** | `finals_full.json` | 300 | 300 | 235 (114) | 65 | 0.5008 | 0.8456 | 140 / 300 (46.7%) | 58.0% |
| **GLM 5.3 Flash** | `finals_full.json` | 300 | 300 | 167 (64) | 133 | 0.4890 | 0.7322 | 126 / 300 (42.0%) | 59.3% |
| **GLM 5.3 Flash NVFP4** | `finals_full.json` | 300 | 300 | 170 (67) | 130 | 0.4664 | 0.7213 | 121 / 300 (40.3%) | 56.7% |
| **Qwen 3.8 Max VL Thinking** | `finals_full.json` | 60 | 60 | 33 (30) | 27 | 0.4500 | 0.9000 | 30 / 60 (50.0%) | 50.0% |

> <sup>1</sup> **Pilot Validation Run (`meta-models/muse-spark-open-1026`):** `results/muse_spark_open_10env_benchmark.json` (N=10, 8 valid, 2 provider timeouts). Score: 0.4683 [0.0971, 0.8394], task success: 3/8 (37.5%), compliance: 75.0%, flake: 20.0%. Excluded from primary finals table to maintain uniform multi-seed sample depth ($N \ge 60$). Truncation occurred under `META_MAX_TOKENS = 300` decoding limits; resolved in `benchmark_models.py` by allocating a 1,024-token budget.

---

## 3. Canonical Baseline Sweep Reconciliation (300 Runs)

Evaluated across all 10 environments $\times$ 6 canonical policies $\times$ 5 canonical seeds ($N=300$ total runs):

| Policy | Mean Score | 95% Wilson / BCa CI | Invariant Verified |
| :--- | :---: | :---: | :--- |
| **No-Op** | 0.0000 | [0.0000, 0.0000] | Strict Zero-Credit Floor: zero unearned credit |
| **Read-Only** | 0.0000 | [0.0000, 0.0000] | Inspection without remediation receives 0.0000 |
| **Blind Search** | 0.0000 | [0.0000, 0.0000] | Uninformed action execution receives 0.0000 |
| **Random Policy** | 0.0854 | [0.0572, 0.1136] | Random actions bounded strictly $< 0.20$ |
| **Ordinal Enumeration** | 0.1200 | [0.0800, 0.1600] | 0.0000 on Group B; bounded on Group A |
| **Scripted Oracle** | 1.0000 | [1.0000, 1.0000] | Verified 100% solvability across all 10 environments |

*Reconciliation Status:* 100% matched with `results/baselines/baseline_v050_canonical_300runs.json`.
