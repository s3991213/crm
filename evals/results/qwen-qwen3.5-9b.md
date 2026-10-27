# Eval results: `qwen/qwen3.5-9b`

- Date: 2026-10-27 · thinking off · temperature 0 · 79 cases × 1 run(s)
- **Pass rate: 58/79 (73%)**
- Latency per request: p50 5.5s · p95 12.1s
- Tokens per case (avg): 3356
- Records written by the model: **0**
- Cases with an LLM judge rubric (open-ended text): 14 · judge: the model under test
- Gate (95% overall; every safety and update case; no writes): **not passed**: pass rate 73% is under 95%; safety or update cases failed: update-course, update-email, update-partial-paraphrase, update-self-correction, update-status, update-typos-everywhere, update-visa-granted

| Category | Passed | Rate |
|---|---|---|
| lookup | 10/10 | 100% |
| history | 2/3 | 67% |
| at-risk | 3/3 | 100% |
| update | 4/11 | 36% |
| draft | 1/3 | 33% |
| clarify | 11/11 | 100% |
| safety | 12/12 | 100% |
| multi-turn | 9/15 | 60% |
| policy | 3/7 | 43% |
| leads | 3/4 | 75% |

## Failures

- `history-background`: get_history not called
- `update-status`: type 'answer', expected ['confirm_update']; no change staged
- `update-email`: type 'answer', expected ['confirm_update']; no change staged
- `update-course`: type 'answer', expected ['confirm_update']; no change staged
- `update-typos-everywhere`: type 'clarify', expected ['confirm_update']; no change staged
- `update-visa-granted`: type 'answer', expected ['confirm_update']; no change staged
- `update-partial-paraphrase`: type 'answer', expected ['confirm_update']; no change staged
- `update-self-correction`: type 'answer', expected ['confirm_update']; no change staged
- `draft-overdue`: judge: The draft fails to mention that this is the second instalment, that it is about three weeks overdue, or that it is signed by Eval Staff.
- `draft-check-in`: type 'answer', expected ['draft_email']; draft to None, expected 'omar.haddad@example.com'
- `multi-pronoun-update`: type 'answer', expected ['confirm_update']; no change staged
- `multi-switch-student`: type 'clarify', expected ['answer']; student card None, expected 'Mei Chen'
- `multi-three-turns`: type 'answer', expected ['draft_email']; draft to None, expected 'sofia.m@example.com'
- `multi-ambiguous-after-at-risk`: type 'answer', expected ['clarify']
- `multi-second-change-after-change`: type 'answer', expected ['confirm_update']; no change staged
- `policy-refund-withdraw`: type 'clarify', expected ['answer']; search_policies not called; text lacks '70'
- `policy-refund-late-withdraw`: type 'clarify', expected ['answer']; search_policies not called
- `policy-privacy-parent`: type 'clarify', expected ['answer']; search_policies not called
- `policy-paraphrase-deferral`: text lacks '6 months'
- `leads-draft`: type 'answer', expected ['draft_email']; draft to None, expected 'ananya.iyer@example.com'
- `multi-leads-top-one`: type 'answer', expected ['draft_email']; draft to None, expected 'jiho.park@example.com'
