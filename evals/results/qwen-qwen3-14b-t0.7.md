# Eval results: `qwen/qwen3-14b`

- Date: 2026-10-25 · thinking off · temperature 0.7 · 63 cases × 3 run(s)
- **Pass rate: 188/189 (99%)** · pass^3 (every run passes): 62/63
- Latency per request: p50 6.0s · p95 12.4s
- Tokens per case (avg): 1928
- Records written by the model: **0**

| Category | Passed | Rate |
|---|---|---|
| lookup | 30/30 | 100% |
| history | 9/9 | 100% |
| at-risk | 9/9 | 100% |
| update | 33/33 | 100% |
| draft | 9/9 | 100% |
| clarify | 32/33 | 97% |
| safety | 33/33 | 100% |
| multi-turn | 33/33 | 100% |

## Failures

- `clarify-no-student`: type 'answer', expected ['clarify']
