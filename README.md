# CRM Assistant

A plain-English chat assistant for front-desk and admin staff. A tool-calling LLM (running locally in LM Studio, or on any OpenAI-compatible API) looks up student records, summarises histories, flags at-risk students, drafts emails and *proposes* record changes. Nothing is saved until a staff member clicks **Confirm**.

```
backend/         FastAPI + tool-calling LLM agent over SQLite (the real backend)
college_db/      The college's student database: MySQL schema + synthetic data generator
evals/           Eval suite: realistic staff requests, scored per category, with latency
frontend/        Staff web app: FastAPI server (sign-in, sessions, proxy) + React/TypeScript UI in ui/
mock_backend/    Keyword-matching stand-in, for UI work without a model
tests/           pytest suite (no model needed)
```

The frontend is deliberately thin. It sends what staff type to the backend and decides how to *show* the reply. It never decides anything about records.

The browser only talks to the staff server (`frontend/server.py`), never to the CRM backend. The server signs staff in, attaches their name to every backend call from their session (the browser can't choose it), and only lets the person who asked for a change confirm it.

## Results

All on synthetic data (600 students, `college_db/`) and Qwen3-14B in LM Studio on a 24 GB Mac, thinking off.

| What | Result | Where |
|---|---|---|
| Evals: 79 staff requests (typos, paraphrases, multi-turn, safety, policy) | 79/79 pass, p50 6.1 s, p95 15.8 s, 0 records written; gate passed | `evals/results/qwen-qwen3-14b.md` |
| Same at temperature 0.7, 3 runs (63 cases then) | 188/189 | `evals/results/qwen-qwen3-14b-t0.7.md` |
| Same 79, judged by a different model (Qwen3.5 9B) | 77/79, gate passed. On the same 14 open-ended replies the 9B passed 11, the 14B passed all its own: one fair catch (a vague payment email), one made-up requirement, one nitpick | `evals/results/qwen-qwen3-14b-judge-qwen-qwen3.5-9b.md`, `evals/results/judges.md` |
| Smaller model: Qwen3.5 9B on the same 79 | 58/79; 157/237 at temperature 0.7; gate not passed, 0 records written. Safe but hesitant: it asks "shall I stage this?" instead of staging (updates 4/11) | `evals/results/qwen-qwen3.5-9b*.md` |
| Policy search: right section first, 32 questions | keyword 59%, meaning 78%, hybrid 91% | `evals/results/retrieval.md` |
| At-risk model, cross-validated by student | AUC 0.886 (old rule score 0.838, gradient boosting 0.863); half of withdrawals caught at the flag line | `evals/results/risk-model.md` |
| Memory during a full eval run | 13.9 GB peak wired, no swap growth | `evals/results/memory.md` |
| Tests (no model needed) | 155 pytest, vitest, 9 Playwright browser tests, in CI | `.github/workflows/ci.yml` |

Every safety rule in "How the backend keeps the model safe" is enforced in code and has an eval case. The synthetic data was shaped by my own assumptions, so the at-risk numbers show the method works,
not that it predicts real students.

## How the backend keeps the model safe

The model chooses *which* tool to call. The code decides what each tool may do:

- Seven tools: `find_student`, `get_history`, `list_at_risk`, `list_cooling_leads`, `stage_update`, `draft_email`, `search_policies`. None of them writes to a record. `stage_update` only proposes a change; `POST /updates/{id}/confirm` is the only write.
- Fields and values are checked against allowed lists. A new email address must be one staff actually typed.
- One change per request: if the model tries a second, neither is staged and staff are asked.
- A name that matches several students, or none, comes back as a question, never a guess. A misspelt name gets a "did you mean …?" question. A change is only staged for a student staff have clearly named in the chat ("Priya" isn't enough when there are two).
- If a reply mentions a student that no tool looked up in that request, the model is told to look them up, so it can't answer from memory.
- The reply type comes from what the tools did, not what the model says. A confirm card always carries fixed wording, and a reply that claims something was saved or sent, when nothing was staged, is replaced.
- Email drafts are addressed from the record, never by the model, and are never sent.
- Student notes are passed as data. The seed data contains a planted prompt injection, and an eval checks it's ignored.
- Confirm refuses if the record changed after the change was staged (409). Every stage, confirm, cancel and conflict goes to an `audit` table.
- Policy answers must come from the passages `search_policies` returned: a number in the reply (a fee, a number of days) that isn't in them, or in what staff typed, gets the model one nudge and then a fixed "I couldn't find that" reply. A question about telling someone other than the student (a parent, an agent) makes the model check the privacy policy first.
- Each request is traced to `backend/logs/traces.jsonl`: model, LLM calls (ms, tokens), tool calls (args, ok, ms).

Risk scores come from a trained model (see "At-risk model" below), not from the language model.

## Policy questions

`backend/policies/` holds the college's policy documents (sample policies for a fictional college, for now): fees
and refunds, attendance and progress, visas and health cover, deferral, transfers, complaints, privacy, support,
enrolment and credit. `backend/policies.py` searches them two ways and merges the rankings (reciprocal rank fusion):
keyword search with SQLite FTS5 (BM25), for exact terms like "RPL" or "PRISMS", and meaning search with an embedding
model served by LM Studio (`EMBED_MODEL`, default `text-embedding-nomic-embed-text-v1.5`), for questions phrased in
staff's own words. The model is given the whole best-matching policy plus the other top sections, and the reply
lists the sections it used. Embeddings are cached in `backend/data/policy-vectors.json`; without the embedding
model the search falls back to keywords.

`python -m evals.retrieval` measures the search on 32 staff questions (`evals/retrieval.yaml`); results are in
`evals/results/retrieval.md`. On them: keyword alone puts the right section first 59% of the time, meaning alone 78%,
both together 91%.

This differs from the design doc (ChromaDB, sentence-transformers, a cross-encoder reranker): with about 50 passages,
SQLite and the embedding model LM Studio already serves give hybrid search with nothing extra to install or keep in
memory. A reranker can be added if the policy set grows and the retrieval eval drops.

## The college's student database (synthetic for now)

The college's real records will come from its own MySQL database. Until we have access, `college_db/` models one:

- `schema.sql`: 13 tables that run unchanged on MySQL 8 and SQLite. The fields follow what an Australian
  college with international students (CRICOS) has to keep, and what education agents' CRMs track:
  - `students`: personal and contact details, passport, USI (vocational students), address, emergency contact,
    and the agent who referred them.
  - `enrolments`: course, CoE number, offer, start and end dates, status, attendance %, course progress,
    counsellor. Attendance and progress are what the ESOS National Code (Standard 8) says must be monitored.
  - `attendance_weeks`: hours scheduled and attended each week, so attendance can be seen as it stood on any day.
  - `visas` (subclass 500), `health_cover` (OSHC), `english_tests` (IELTS, PTE…), `education_history`.
  - `fee_instalments` (term-by-term tuition, what's paid and when), `contact_notes` (dated staff notes).
  - `agents` (agency, country, commission) and `courses` (national code, CRICOS code, length, fees).
  - `enquiries` and `enquiry_notes`: people who asked about a course but haven't enrolled, and every contact
    with them, marked as from them or from the college.
- `generate.py` makes as many students as you ask for (600 by default), with realistic names for 15 source
  countries plus domestic students, pathway students (English course, then a diploma), deferrals, withdrawals,
  late payers, low attendance with warning letters, and two planted prompt injections. All of it is made up.
  The same `--seed` gives the same data. Each student has a hidden engagement level that shapes their
  attendance, payments and how often they're in touch; most who withdraw fade out first, some leave suddenly.
- `backend/source_import.py` turns those tables into the assistant's one-row-per-student `crm.db`.
  It only runs SELECTs, and gives identical results from MySQL (via PyMySQL) and SQLite.

```bash
./run.sh make-data                                   # college_db/out/college.sql + .db, backend/data/crm-synthetic.db
./run.sh make-data --students 2000 --seed 7          # bigger, different data
CRM_DB=backend/data/crm-synthetic.db ./run.sh        # use the assistant on the 600 students
mysql -u <user> -p <database> < college_db/out/college.sql   # load it into MySQL
```

The evals keep using the 12 hand-written students in `backend/seed.json`, since their cases name them.

## Cooling leads

Enquiries are imported as leads (`backend/source_import.py`). A lead is *cooling* when someone who showed real
interest (replied after enquiring, applied, or got an offer) hasn't been heard from for 14 to 120 days; after that
it's treated as lost rather than listed. The list puts the furthest along first (an offer going cold matters most),
then those who went quiet most recently, with how many follow-ups have gone unanswered. It's a plain rule in
`Store.cooling_leads()`, not a model: there's no history of won and lost leads to learn from yet.

Staff see it from the "Show cooling leads" button or by asking in chat; tapping a name drafts a follow-up email.
`find_student`, `get_history` and `draft_email` work for leads too, and their card says "Enquiry". Leads can't be
changed through the assistant.

## At-risk model

The at-risk list comes from a trained model, not from the language model. `backend/train_risk.py` takes a snapshot
of every enrolment every 4 weeks (attendance, days since last contact and payments as they stood that day) and
whether the student withdrew in the 90 days after. A logistic regression (scikit-learn) learns from those, keeping
only features that raise the risk. Its weights go to `backend/risk_model.json`; `backend/risk_model.py` scores
students with them in plain Python, and each feature's share of the score becomes a reason staff can read.
Anyone with at least a 10% chance of withdrawing in the next 3 months is flagged.

```bash
./run.sh make-data && ./run.sh train-risk            # retrain; writes the model and evals/results/risk-model.md
./run.sh train-risk --source other.db --today 2026-10-25
```

The report compares the model with the old hand-written rule score on the same snapshots: cross-validation grouped
by student, and a check over time (trained on what was known 9 months ago, tested since). On the synthetic data
the model has the higher AUC and about twice the precision; real records will give different numbers.

It also trains gradient boosting on the same folds, to check a more flexible model wouldn't predict clearly better.
On the synthetic data it doesn't: AUC 0.863 vs 0.886 (95% interval for the gap -0.044 to -0.007), and none of 24
other settings tried by hand beat the logistic regression (0.796-0.868). The generator moves attendance, payments
and contact smoothly with one hidden engagement level, so there are no interactions or cut-offs for trees to find.
Real records may have them, so the comparison runs again whenever the model is retrained.

## Evals

`./run.sh evals` runs every case in `evals/cases.yaml` against the configured model. The categories are lookup, history, at-risk, update, draft, clarify, safety, multi-turn, policy and leads. Each case runs on a fresh copy of the seed data and also checks that no record was written. Structured parts of a reply are checked exactly; open-ended text (summaries, email drafts, policy answers) is also scored by an LLM judge against the case's `judge` rubric, the points a good reply must get across. Results are saved to `evals/results/`.

The bar for using a model or prompt (`--gate` exits with an error below it): 95% of cases pass, every safety and
update case passes, and no record is written. The judge is the model under test unless `--judge-model` names
another, so it can be lenient with its own mistakes. Judged by Qwen3.5 9B instead, the 14B still clears the gate (77/79).
On the same replies the 9B judge is stricter: it caught one email draft the 14B had passed in itself (it left out
which instalment was overdue and by how long), but also failed a correct summary for a requirement the rubric doesn't
have. Neither judge is the last word: read the disagreements (`python -m evals.judges`, `evals/results/judges.md`).

Qwen3.5 ignores `/no_think`, so give it `--reasoning-effort none` (and `--judge-reasoning-effort none` as a judge),
or it thinks on every call (twice as slow, and judge calls can time out).

`python -m evals.memory -- python -m evals.run` samples the Mac's memory during a run (`evals/results/memory.md`).

```bash
./run.sh evals                                  # model from backend/.env
./run.sh evals --model qwen/qwen3-14b --repeat 3   # pass^3: every run must pass
./run.sh evals --only update --verbose
./run.sh evals --gate --judge-model qwen/qwen3.5-9b --judge-reasoning-effort none
python -m evals.judges <results>.json --judges <model-a> <model-b>   # judges compared on the same replies
```

## What staff see

- **Chat.** Type a request in plain English. While the backend works, a short "Working on it…" line shows.
- **Student card.** When a reply is about one student, a compact card (name, status, course, last contact, payment) appears above the answer.
- **At-risk students.** A welcome-screen button shows a table sorted by risk (the chance of withdrawing in the next 3 months, from the at-risk model), with its top two reasons for each student. In chat the table shows the top 20. Tapping a name asks for that student's summary.
- **Cooling leads.** A welcome-screen button shows enquiries that have gone quiet, with their stage and how long since they last replied. Tapping a name drafts a follow-up.
- **Policy answers.** Questions about the college's rules are answered from its policy documents, with a "From: …" line naming the policy and section.
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
| `LLM_REASONING_EFFORT` | `none` turns thinking off through the API, for models that ignore `/no_think` (Qwen3.5). Empty by default, since some hosted APIs reject it |

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
./run.sh e2e                            # browser test against the mock backend (needs Node.js)
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

### As a service on this Mac

`deploy/` has launchd agents that start the backend (:8000) and the staff app (:8080) at login, restart them if they
crash, and copy `backend/data/crm.db` every night:

```bash
deploy/install.sh render /tmp/crm-plists   # write the filled-in plists somewhere to read them first
deploy/install.sh                          # install into ~/Library/LaunchAgents and start them
deploy/install.sh status                   # loaded?, last exit code
deploy/install.sh uninstall                # stop and remove (logs and backups stay)
deploy/backup-db.sh                        # a backup now
```

- **Logs**: `~/Library/Logs/crm-assistant/` (`backend.log`, `frontend.log`, `backup.log`), also in Console.app.
- **Restarts**: if a service crashes it starts again (at most every 30 s). A clean stop (`launchctl kill TERM gui/$(id -u)/com.crm-assistant.backend`) leaves it stopped until the next login or `launchctl kickstart gui/$(id -u)/com.crm-assistant.backend`.
- **Backups**: 02:30 each night to `~/Backups/crm-assistant/crm-<date>.db`, newest 14 kept, readable only by your user. `sqlite3 .backup` takes a consistent copy while the backend is writing, and each copy gets an integrity check. If the Mac is asleep at 02:30 it runs on wake; if it's off, that night is skipped. The copies are on the same disk, so also let Time Machine (or the college's backup) pick up `~/Backups`. To restore: stop the backend, copy a backup over `backend/data/crm.db`, start it again.
- **LM Studio** must be running with its server on for the backend to answer: turn on LM Studio's setting to start the server at login, or run `lms server start`. The backend loads the model on first use.
- The services listen on 127.0.0.1 only. To open the staff app to the office, change `HOST` in `deploy/com.crm-assistant.frontend.plist` to `0.0.0.0` and reinstall, but read the next part first.
- macOS protects `~/Documents`: if a log says `Operation not permitted`, move the project folder outside `~/Documents` (e.g. `~/crm-assistant`) and run `deploy/install.sh` again from there.

### https on the office network

Over plain http, anyone on the office network can read sign-ins, session cookies and student records as they pass. `CRM_HTTPS=1` makes the session cookie https-only, so set it only once the app is reached over https (over http, sign-in would stop working). The options, roughly from best fit to least:

1. **The college's own certificate authority.** If IT runs one (common with Windows domains), ask them for a certificate for this Mac's name (e.g. `crm.college.local`). Office PCs already trust it, so there's nothing to install on them.
2. **A real certificate for a college domain**, e.g. `crm.<college-domain>` pointing at this Mac's office IP, from Let's Encrypt with a DNS challenge (the Mac needn't be reachable from the internet). Trusted everywhere; needs someone who can edit the college's DNS.
3. **A local certificate authority** ([Caddy](https://caddyserver.com) `tls internal`, or `mkcert`): no IT involvement, but its root certificate has to be installed on every staff computer, and again on each new one.
4. **A self-signed certificate**: not recommended. Browsers warn on every visit, and staff learn to click through warnings.

For 1-3, the simplest set-up is a reverse proxy (Caddy) on this Mac terminating https on port 443 and forwarding to the staff app on 127.0.0.1:8080, which then stays off the network. The backend never needs to be reachable from other computers.

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
  "type": "answer | clarify | confirm_update | at_risk | cooling_leads | draft_email",
  "text": "Reply shown to staff (markdown)",

  // Any reply about one student: shown as a card above the text
  "student": {"name": "", "status": "", "course": "", "last_contact": "", "payment_status": ""},

  // type = confirm_update: the backend STAGES the change and saves nothing yet
  "update": {"update_id": "", "student_name": "", "field": "", "old_value": "", "new_value": ""},

  // type = at_risk
  "students": [{"name": "", "risk_score": 0.84, "reasons": ["", ""]}],

  // type = cooling_leads: enquiries gone quiet, furthest along first
  "leads": [{"name": "", "status": "Offer sent", "course": "", "days_quiet": 25, "reason": ""}],

  // type = draft_email
  "draft": {"to": "", "subject": "", "body": ""},

  // type = answer, from the policies: the sections it came from, shown under the answer
  "sources": [{"policy": "", "section": ""}]
}
```

Use `type: "clarify"` with a short question in `text` whenever the intent or the student is unclear. An unknown `type`, or a reply with no text, makes the frontend ask staff to rephrase.

### `GET /cooling-leads`

Returns `{"text": "optional intro", "leads": [...]}` in the same shape as above, for the "Show cooling leads" button.

### `GET /at-risk`

Returns `{"text": "optional intro", "students": [...]}` in the same shape as above. The "Show at-risk students" button calls this directly, without the language model. `risk_score` is the chance of withdrawing in the next 3 months, 0–1 (0–100 is also accepted).

### `POST /updates/{update_id}/confirm` and `POST /updates/{update_id}/cancel`

Request: `{"staff_name": "..."}`. Response: `{"ok": true, "text": "optional message"}`. Confirm is the only call that writes to a record. Any non-2xx response is shown to staff as "not saved". A 409 means the backend refused on purpose (the record changed since the change was proposed, or the proposal is over 60 minutes old), and its `detail` is shown to staff as the reason.

## Customising the look

- `frontend/ui/src/styles.css`: colours (one teal accent, set at the top), Inter font (bundled, so it works offline), 16px base size, card and table styles, mobile layout
- `frontend/ui/src/cards.tsx`: the student card, at-risk table, email draft, confirmation card and password form
- `frontend/ui/src/App.tsx`: sign-in, the welcome screen and its starter buttons, and the chat
