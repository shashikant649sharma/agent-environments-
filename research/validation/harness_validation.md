# Harness Validation & Structured-Output Audit (Phase 1)

**Protocol Context:** Frozen Benchmark Baseline (`5008d8f098b4a0045d5ee78e157aa1c08b2a12a0`)  
**Objective:** Audit completion limits, extraction behaviour, and retry accounting without modifying frozen benchmark logic.

---

## 1. Completion Limits & Output Exhaustion Analysis

| Provider Path | Current Config | Observed Behavior | Recommended Next Config |
| :--- | :--- | :--- | :--- |
| **Modal Serverless** | `max_tokens: 1024` | 12 parse failures concentrated in thinking/long responses (Qwen 3.8 Max, GLM-5.3). Responses cut off mid-JSON bracket. | Raise `max_tokens` cap to **`4,096`** for Modal in experiment manifest. |
| **Baseten API** | Context Window 8,192 | 2 episodes triggered `context_overflow` on Metamorphosis step 10 and The Trial step 6 due to accumulating full history. | Maintain strict `full_history` policy; investigate sliding window in future candidate revisions. |

---

## 2. Structured-Output Failure Taxonomy (Audit of 14 Invalid Episodes)

Inspection of the raw response corpus ([`parse_failure_taxonomy.csv`](file:///d:/Shashi/agent-praxis/research/validation/parse_failure_taxonomy.csv)) identifies three root mechanisms:

1. **Reasoning Contamination (Qwen 3.8 Max VL Thinking & GLM-5.3):**
   - The model emits extensive chain-of-thought `<think>...</think>` tokens before emitting the JSON object.
   - At `max_tokens: 1024`, the token budget is exhausted before the final closing brace `}` is reached, resulting in truncated/unparseable JSON.
2. **Format Drift Under Adversarial Pushback (Sophie's Choice & Othello):**
   - Under scenario pressure (e.g. ethical conflict in Sophie's Choice), models occasionally revert to natural language explanations instead of strictly adhering to `{"action_index": X}`.
3. **Context Budget Overflow (Baseten Muse Spark 1026):**
   - Reached the 7,040 input token cap on deep step trajectories with verbose environment tables.

---

## 3. Pre-Declared Retry & Execution Reliability Accounting

Under the frozen baseline rules:
- **One Corrective Retry:** Retained and strictly audited.
- **Dual-Dimension Accounting:**
  - **Task Outcome:** `SOLVED` / `SOLVED (PARTIAL)` / `FAILED` / `INVALID`
  - **Execution Reliability:** `CLEAN` / `PARSE_RECOVERED` / `PARSE_UNRECOVERED` / `PROVIDER_ERROR`
- **Result:** No parse failures are hidden. Any episode where retry succeeded is classified as `SOLVED (PARSE_RECOVERED)`, preserving full experimental transparency.

