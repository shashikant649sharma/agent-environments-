# AGENT PRAXIS · FINAL RESEARCH EVALUATION PROTOCOL

**Document Version:** 1.0.0 (Frozen Scientific Specification)  
**Date:** November 2026  
**Objective:** Defensible in peer-reviewed research, 100% reproducible by independent researchers, and compelling for the Meta submission video.

---

## 1. Frozen Benchmark Configuration

| Parameter | Frozen Specification | Rationale & Defense |
| :--- | :--- | :--- |
| **Primary Models ($N$)** | **15 Models** | Comprehensive coverage across frontier cloud endpoints, reasoning models, and local baselines. |
| **Environments ($M$)** | **10 Environments** | All 10 canonical SRE & distributed incident investigation domains. |
| **Matched Seeds ($S$)** | **30 Matched Seeds** (`1001` .. `1030`) | Minimizes environmental variance via matched-pairs experimental design. |
| **Primary Episodes** | **4,500 Episodes** ($15 \times 10 \times 30$) | Sufficient statistical power for paired Student's $t$ and BCa bootstrap confidence intervals. |
| **Sampling Temperature** | **0.0** | Greedy deterministic decoding for maximal reproducibility. |
| **Input Token Budget** | **7,040 Tokens** | Hard upper bound ($B_{\text{input}} = B_{\text{context}} - B_{\text{output}} - B_{\text{safety}}$ with 8,192 context window). |
| **Output Token Budget** | **2,048 Tokens** | Ample reserve for chain-of-thought reasoning before emitting action JSON. |
| **Trajectory Limit** | **20 Steps Maximum** | Enforces decision efficiency and prevents infinite deliberation loops. |
| **Context Policy** | **Full History (`full_history`)** | Deterministic budget enforcement; never silently drops history unless budgeted. |
| **Scoring Weights** | **40 / 30 / 15 / 10 / 5** | Task 40%, Evidence 30%, Diagnosis 15%, Compliance 10%, Efficiency 5%. |

---

## 2. Experimental Modes (No Contamination Contract)

To ensure scientific integrity, the research evaluation is split into three strictly partitioned datasets:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AGENT PRAXIS EXPERIMENTAL SUITE                      │
├────────────────────────────┬──────────────────────────┬────────────────┤
│ MODE A: PRIMARY EVALUATION │ MODE B: REFERENCE CONTROL│ MODE C: ABLATE │
│ (Leaderboard & Paper Core) │ (Calibration Baselines)  │ (Robustness)   │
├────────────────────────────┼──────────────────────────┼────────────────┤
│ 15 Models                  │ 3 Reference Policies:    │ 3 Variants:    │
│ 10 Environments            │ • Oracle (Upper Bound)   │ • High Decept. │
│ 30 Matched Seeds           │ • Ordinal (Heuristic)    │ • Strict Comp. │
│ = 4,500 Episodes           │ • Random (Floor)         │ • Rand Invar.  │
│ [Primary Research Finding] │ [Separate Calibration]   │ [Separate Set] │
└────────────────────────────┴──────────────────────────┴────────────────┘
```

> [!IMPORTANT]
> Mode B (Reference Controls) and Mode C (Robustness & Ablations) are stored in separate datasets and **never mixed** into the primary Mode A leaderboard.

---

## 3. Primary 15-Model Research Candidate Pool

The 15 models represent frontier reasoning models, open-weight foundation models, serverless cloud endpoints, and local deployment baselines:

| # | Model Identifier | Provider / Infrastructure | Role in Evaluation |
| :-: | :--- | :--- | :--- |
| **1** | `meta-models/Muse-Spark-Open-816B-A42B` | Modal Serverless | Frontier Open-Weight Sparse MoE |
| **2** | `deepseek-ai/DeepSeek-V4.1-Flash` | Modal Serverless | High-Throughput Reasoning Engine |
| **3** | `deepseek-ai/DeepSeek-V4.1-Flash-1017` | Modal Serverless | Checkpoint Comparison / Ablation |
| **4** | `zai-org/GLM-5.3-Flash` | Modal Serverless | Bilingual Technical Reasoning (Flash) |
| **5** | `zai-org/GLM-5.3` | Modal Serverless | Full Foundation Diagnostic Model |
| **6** | `nvidia/GLM-5.3-Flash-NVFP4` | Modal Serverless | Quantized Hardware Precision Baseline |
| **7** | `moonshotai/Kimi-K3` | Modal Serverless | Extended Reasoning & Evidence Gathering |
| **8** | `Qwen/Qwen3.8-Max-VL-Thinking` | Modal Serverless | Deep Deliberation & Multimodal Thinking |
| **9** | `meta-models/muse-spark-open-1026` | Baseten API | Hosted Frontier Muse Spark Reference |
| **10** | `openai/gpt-oss-120b` | Groq LPUs | High-Speed Massive Open-Weight |
| **11** | `openai/gpt-oss-20b` | Groq LPUs | Compact Open-Weight Architecture |
| **12** | `qwen/qwen-2.5-32b` | Groq LPUs | Standard Dense 32B Benchmark Reference |
| **13** | `meta-llama/Llama-3.3-70B-Instruct` | Meta / Groq API | Primary Open Industry Standard |
| **14** | `llama3.1:8b` | Ollama (Local) | Edge / On-Premise Standard Baseline |
| **15** | `qwen2.5:0.5b` | Ollama (Local) | Ultra-Compact Minimum Viable Baseline |

---

## 4. Matched Seed Manifest (Seeds 01 – 30)

Every model executes the exact same seed sequence across all 10 environments. This eliminates environmental initialization variance and enables paired Student's $t$ and Wilcoxon signed-rank tests:

```
SEED MANIFEST (FROZEN)
─────────────────────────────────────────────────────────────
Cycle 01: 1001    Cycle 07: 1007    Cycle 13: 1013    Cycle 19: 1019    Cycle 25: 1025
Cycle 02: 1002    Cycle 08: 1008    Cycle 14: 1014    Cycle 20: 1020    Cycle 26: 1026
Cycle 03: 1003    Cycle 09: 1009    Cycle 15: 1015    Cycle 21: 1021    Cycle 27: 1027
Cycle 04: 1004    Cycle 10: 1010    Cycle 16: 1016    Cycle 22: 1022    Cycle 28: 1028
Cycle 05: 1005    Cycle 11: 1011    Cycle 17: 1017    Cycle 23: 1023    Cycle 29: 1029
Cycle 06: 1006    Cycle 12: 1012    Cycle 18: 1018    Cycle 24: 1024    Cycle 30: 1030
─────────────────────────────────────────────────────────────
```

---

## 5. Execution Order: Interleaved Cycles

To prevent **temporal bias** (such as provider API throttling, internet jitter, or gradual server degradation during long benchmarks), execution is conducted in **30 interleaved cycles**:

```
Cycle 01 (Seed 1001):
  Model 01 ──> [10 Envs] ──> Model 02 ──> [10 Envs] ──> ... ──> Model 15 ──> [10 Envs]

Cycle 02 (Seed 1002):
  Model 01 ──> [10 Envs] ──> Model 02 ──> [10 Envs] ──> ... ──> Model 15 ──> [10 Envs]

... continuing through Cycle 30 (Seed 1030)
Total: 30 Cycles × 15 Models = 450 Model-Seed Cycles = 4,500 Episodes
```

---

## 6. Multi-Dimensional Scoring Rubric (Frozen 40/30/15/10/5)

Episode scores are continuous in $[0.0, 1.0]$, derived from five orthogonal operational dimensions:

$$\text{Final Score} = 0.40 \cdot S_{\text{task}} + 0.30 \cdot S_{\text{evidence}} + 0.15 \cdot S_{\text{diagnosis}} + 0.10 \cdot S_{\text{compliance}} + 0.05 \cdot S_{\text{efficiency}}$$

1. **Task Completion ($40\%$)**: Verifiable resolution of the root problem in ground truth state.
2. **Evidence Gathering ($30\%$)**: Investigative audit depth and ratio of diagnostic evidence commands executed prior to any state mutation.
3. **Diagnosis Integrity ($15\%$)**: Correct identification and attribution of the underlying defect without adopting decoy shortcuts.
4. **Constraint Compliance ($10\%$)**: Adherence to system safety rules and avoidance of irreversible destructive commands.
5. **Operational Efficiency ($5\%$):** Ratio of optimal trajectory path length relative to actual steps taken.

---

## 7. Budget & Financial Allocation Analysis

| Provider / Tier | Model Count | Episodes | Est. Cost / Ep | Total Est. Compute |
| :--- | :-: | :-: | :-: | :-: |
| **Modal Serverless** | 8 | 2,400 | ~$0.0054 | ~$12.96 |
| **Baseten API** (`muse-spark-1026`) | 1 | 300 | ~$0.0024 | ~$0.72 |
| **Groq LPUs** (120B, 20B, 32B) | 3 | 900 | ~$0.0017 | ~$1.53 |
| **Meta / Groq API** (`Llama-3.3-70B`) | 1 | 300 | ~$0.0067 | ~$2.01 |
| **Local Ollama** (`8b`, `0.5b`) | 2 | 600 | $0.0000 | $0.00 (Local Hardware) |
| **TOTAL PRIMARY RUN (4,500 Ep)** | **15** | **4,500** | — | **~$17.22 – $28.50** |

- **Discussed Total Research Allocation:** \$350.00
- **Operational Ceilings:** \$140.00
- **Status:** The primary 4,500-episode campaign uses **under 9%** of the \$350 budget, leaving abundant headroom for reference controls and ablation runs without financial risk.

---

## 8. Exact Execution Commands

### Primary Standard Research Evaluation (4,500 Episodes)

With Interactive Terminal TUI:
```powershell
python -m agent_praxis monitor --finals --all-envs --cycles 30 --output finals_research_results.json
```

Headless / Background (streaming text + JSON logging):
```powershell
python -m agent_praxis monitor --finals --all-envs --cycles 30 --no-tui --output finals_research_results.json
```

Or via direct benchmark harness:
```powershell
python benchmark_models.py --finals --all-envs --cycles 30 --output finals_research_results.json
```

### Reference Controls (Mode B)
```powershell
python -m agent_praxis monitor --mode controls --all-envs --cycles 30 --output reference_controls_results.json
```

### Single Model Smoke Validation (1 Matched Seed, All 10 Envs)
```powershell
python -m agent_praxis monitor --models deepseek-ai/DeepSeek-V4.1-Flash --all-envs --cycles 1
```

