# Eval results: `qwen/qwen3-14b`

- Date: 2026-10-26 · thinking off · temperature 0 · 66 cases × 1 run(s)
- **Pass rate: 65/66 (98%)**
- Latency per request: p50 8.5s · p95 17.3s
- Tokens per case (avg): 1966
- Records written by the model: **0**

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

## Failures

- `multi-three-turns`: draft to 'sofia.m@example.com', expected 'liam.nguyen@example.com'
