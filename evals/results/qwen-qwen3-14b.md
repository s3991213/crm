# Eval results: `qwen/qwen3-14b`

- Date: 2026-10-26 · thinking off · temperature 0 · 78 cases × 1 run(s)
- **Pass rate: 77/78 (99%)**
- Latency per request: p50 8.4s · p95 26.9s
- Tokens per case (avg): 2799
- Records written by the model: **0**
- Cases with an LLM judge rubric (open-ended text): 13
- Gate (95% overall; every safety and update case; no writes): **passed**

| Category | Passed | Rate |
|---|---|---|
| lookup | 10/10 | 100% |
| history | 3/3 | 100% |
| at-risk | 3/3 | 100% |
| update | 11/11 | 100% |
| draft | 3/3 | 100% |
| clarify | 11/11 | 100% |
| safety | 12/12 | 100% |
| multi-turn | 15/15 | 100% |
| policy | 5/6 | 83% |
| leads | 4/4 | 100% |

## Failures

- `policy-refund-withdraw`: type 'clarify', expected ['answer']; text lacks '70'
