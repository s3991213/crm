# CRM Assistant: staff frontend

A plain-English chat app for front-desk and admin staff, built with Chainlit and connected to the CRM Assistant FastAPI backend.

```
frontend/        Chainlit app (what staff use)
mock_backend/    Stand-in FastAPI backend for trying the UI without the real one
```

The frontend is deliberately thin. It sends what staff type to the backend and decides how to *show* the reply. It never decides anything about records.

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
pip install -r frontend/requirements.txt
pip install -r mock_backend/requirements.txt   # only needed for the mock
```

Create `frontend/.env` from the example and fill it in:

```bash
cd frontend
cp .env.example .env
chainlit create-secret      # paste the printed CHAINLIT_AUTH_SECRET into .env
```

| Setting | Meaning |
|---|---|
| `CRM_API_BASE_URL` | Where the FastAPI backend runs, e.g. `http://localhost:8000` |
| `CRM_API_TIMEOUT` | Seconds to wait before asking staff to retry (default 60) |
| `CHAINLIT_AUTH_SECRET` | Signs login sessions. Keep it private. |

### Staff logins

Each staff member gets their own login, so every saved change is recorded under their name.

```bash
./run.sh add-staff priya "Priya Shah"       # asks you for a temporary password (8+ characters)
cd frontend && python add_staff.py --remove priya   # remove a login
```

Logins are stored as salted hashes in `frontend/staff.json`. Running `add-staff` again for an existing username resets that person to a new temporary password, which is how you handle a forgotten password.

### Signing in

1. Start the app (`./run.sh`) and open **http://localhost:8080**. On another office computer, use `http://<this-computer's-IP>:8080`, with the app started as `HOST=0.0.0.0 ./run.sh`.
2. Enter the **username** (e.g. `priya`, not the full name) and the temporary password you gave them.
3. The first time, the app asks them to choose their own password before they can do anything else. After that they sign in with their own password.

Staff can change their password any time by typing **"change my password"** in the chat. The password form talks only to the Chainlit server: the password never appears in the chat history and is never sent to the CRM backend.

## Running

The quickest way is `run.sh` from the project folder (no need to activate the environment):

```bash
./run.sh add-staff priya "Priya Shah"   # first time only
./run.sh                                # mock backend + frontend together (Ctrl+C stops both)
./run.sh backend                        # mock backend only
./run.sh frontend                       # frontend only, e.g. against the real backend
./run.sh test                           # run the tests (needs: pip install -r requirements-dev.txt)
```

Ports and host can be changed: `BACKEND_PORT=8001 FRONTEND_PORT=9000 HOST=0.0.0.0 ./run.sh`.

To run them by hand instead:

**1. Backend.** Start the real FastAPI backend, or the mock:

```bash
cd mock_backend
uvicorn main:app --port 8000
```

**2. Frontend**

```bash
cd frontend
chainlit run app.py --port 8080
```

Open http://localhost:8080 and sign in. To let other computers in the office use it, run with `--host 0.0.0.0` and share `http://<this-computer's-IP>:8080`.

With the mock backend, try: *"find Liam"*, *"summarise Sofia's history"*, *"change Arjun's status to Withdrawn"*, *"draft a follow-up email for Priya"*.

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

Request: `{"staff_name": "..."}`. Response: `{"ok": true, "text": "optional message"}`. Confirm is the only call that writes to a record. Any non-2xx response is shown to staff as "not saved".

## Customising the look

- `frontend/.chainlit/config.toml`: app name, light theme, hidden extras (file upload, message editing, step details)
- `frontend/public/theme.json`: colours (one teal accent) and font (Inter)
- `frontend/public/custom.css`: spacing, 16px base size, card and table styles, mobile layout
- `frontend/public/elements/*.jsx`: the student card, at-risk table, email draft and confirmation card
