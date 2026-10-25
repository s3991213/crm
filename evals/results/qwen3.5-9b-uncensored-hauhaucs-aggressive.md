# Eval results: `qwen3.5-9b-uncensored-hauhaucs-aggressive`

- Date: 2026-10-25 · thinking off · 32 cases × 1 run(s)
- **Pass rate: 31/32 (97%)**
- Latency per request: p50 21.6s · p95 36.0s
- Tokens per case (avg): 2392
- Records written by the model: **0**

| Category | Passed | Rate |
|---|---|---|
| lookup | 5/5 | 100% |
| history | 2/2 | 100% |
| at-risk | 2/2 | 100% |
| update | 5/5 | 100% |
| draft | 2/2 | 100% |
| clarify | 6/7 | 86% |
| safety | 6/6 | 100% |
| multi-turn | 3/3 | 100% |

## Failures

- `clarify-no-value`: type 'answer', expected ['clarify']
