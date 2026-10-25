# Plan: real LLM backend + evals

Goal: replace the keyword mock with a real tool-calling LLM backend that runs on a local model (LM Studio),
keeps the existing API contract (README.md), and is measured by an eval suite.

## Design
- **`backend/`** is a FastAPI app with the same endpoints as `mock_backend/` (`/chat`, `/at-risk`,
  `/updates/{id}/confirm|cancel`), so the frontend and its tests don't change.
- **LLM access** goes through the OpenAI-compatible API. `LLM_BASE_URL` / `LLM_MODEL` in `backend/.env` point at
  LM Studio for development, or at a hosted model for a public demo.
- **Tools** (the only way the model touches data):
  | Tool | Does | Writes? |
  |---|---|---|
  | `find_student(name)` | look up a record, shown as a card | no |
  | `get_history(name)` | notes for a summary | no |
  | `list_at_risk()` | ranked list with reasons (scored in code, not by the model) | no |
  | `stage_update(name, field, new_value)` | validates and *stages* a change | no |
  | `draft_email(name, subject, body)` | `to` comes from the record, never from the model | no |
- **Safety lives in code, not the prompt:**
  - Only `POST /updates/{id}/confirm` writes.
  - Fields and values are checked against allowed lists.
  - Names that match several students, or none, come back as a question, never a guess.
  - The model's text can't claim a change was saved: the confirm card has fixed wording.
  - Student notes are treated as data (there's a prompt-injection test case).
  - Confirm refuses if the record changed after the change was staged.
- **Data:** SQLite (`backend/data/crm.db`, created and seeded on first run from `backend/seed.json`). Staged
  changes and the audit trail are tables, not log lines.
- **Tracing:** one JSON line per request in `backend/logs/traces.jsonl`: model, every LLM call (ms, tokens), every
  tool call (args, ok, ms), total ms.
- **Conversation memory:** the last few turns per session, so "change her status" works after "find Sofia".

## Evals (`evals/`)
- `cases.yaml`: about 35 staff requests in these categories: lookup, history, at-risk, update, draft, clarify,
  safety, and multi-turn.
- Each case states the expected reply type, tool, student and update. Every case also checks that **no record
  was written**.
- `python -m evals.run --model <id>` gives the pass rate per category plus p50/p95 latency, and saves the results
  to `evals/results/`. `--repeat k` reports pass^k (every one of k runs passes).
- Compare the models you have: Qwen3 14B and the official Qwen3.5 9B.

## Tests
- Unit tests use a scripted fake LLM: tool routing, name ambiguity, value checks, one change per turn,
  confirm/cancel/conflict, the audit trail, the reply format, and the trace.
- Evals are kept out of `pytest` because they need LM Studio and are slow.

## Out of scope (later)
- React + TypeScript frontend (see PROGRESS.md).
- Hosted deployment and live demo.
- Streaming replies.
