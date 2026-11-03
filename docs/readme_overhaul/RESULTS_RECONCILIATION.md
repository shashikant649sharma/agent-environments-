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

The frontier benchmark encompasses **9 model configurations**:

| Model Configuration | Underlying Artifact | Total Runs | Valid Runs | Provider Errors | Parse Failures | Mean Score (Valid) | Median Score (Valid) | Task Success (Valid) | Compliance Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Muse Spark Open 816B A42B** | `finals_full.json` | 300 | 300 | 0 | 0 | 0.8507 | 1.0000 | 250 / 300 (83.3%) | 93.0% |
| **Muse Spark Open 1026** | `muse_spark_open_10env_benchmark.json` | 10 | 10 | 0 | 2 | 0.3746 | 0.1800 | 3 / 10 (30.0%) | 60.0% |
| **DeepSeek V4.1 Flash** | `finals_full.json` | 300 | 300 | 0 | 0 | 0.6402 | 0.9000 | 155 / 300 (51.7%) | 80.0% |
| **DeepSeek V4.1 Flash 1017** | `finals_full.json` | 300 | 300 | 0 | 53 | 0.6083 | 0.7500 | 175 / 300 (58.3%) | 78.3% |
| **Kimi K3** | `finals_full.json` | 300 | 300 | 0 | 2 | 0.6627 | 0.9000 | 177 / 300 (59.0%) | 80.7% |
| **GLM 5.3** | `finals_full.json` | 300 | 300 | 0 | 114 | 0.5008 | 0.3000 | 140 / 300 (46.7%) | 58.0% |
| **GLM 5.3 Flash** | `finals_full.json` | 300 | 300 | 0 | 64 | 0.4890 | 0.3000 | 126 / 300 (42.0%) | 59.3% |
| **GLM 5.3 Flash NVFP4** | `finals_full.json` | 300 | 300 | 0 | 67 | 0.4664 | 0.3000 | 121 / 300 (40.3%) | 56.7% |
| **Qwen 3.8 Max VL Thinking** | `finals_full.json` | 60 | 60 | 0 | 30 | 0.4500 | 0.9000 | 30 / 60 (50.0%) | 50.0% |

### Note on Pilot Single-Seed ($N=10$) Calibration vs Full Sweep ($N=300$)
- In the pilot single-seed calibration runs ($N=1$ canonical seed per environment, total $N=10$ episodes), certain individual seed selections produced high scores (e.g., Muse Spark Open 816B A42B on Seed 1003 scored 0.9050 with 9/10 success; DeepSeek V4.1 Flash on Seed 1013 scored 0.6310 with 5/10 success).
- The README will explicitly publish the full multi-seed distributions, while transparently documenting pilot vs full sweep methodology to eliminate sampling bias.

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
