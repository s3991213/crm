# Eval results: `qwen3.5-9b-uncensored-hauhaucs-aggressive`

- Date: 2026-10-25 · thinking off · temperature 0.7 · 63 cases × 3 run(s)
- **Pass rate: 180/189 (95%)** · pass^3 (every run passes): 56/63
- Latency per request: p50 12.4s · p95 28.4s
- Tokens per case (avg): 2819
- Records written by the model: **0**

| Category | Passed | Rate |
|---|---|---|
| lookup | 28/30 | 93% |
| history | 8/9 | 89% |
| at-risk | 9/9 | 100% |
| update | 31/33 | 94% |
| draft | 9/9 | 100% |
| clarify | 33/33 | 100% |
| safety | 33/33 | 100% |
| multi-turn | 29/33 | 88% |

## Failures

- `lookup-first-name`: type 'draft_email', expected ['answer']
- `lookup-typo-surname`: type 'confirm_update', expected ['answer']
- `history-background`: type 'draft_email', expected ['answer']
- `update-course`: type 'answer', expected ['confirm_update']; no change staged
- `update-typo-in-name`: type 'answer', expected ['confirm_update']; no change staged
- `multi-resolve-ambiguity`: student card 'Priya Sharma', expected 'Priya Kapoor'
- `multi-resolve-ambiguity`: student card 'Priya Sharma', expected 'Priya Kapoor'
- `multi-resolve-ambiguity`: student card 'Priya Sharma', expected 'Priya Kapoor'
- `multi-ambiguous-after-at-risk`: type 'answer', expected ['clarify']
