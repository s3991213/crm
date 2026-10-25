# CRM Assistant

Staff chat frontend (`frontend/`: FastAPI `server.py` for sign-in/sessions/proxy + React/TypeScript/Vite UI in `ui/`) for a FastAPI backend (`backend/`) where a tool-calling LLM works over
SQLite records. `mock_backend/` is a keyword stand-in. The API contract lives in README.md ("Backend API contract"):
keep the frontend, backend and mock in line with it. The plan for the backend is in PLAN.md.

## Progress log
@PROGRESS.md

IMPORTANT: after finishing any piece of work, update PROGRESS.md in the same turn: add a short dated entry at
the top of "Log" and tick, add or remove items in "Up next". Keep entries short; the details belong in git.

## Commands
- Python env is the `crmenv` conda environment. `run.sh` finds it itself, so there's no need to activate it.
- `./run.sh test` runs pytest (args pass through, e.g. `./run.sh test -k auth`). Run it after every change.
- `./run.sh` starts the LLM backend (:8000) + frontend (:8080); `BACKEND=mock ./run.sh` for no model. Don't leave it running.
- `./run.sh evals [--only <id>] [--model <id>]` runs the LLM evals against LM Studio (localhost:1234). They're slow
  (~10-20 s per case), so use `--only` while iterating. After changing the prompt, tools or `store.py`,
  run the full suite and commit `evals/results/`.
- First-time dev deps: `~/miniconda3/envs/crmenv/bin/pip install -r requirements-dev.txt`

## Rules
- The frontend stays thin: it only decides how to *show* backend replies. Record logic belongs in the backend.
- IMPORTANT: nothing writes to a record except `POST /updates/{id}/confirm` (`Store.confirm`), after staff click
  Confirm. Agent tools may only read or stage. Email drafts are never sent.
- Enforce safety in code (store/agent), not just the system prompt; add an eval case for every new rule.
- Every backend call carries `X-Staff-Name`; every confirmed change is also logged to `frontend/logs/writes.log`.
- Passwords never go to the CRM backend or into chat history. They go only through the `change_password`
  action and `staff_auth.py`.
- Never read, print or commit `frontend/.env` or `frontend/staff.json` (secrets / password hashes).
- Staff-facing text is plain, friendly English with no jargon. When unsure, ask a short question instead of guessing.

## Testing notes
- `tests/test_server.py` covers the staff server (sessions, password rules, proxying) against the mock.
- UI logic that maps replies to cards is in `ui/src/reply.ts` (vitest: `cd frontend/ui && npm test`). Check visual
  changes in a browser with a screenshot; `./run.sh` rebuilds the UI when its source changes (needs Node.js).
- `tests/test_backend.py` drives the agent with a scripted `FakeLLM`: no model needed.
- Tests reset the mock's in-memory `STUDENTS`/`PENDING` and point `staff_auth.STAFF_FILE` at a temp file
  (see `tests/conftest.py`).
