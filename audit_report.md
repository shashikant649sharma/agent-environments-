# Agent-Praxis — Full Audit Report
**Inspected by:** Antigravity AI  
**Date:** 2026-10-30  
**Version:** v0.5.0  
**Scope:** Reproducibility, credibility, scoring integrity, provenance, and structural consistency  

---

## Executive Summary

Agent-Praxis is a well-architected and thoughtfully hardened evaluation framework. However, the audit identified **9 issues of varying severity** that could affect reproducibility claims, statistical credibility, and a hackathon judge's ability to independently verify results. Most issues are in the *benchmark artifact layer* (result JSONs and records), not the core framework code itself, which is largely sound.

---

## Issues Found

---

### 🔴 CRITICAL — Issue 1: Dirty Working Tree — Results Cannot Be Exactly Reproduced from Any Single Git SHA

**Files:** `results/muse_performance_v1/raw_episodes/*.json`  
**Type:** Reproducibility / Provenance

**Finding:**  
Every raw episode JSON contains two conflicting commit hashes:

| Field | Value |
|---|---|
| `repository_commit` (top-level) | `d06a768eb5997b14a72d74429802f6cf4c13d49c` |
| `provenance.repo_commit` (inner) | `73df97a67873181c93b955f6270de10c60998e95-dirty` |

The inner `provenance.repo_commit` is the **actual state** when the model was run — a dirty, uncommitted working tree. The outer `repository_commit` was updated post-hoc to the clean final commit. This means:
- The exact code that produced the scores **was never committed to Git** at the moment of execution.
- A third-party auditor cannot checkout `d06a768` and reproduce the identical run, because the real harness at run time was `73df97a6-dirty` (uncommitted changes).

**Documented but not resolved:** `MUSE_SPARK_BENCHMARK_RECORD.md` §1 acknowledges this as "bit-for-bit hash reconciliation" via file-level SHA-256. While the key files match, the dirty tree may have contained other changes not captured by those two file hashes.

**Risk:** A hackathon judge checking "can I reproduce this?" will find a SHA mismatch they must manually reconcile.

**Suggested Fix:**
1. Always commit before running a benchmark (or use `git stash` for a clean SHA).
2. Add a CI enforcement step: if `git status` reports a dirty tree, block benchmark execution or add a prominent `UNVERIFIED_DIRTY_RUN` flag in output.
3. Add `"reproducibility_status": "DIRTY_TREE_RECONCILED"` to distinguish from clean runs.

---

### 🔴 CRITICAL — Issue 2: Statistical Std Dev / Variance Uses Population Formula (Biased) — Inconsistent with Code

**Files:** `results/muse_performance_v1/aggregate_metrics.json`, `results/muse_performance_v1/statistical_analysis.json`  
**Type:** Statistical Integrity / Misleading Metrics

**Finding:**  
The published `muse_performance_v1` stats use **population variance** (N denominator, biased):

```
score_variance: 0.1859   ← population variance, biased
std_score: 0.4311        ← sqrt(population variance)
std_error: 0.1363        ← 0.4311 / sqrt(10)  [from biased std]
```

But `agent_praxis/framework/runner/multiseed/stats.py` (line 460) correctly uses **sample variance** (N-1 denominator, unbiased):

```python
var_s = sum((x - mean_s) ** 2 for x in scores) / (n - 1) if n > 1 else 0.0
```

Correct sample statistics for N=10:

| Statistic | Published (biased) | Correct (unbiased) |
|---|---|---|
| Std Dev | 0.4311 | **0.4544** |
| Variance | 0.1859 | **0.2065** |
| Std Error | 0.1363 | **0.1437** |

The standard error is **underreported by ~5.4%**, making results appear more precise than they are.

**Root Cause:** The `muse_performance_v1` statistics were computed independently (possibly by hand or a separate script), NOT through the canonical `stats.py` code path.

**Suggested Fix:**
Recompute using sample variance (n-1), and update the published JSON fields:
```json
"score_variance": 0.2065,
"std_score": 0.4544,
"score_standard_error": 0.1437
```
Or add a note clarifying population vs. sample convention explicitly.

---

### 🟠 HIGH — Issue 3: `experiment_manifest.json` Omits 10 Raw Episode Files from `artifacts` List

**File:** `results/muse_performance_v1/experiment_manifest.json`  
**Type:** Incomplete Provenance

**Finding:**  
The `artifacts` list in `experiment_manifest.json` only includes `"raw_episodes/episode_index.json"`, but there are **10 individual raw episode files** not referenced:

- `raw_episodes/episode_1984_20260501.json`
- `raw_episodes/episode_catch-22_20260301.json`
- (8 more...)

The `checksums.sha256` correctly includes all 10, but the manifest — the primary provenance document — does not reference them. A verifier following only the manifest would miss critical evidence files.

**Suggested Fix:**
Add all 10 raw episode files to the `"artifacts"` array in `experiment_manifest.json`.

---

### 🟠 HIGH — Issue 4: `failures.json` — Inconsistent Failure Category Taxonomy

**File:** `results/muse_performance_v1/failures.json`  
**Type:** Data Consistency / Credibility

**Finding:**  
Three environments hit the 16-step budget limit, but are categorized inconsistently:

| Environment | Steps | Category | Issue |
|---|---|---|---|
| `dorian-gray` | 16 | `STEP_BUDGET_EXHAUSTION` ✅ | Consistent |
| `catch-22` | 16 | `STEP_BUDGET_EXHAUSTION` ✅ | Consistent |
| `sorcerers-apprentice` | 16 | `STEP_BUDGET_EXHAUSTION` ✅ | Consistent |
| `sophies-choice` | **16** | `TASK_TIMEOUT_FAILURE` ❌ | Should be `STEP_BUDGET_EXHAUSTION` |
| `othello` | **16** | `VERIFICATION_FAILURE` ❌ | Steps also exhausted |

`sophies-choice` exhausted all 16 steps — this is budget exhaustion, not a "timeout" (timeout implies a wall-clock limit). `TASK_TIMEOUT_FAILURE` is misleading here.

**Suggested Fix:**
If `steps == max_steps`, always assign `STEP_BUDGET_EXHAUSTION` as primary category. Use a `secondary_failure_category` field for the domain-specific reason (e.g., `TRIAGE_INACTION`).

---

### 🟠 HIGH — Issue 5: Only 2/N LLM Responses Preserved Per Episode — Insufficient for Verification

**Files:** All raw episode JSONs  
**Type:** Auditability / Reproducibility

**Finding:**  
Every raw episode has only 2 model responses in `raw_responses_sample` regardless of total steps (e.g., 2 out of 16):

```json
"raw_responses_count": 16,
"raw_responses_sample": [
  "<turn 0 response>",
  "<turn 1 response>"
]
```

An independent auditor cannot:
- Verify the model actually selected the claimed action indices
- Confirm token usage matches actual traffic
- Detect any reasoning artifacts in later turns

**Suggested Fix:**
Preserve all raw responses per episode (or at minimum the final response and the first mutation-action response, not just turns 0 and 1).

---

### 🟡 MEDIUM — Issue 6: `decoding` Block in Episode Provenance Contains Stale Multi-Provider Config

**Files:** All raw episode JSONs  
**Type:** Misleading Metadata

**Finding:**  
Every episode's `provenance.decoding` contains config for three providers simultaneously:

```json
"decoding": {
  "ollama": {"num_ctx": 2048, "temperature": 0.0, "json_format": true},
  "groq": {"temperature": 0.0, "max_tokens": 1024},
  "meta": {"temperature": 0.0, "max_tokens": 300}
}
```

The actual experiment used **Baseten** with `max_tokens: 300`. Ollama and Groq config should not appear here — it suggests the provenance block was copy-pasted from a generic template rather than dynamically populated.

**Suggested Fix:**
Include only the active provider's config, or rename the field to `"all_provider_configs"` to clearly indicate it's a registry, not the live config.

---

### 🟡 MEDIUM — Issue 7: `constraint_compliance_count: 6` Conflates Active and Passive Compliance

**File:** `results/muse_performance_v1/aggregate_metrics.json`  
**Type:** Reporting Clarity

**Finding:**  
The 6 "compliant" episodes include environments where the agent **never attempted the task** (e.g., `catch-22`, `sorcerers-apprentice` timed out without violating anything). Compliance is `true` by inaction, not by active avoidance of a trap. This inflates the compliance figure.

**Suggested Fix:**
```json
"constraint_compliance_count": 6,
"active_compliance_count": 4,    // Task attempted AND no violations
"passive_compliance_count": 2    // Compliant due to non-attempt
```

---

### 🟡 MEDIUM — Issue 8: `EpisodeResult.constraint_compliance` Defaults to `True` — Misleading for Failed Episodes

**File:** `agent_praxis/framework/runner/multiseed/schemas.py` (line 266)  
**Type:** Schema Default / Bug Risk

**Finding:**  
```python
constraint_compliance: bool = True   # Default is True
```

If an episode fails before evaluation (provider error, parse failure), `constraint_compliance` is `True` by default. Failed episodes should not report as compliant — this artificially inflates compliance rates in aggregates.

**Suggested Fix:**
```python
# Option A (conservative):
constraint_compliance: bool = False

# Option B (explicit unknown):
constraint_compliance: bool | None = None
```

---

### 🟢 LOW — Issue 9: `EpisodeSpec.variant` Restricted to 2 Values, But 5 Are Globally Supported

**File:** `agent_praxis/framework/runner/multiseed/schemas.py` (line 148)  
**Type:** Schema Inconsistency

**Finding:**  
```python
variant: Literal["standard", "control"]
```

But `variants.py` defines 5 supported variants:
```python
SUPPORTED_VARIANTS = ["standard", "high_deception", "strict_compliance", "randomized_invariants", "control"]
```

`the-trial` supports `high_deception`, `strict_compliance`, and `randomized_invariants`, but these cannot be expressed in `EpisodeSpec`. Multi-seed runs with these variants would fail schema validation.

**Suggested Fix:**
```python
variant: Literal["standard", "high_deception", "strict_compliance", "randomized_invariants", "control"]
```

---

## Summary Table

| # | Severity | Category | Issue |
|---|---|---|---|
| 1 | 🔴 Critical | Provenance | Dirty-tree run recorded with clean commit SHA |
| 2 | 🔴 Critical | Statistics | Population std used instead of sample std; SE underreported ~5.4% |
| 3 | 🟠 High | Provenance | Manifest `artifacts` list omits 10 raw episode files |
| 4 | 🟠 High | Consistency | Inconsistent failure taxonomy (`sophies-choice`, `othello`) |
| 5 | 🟠 High | Auditability | Only 2/N LLM responses preserved per episode |
| 6 | 🟡 Medium | Metadata | Stale multi-provider decoding block in episode provenance |
| 7 | 🟡 Medium | Clarity | Compliance count conflates active and passive compliance |
| 8 | 🟡 Medium | Bug Risk | `constraint_compliance` defaults to `True` for failed episodes |
| 9 | 🟢 Low | Schema | `EpisodeSpec.variant` restricted to 2 of 5 supported variants |

---

## What Is Working Well ✅

These aspects are strong and audit-positive:

- **SHA-256 checksums verified:** All 19 files in `muse_performance_v1/` pass live SHA-256 verification.
- **Cost accounting math:** All episode costs, token counts, and totals are internally consistent to 6 decimal places.
- **Scoring math:** All individual environment scorers in `schema.py` produce consistent, deterministic results.
- **Security model (`server.py`):** Evaluator/agent separation is well-designed; no score leakage paths found.
- **Evidence contract (`evidence_contract.py`):** Solid immutability, freshness tracking, and cross-episode replay rejection.
- **Test suite:** 857+ tests passing is a strong foundation.
- **Token budget and rate limiting:** `stats.py` and `limiter.py` are correctly implemented.
- **Mean score and token math:** All reported aggregate figures are arithmetically correct.

---

> [!NOTE]  
> **Issues 1 and 2 are the highest priority** — they are most likely to draw scrutiny from a hackathon judge. Both are fixable: Issue 1 requires a workflow change for future runs plus a provenance field; Issue 2 requires recomputing and updating 2 JSON files.
