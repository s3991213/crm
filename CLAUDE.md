# CRM Assistant

Staff chat frontend (Chainlit, `frontend/`) for a FastAPI CRM backend. `mock_backend/` is a stand-in for the
real backend. The API contract lives in README.md ("Backend API contract"): keep the frontend and the mock in
line with it.

## Commands
- Python env is the `crmenv` conda environment. `run.sh` finds it itself, so there's no need to activate it.
- `./run.sh test` runs pytest (args pass through, e.g. `./run.sh test -k auth`). Run it after every change.
- `./run.sh` starts mock backend (:8000) + frontend (:8080). Don't leave it running after checking something.
- First-time dev deps: `~/miniconda3/envs/crmenv/bin/pip install -r requirements-dev.txt`

## Rules
- The frontend stays thin: it only decides how to *show* backend replies. Record logic belongs in the backend.
- IMPORTANT: nothing writes to a record except `POST /updates/{id}/confirm`, after staff click Confirm.
  Email drafts are never sent.
- Every backend call carries `X-Staff-Name`; every confirmed change is also logged to `frontend/logs/writes.log`.
- Passwords never go to the CRM backend or into chat history. They go only through the `change_password`
  action and `staff_auth.py`.
- Never read, print or commit `frontend/.env` or `frontend/staff.json` (secrets / password hashes).
- Staff-facing text is plain, friendly English with no jargon. When unsure, ask a short question instead of guessing.

## Testing notes
- `app.py` needs a Chainlit context and has no unit tests; check UI changes with `./run.sh` and a screenshot.
- Tests reset the mock's in-memory `STUDENTS`/`PENDING` and point `staff_auth.STAFF_FILE` at a temp file
  (see `tests/conftest.py`).
