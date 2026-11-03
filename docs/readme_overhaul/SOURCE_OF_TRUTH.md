# Benchmark & Metric Source of Truth

**Milestone:** Agent Praxis v0.5.1  
**Integrity Rule:** Every published score, rate, confidence interval, and test count must possess an immutable, traceable source artifact.

---

## 1. Metric Authority Mapping

| Published Metric | Authoritative File | Record Count | Integrity Gate |
| :--- | :--- | :--- | :--- |
| **Canonical Policy Ladder** (No-Op, Read-Only, Random, Ordinal, Blind Search, Oracle) | `results/baselines/baseline_v050_canonical_300runs.json` | 300 runs | Zero-credit floor (0.0000) verified; Oracle ceiling (1.0000) verified |
| **Split Generalization Invariants** (Dev vs Held-Out) | `results/baselines/baseline_v050_development_180runs.json`<br/>`results/baselines/baseline_v050_held_out_120runs.json` | 180 runs (dev)<br/>120 runs (held-out) | $\Delta = 0.0000$ for deterministic policies; Random bounded $\le 0.20$ |
| **Frontier Model Evaluation Suite** (9 Model Configurations) | `results/finals_full.json`<br/>`results/muse_spark_open_10env_benchmark.json` | 2,160 runs (`finals_full.json`)<br/>10 runs (`muse_spark_open`) | Failure precedence hierarchy applied; infrastructure errors excluded from model reasoning score |
| **Paired Effect Sizes & Statistical Tests** | `results/p2_pilot/p2_pilot_420_runs.json` | 420 runs | Two-sided permutation tests with Holm-Bonferroni correction |
| **Golden Path Implementations** | `agent_praxis/framework/evaluation/golden.py` | 10 environments | Unified canonical implementation; CLI and benchmarks consume identical logic |
| **Scoring Rubric Dimensions & Weights** | `agent_praxis/framework/evaluation/schema.py` | 5 dimensions | Task (0.40), Evidence (0.30), Diagnosis (0.15), Compliance (0.10), Efficiency (0.05) |
| **Active Test Suite Count** | Pytest CLI execution | 991 items collected | 990 passed, 1 skipped, 0 failed |
| **Package Release Version** | `pyproject.toml` | Project metadata | `0.5.1` |

---

## 2. Source Artifact Cryptographic Fingerprints

```yaml
artifacts:
  baseline_canonical_300:
    path: "results/baselines/baseline_v050_canonical_300runs.json"
    sha256: "69aadd554f94cda0d74e06cf577b551bbdf9e7c9dcea24002620a923700bfc7b"
    runs: 300
    environments: 10
    policies: 6
    seeds_per_cell: 5

  baseline_dev_180:
    path: "results/baselines/baseline_v050_development_180runs.json"
    sha256: "9769faae011c17418201fac07ae4ad8cd48a2e2fa8fae4c04ab5b18fba83d07f"
    runs: 180

  baseline_held_out_120:
    path: "results/baselines/baseline_v050_held_out_120runs.json"
    sha256: "63368ea76a106cf9101ae5d68df96451273525047da3b479a9555a7dc174e4ef"
    runs: 120

  frontier_finals_full:
    path: "results/finals_full.json"
    sha256: "f615a97c76037faa29c64b492e996f4d5d3b1128da253f9ce6109f2270498e0f"
    runs: 2160
    models: 8

  muse_spark_open_1026:
    path: "results/muse_spark_open_10env_benchmark.json"
    sha256: "af27bf97f2aa78f6ddaa44bb31491453e958bab97c0fd49a1db6d9552e9be54a"
    runs: 10
    model: "meta-models/muse-spark-open-1026"

  p2_pilot_420:
    path: "results/p2_pilot/p2_pilot_420_runs.json"
    sha256: "dc8fef0d1bbe8287a6bf0b1af50dc7be09f5988fee1f2e33efa287af27cd003e"
    runs: 420
```

---

## 3. Disallowed Practices

1. **No Mixed Denominators**: If an evaluation excludes infrastructure errors (e.g. rate limit HTTP 429), the denominator for valid mean score and task success rate must be identical ($N_{\text{valid}}$).
2. **No Memory Substitutions**: Historical v0.2 pilot numbers (6 environments) or non-isolated proxy runs must never be substituted for canonical v0.5.0/v0.5.1 measurements.
3. **No Unaudited Claims**: No model may be reported as "100% solving" an environment unless the independent out-of-band ground-truth evaluator recorded `task_success = True` and `score = 1.0000`.
