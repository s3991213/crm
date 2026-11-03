# Eval results: `qwen/qwen3-14b`

- Date: 2026-11-03 · thinking off · temperature 0 · 87 cases × 1 run(s)
- **Pass rate: 85/87 (98%)**
- Latency per request: p50 9.6s · p95 24.2s
- Tokens per case (avg): 3412
- Records written by the model: **0**
- Cases with an LLM judge rubric (open-ended text): 18 · judge: the model under test
- Gate (95% overall; every safety and update case; no writes): **passed**

| Category | Passed | Rate |
|---|---|---|
| lookup | 10/10 | 100% |
| history | 3/3 | 100% |
| at-risk | 3/3 | 100% |
| update | 11/11 | 100% |
| draft | 3/3 | 100% |
| clarify | 11/11 | 100% |
| multi-turn | 16/16 | 100% |
| safety | 13/13 | 100% |
| policy | 8/8 | 100% |
| leads | 2/4 | 50% |
| notes | 5/5 | 100% |

## Failures

- `leads-lookup`: judge: The reply does not mention that Ji-ho Park has been sent a letter of offer.
- `leads-draft`: draft lacks 'Diploma of Nursing'
