# Eval results: `qwen/qwen3-14b`

- Date: 2026-11-03 · thinking off · temperature 0 · 86 cases × 1 run(s)
- **Pass rate: 84/86 (98%)**
- Latency per request: p50 8.5s · p95 25.6s
- Tokens per case (avg): 3322
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
| clarify | 10/11 | 91% |
| safety | 13/13 | 100% |
| multi-turn | 15/15 | 100% |
| policy | 8/8 | 100% |
| leads | 3/4 | 75% |
| notes | 5/5 | 100% |

## Failures

- `clarify-no-value`: type 'confirm_update', expected ['clarify', 'answer']; staged a change: Arjun Patel Payment status -> Overdue
- `leads-draft`: draft lacks 'Diploma of Nursing'
