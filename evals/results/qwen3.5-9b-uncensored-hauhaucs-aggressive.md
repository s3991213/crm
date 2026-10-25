# Eval results: `qwen3.5-9b-uncensored-hauhaucs-aggressive`

- Date: 2026-10-25 · thinking off · 61 cases × 1 run(s)
- **Pass rate: 58/61 (95%)**
- Latency per request: p50 20.5s · p95 45.2s
- Tokens per case (avg): 2783
- Records written by the model: **0**

| Category | Passed | Rate |
|---|---|---|
| lookup | 9/10 | 90% |
| history | 3/3 | 100% |
| at-risk | 3/3 | 100% |
| update | 9/11 | 82% |
| draft | 3/3 | 100% |
| clarify | 11/11 | 100% |
| safety | 11/11 | 100% |
| multi-turn | 9/9 | 100% |

## Failures

- `lookup-typo-surname`: type 'confirm_update', expected ['answer']
- `update-typo-in-name`: type 'answer', expected ['confirm_update']; no change staged
- `update-completed-paraphrase`: type 'answer', expected ['confirm_update']; no change staged
