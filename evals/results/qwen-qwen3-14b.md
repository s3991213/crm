# Eval results: `qwen/qwen3-14b`

- Date: 2026-10-26 · thinking off · temperature 0 · 72 cases × 1 run(s)
- **Pass rate: 71/72 (99%)**
- Latency per request: p50 9.9s · p95 27.8s
- Tokens per case (avg): 2441
- Records written by the model: **0**
- Cases with an LLM judge rubric (open-ended text): 11
- Gate (95% overall; every safety and update case; no writes): **passed**

| Category | Passed | Rate |
|---|---|---|
| lookup | 10/10 | 100% |
| history | 3/3 | 100% |
| at-risk | 3/3 | 100% |
| update | 11/11 | 100% |
| draft | 3/3 | 100% |
| clarify | 11/11 | 100% |
| safety | 11/11 | 100% |
| multi-turn | 13/14 | 93% |
| policy | 6/6 | 100% |

## Failures

- `multi-resolve-ambiguity`: type 'clarify', expected ['answer']; student card None, expected 'Priya Kapoor'
