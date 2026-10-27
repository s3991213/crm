# Judges compared on the same replies (`qwen-qwen3-14b-judge-qwen-qwen3.5-9b.json`)

14 judged replies (open-ended text that passed the exact checks).

| Judge | Passed |
|---|---|
| `qwen/qwen3-14b` | 14/14 |
| `qwen/qwen3.5-9b` | 11/14 |

## Disagreements (3)

- `history-summary`: `qwen/qwen3-14b` pass; `qwen/qwen3.5-9b` judge: The reply fails to include the student's full name (Sofia Martinez) as required.
- `draft-overdue`: `qwen/qwen3-14b` pass; `qwen/qwen3.5-9b` judge gave no verdict: '{"pass": false, "reason": "The reply fails because it omits the specific details'
- `leads-draft`: `qwen/qwen3-14b` pass; `qwen/qwen3.5-9b` judge: The draft fails to specify that the application is for the Diploma of Nursing, which is a required point.
