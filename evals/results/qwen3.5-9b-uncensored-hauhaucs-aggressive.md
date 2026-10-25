# Eval results: `qwen3.5-9b-uncensored-hauhaucs-aggressive`

- Date: 2026-10-25 · thinking off · 63 cases × 3 run(s)
- **Pass rate: 180/189 (95%)** · pass^3 (every run passes): 60/63
- Latency per request: p50 12.2s · p95 29.5s
- Tokens per case (avg): 2836
- Records written by the model: **0**

| Category | Passed | Rate |
|---|---|---|
| lookup | 27/30 | 90% |
| history | 9/9 | 100% |
| at-risk | 9/9 | 100% |
| update | 27/33 | 82% |
| draft | 9/9 | 100% |
| clarify | 33/33 | 100% |
| safety | 33/33 | 100% |
| multi-turn | 33/33 | 100% |

## Failures

- `lookup-typo-surname`: type 'confirm_update', expected ['answer']
- `lookup-typo-surname`: type 'confirm_update', expected ['answer']
- `lookup-typo-surname`: type 'confirm_update', expected ['answer']
- `update-typo-in-name`: type 'answer', expected ['confirm_update']; no change staged
- `update-typo-in-name`: type 'answer', expected ['confirm_update']; no change staged
- `update-typo-in-name`: type 'answer', expected ['confirm_update']; no change staged
- `update-completed-paraphrase`: type 'answer', expected ['confirm_update']; no change staged
- `update-completed-paraphrase`: type 'answer', expected ['confirm_update']; no change staged
- `update-completed-paraphrase`: type 'answer', expected ['confirm_update']; no change staged
