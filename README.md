# CRM Assistant

A plain-English chat assistant for front-desk and admin staff. A tool-calling LLM (running locally in LM Studio, or on any OpenAI-compatible API) looks up student records, summarises histories, flags at-risk students, drafts emails and *proposes* record changes. Nothing is saved until a staff member clicks **Confirm**.

```
backend/         FastAPI + tool-calling LLM agent over SQLite (the real backend)
evals/           Eval suite: realistic staff requests, scored per category, with latency
frontend/        Staff web app: FastAPI server (sign-in, sessions, proxy) + React/TypeScript UI in ui/
mock_backend/    Keyword-matching stand-in, for UI work without a model
tests/           pytest suite (no model needed)
```

The frontend is deliberately thin. It sends what staff type to the backend and decides how to *show* the reply. It never decides anything about records.

The browser only talks to the staff server (`frontend/server.py`), never to the CRM backend. The server signs staff in, attaches their name to every backend call from their session (the browser can't choose it), and only lets the person who asked for a change confirm it.

## How the backend keeps the model safe

The model chooses *which* tool to call. The code decides what each tool may do:

- Five tools: `find_student`, `get_history`, `list_at_risk`, `stage_update`, `draft_email`. None of them writes to a record. `stage_update` only proposes a change; `POST /updates/{id}/confirm` is the only write.
- Fields and values are checked against allowed lists. A new email address must be one staff actually typed.
- One change per request: if the model tries a second, neither is staged and staff are asked.
- A name that matches several students, or none, comes back as a question, never a guess. A misspelt name gets a "did you mean …?" question. A change is only staged for a student staff have clearly named in the chat ("Priya" isn't enough when there are two).
- If a reply mentions a student that no tool looked up in that request, the model is told to look them up, so it can't answer from memory.
- The reply type comes from what the tools did, not what the model says. A confirm card always carries fixed wording, and a reply that claims something was saved or sent, when nothing was staged, is replaced.
- Email drafts are addressed from the record, never by the model, and are never sent.
- Student notes are passed as data. The seed data contains a planted prompt injection, and an eval checks it's ignored.
- Confirm refuses if the record changed after the change was staged (409). Every stage, confirm, cancel and conflict goes to an `audit` table.
- Each request is traced to `backend/logs/traces.jsonl`: model, LLM calls (ms, tokens), tool calls (args, ok, ms).

Risk scores come from transparent rules in `backend/store.py` (days since contact, payment, attendance), not from the model.

## Evals

`./run.sh evals` runs every case in `evals/cases.yaml` against the configured model. The categories are lookup, history, at-risk, update, draft, clarify, safety and multi-turn. Each case runs on a fresh copy of the seed data and also checks that no record was written. Results are saved to `evals/results/`.

```bash
./run.sh evals                                  # model from backend/.env
./run.sh evals --model qwen/qwen3-14b --repeat 3   # pass^3: every run must pass
./run.sh evals --only update --verbose
```

## What staff see

- **Chat.** Type a request in plain English. While the backend works, a short "Working on it…" line shows.
- **Student card.** When a reply is about one student, a compact card (name, status, course, last contact, payment) appears above the answer.
- **At-risk students.** A welcome-screen button shows a table sorted by risk, with the model's top two reasons for each student. Tapping a name asks for that student's summary.
- **Draft emails.** Drafts appear in editable boxes with a **Copy** button. Nothing is ever sent from here.
- **Confirmed changes.** Any change to a record shows a card (student, field, old value → new value) with **Confirm** and **Cancel**. Nothing is saved until Confirm is clicked. The buttons disappear after one click, so a change can't be saved twice.
- **When things go wrong.** If the backend is down, slow, or the request is unclear, the assistant asks a short question instead of guessing.

## Setup (first time)

Uses the `crmenv` conda environment.

```bash
conda create -n crmenv python=3.12 -y     # skip if it already exists
conda activate crmenv
pip install -r requirements-dev.txt     # backend, frontend, mock and test dependencies
```

**Model.** Install [LM Studio](https://lmstudio.ai), download a tool-calling model (e.g. Qwen3 14B) and start its server
(Developer tab, or `lms server start`). Then:

```bash
cp backend/.env.example backend/.env   # set LLM_MODEL to the id LM Studio shows
```

| Setting (`backend/.env`) | Meaning |
|---|---|
| `LLM_BASE_URL` | OpenAI-compatible server, default LM Studio `http://localhost:1234/v1` |
| `LLM_MODEL` | Model id |
| `LLM_API_KEY` | Only for hosted APIs |
| `LLM_NO_THINK` | `1` (default) adds `/no_think` so Qwen3-style models skip hidden reasoning (several times faster) |

The database is created and seeded from `backend/seed.json` on first run at `backend/data/crm.db`. Delete that file to reset it.

**Frontend.** The staff app needs [Node.js](https://nodejs.org) to build its UI (`run.sh` builds it the first time and
whenever the UI's source changes). Create `frontend/.env` from the example and fill it in:

```bash
cd frontend
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'   # paste into CRM_SESSION_SECRET in .env
chmod 600 .env              # only your user account can read the secret
```

| Setting | Meaning |
|---|---|
| `CRM_API_BASE_URL` | Where the FastAPI backend runs, e.g. `http://localhost:8000` |
| `CRM_API_TIMEOUT` | Seconds to wait before asking staff to retry (default 60) |
| `CRM_SESSION_SECRET` | Signs login sessions. Keep it private. (An older `.env` with `CHAINLIT_AUTH_SECRET` still works.) |
| `CRM_HTTPS` | `1` when served over https, so the session cookie is only sent encrypted |

Sessions are a signed, HttpOnly, SameSite=Strict cookie that lasts 12 hours (one working day).

### Staff logins

Each staff member gets their own login, so every saved change is recorded under their name.

```bash
./run.sh add-staff priya "Priya Shah"       # asks you for a temporary password (8+ characters)
cd frontend && python add_staff.py --remove priya   # remove a login
```

Logins are stored as salted hashes in `frontend/staff.json`, readable only by your user account. Running `add-staff` again for an existing username resets that person to a new temporary password, which is how you handle a forgotten password.

Removing or resetting a login, or the person changing their own password, ends their other open sessions straight away: their next message asks them to sign in again.

### Signing in

1. Start the app (`./run.sh`) and open **http://localhost:8080**. On another office computer, use `http://<this-computer's-IP>:8080`, with the app started as `HOST=0.0.0.0 ./run.sh`.
2. Enter the **username** (e.g. `priya`, not the full name) and the temporary password you gave them.
3. The first time, the app asks them to choose their own password before they can do anything else. After that they sign in with their own password.

Staff can change their password any time by typing **"change my password"** in the chat. The password form talks only to the staff server: the password never appears in the chat history and is never sent to the CRM backend.

## Running

The quickest way is `run.sh` from the project folder (no need to activate the environment):

```bash
./run.sh add-staff priya "Priya Shah"   # first time only
./run.sh                                # backend + frontend together (Ctrl+C stops both)
./run.sh backend                        # backend only
BACKEND=mock ./run.sh                   # keyword mock instead of the LLM (no model needed)
./run.sh frontend                       # frontend only, e.g. against the real backend
./run.sh test                           # run the tests (needs: pip install -r requirements-dev.txt)
```

Ports and host can be changed: `BACKEND_PORT=8001 FRONTEND_PORT=9000 HOST=0.0.0.0 ./run.sh`.

To run them by hand instead:

**1. Backend.** From the project folder, start the LLM backend, or the mock:

```bash
uvicorn --factory backend.app:default_app --port 8000
cd mock_backend && uvicorn main:app --port 8000   # or the mock
```

**2. Frontend**

```bash
cd frontend/ui && npm ci && npm run build && cd ..   # after any UI change
uvicorn server:app --port 8080
```

While working on the UI, `./run.sh ui-dev` serves it with hot reload on http://localhost:5173 (run `./run.sh frontend`
alongside; `/api` is passed through to it). `cd frontend/ui && npm test` runs the UI tests.

Open http://localhost:8080 and sign in. To let other computers in the office use it, run with `--host 0.0.0.0` and share `http://<this-computer's-IP>:8080`.

Try: *"find Liam"*, *"summarise Sofia's history"*, *"change Arjun's status to Withdrawn"*, *"draft a follow-up email for Liam about his overdue payment"*, *"find Priya"* (two students match, so it asks which).

## Audit trail

Every confirmed change is logged twice:

- by the **backend**, which receives the staff member's name in the `X-Staff-Name` header and in the request body;
- by the **frontend**, in `frontend/logs/writes.log` (time, staff name, student, field, old and new values).

## Backend API contract

The frontend expects these endpoints. All requests carry the header `X-Staff-Name: <display name>`.

### `POST /chat`

Request: `{"message": "...", "staff_name": "...", "session_id": "..."}`

Response (every field except `type` is optional):

```jsonc
{
  "type": "answer | clarify | confirm_update | at_risk | draft_email",
  "text": "Reply shown to staff (markdown)",

  // Any reply about one student: shown as a card above the text
  "student": {"name": "", "status": "", "course": "", "last_contact": "", "payment_status": ""},

  // type = confirm_update: the backend STAGES the change and saves nothing yet
  "update": {"update_id": "", "student_name": "", "field": "", "old_value": "", "new_value": ""},

  // type = at_risk
  "students": [{"name": "", "risk_score": 0.84, "reasons": ["", ""]}],

  // type = draft_email
  "draft": {"to": "", "subject": "", "body": ""}
}
```

Use `type: "clarify"` with a short question in `text` whenever the intent or the student is unclear. An unknown `type`, or a reply with no text, makes the frontend ask staff to rephrase.

### `GET /at-risk`

Returns `{"text": "optional intro", "students": [...]}` in the same shape as above. The "Show at-risk students" button calls this directly, without the language model. `risk_score` may be 0–1 or 0–100.

### `POST /updates/{update_id}/confirm` and `POST /updates/{update_id}/cancel`

Request: `{"staff_name": "..."}`. Response: `{"ok": true, "text": "optional message"}`. Confirm is the only call that writes to a record. Any non-2xx response is shown to staff as "not saved". A 409 means the backend refused on purpose (the record changed since the change was proposed, or the proposal is over 60 minutes old), and its `detail` is shown to staff as the reason.

## Customising the look

- `frontend/ui/src/styles.css`: colours (one teal accent, set at the top), Inter font (bundled, so it works offline), 16px base size, card and table styles, mobile layout
- `frontend/ui/src/cards.tsx`: the student card, at-risk table, email draft, confirmation card and password form
- `frontend/ui/src/App.tsx`: sign-in, the welcome screen and its starter buttons, and the chat
