"""CRM Assistant: the staff web server.

Serves the React app (ui/dist) and a small /api for it. Kept deliberately thin:
it signs staff in, passes their requests to the CRM backend with their name
attached, and returns the backend's replies untouched for the UI to show.

Passwords stop here: they go only to staff_auth, never to the CRM backend.
Run from frontend/:  uvicorn server:app --port 8080
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

from fastapi import FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import api  # noqa: E402
import staff_auth  # noqa: E402
import state  # noqa: E402

COOKIE = "crm_session"
SESSION_HOURS = 12  # staff sign in once per working day (shared front-desk PCs)
UI_DIR = Path(os.getenv("CRM_UI_DIR", HERE / "ui" / "dist"))
WRITES_LOG = Path(os.getenv("CRM_WRITES_LOG", HERE / "logs" / "writes.log"))
# Older .env files only have the Chainlit secret; it signs sessions just as well.
SECRET = os.getenv("CRM_SESSION_SECRET") or os.getenv("CHAINLIT_AUTH_SECRET") or ""

SIGNED_OUT = "Your session has ended. Please sign in again."
CLARIFY_SLOW = "That took longer than expected. Would you like me to try again?"
CLARIFY_DOWN = (
    "I couldn't reach the student records just now. Would you like to try again in a minute? "
    "If it keeps happening, please let your manager know."
)
PASSWORD_FIRST = "Please choose your new password first. It only takes a moment."
TOO_MANY_TRIES = "Too many wrong passwords. Please wait a minute and try again."
MAX_FAILS, LOCK_SECONDS = 5, 60  # per username, so guessing a password takes years, not minutes

write_log = logging.getLogger("crm.writes")
write_log.setLevel(logging.INFO)


def _open_write_log() -> None:
    if not write_log.handlers:
        WRITES_LOG.parent.mkdir(exist_ok=True)
        handler = logging.FileHandler(WRITES_LOG)
        handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
        write_log.addHandler(handler)


# --- sessions: a signed cookie holding the username, login version and session id ---
# The session id must still be open in state.db, so signing out ends it on the server too.

def _sign(data: bytes) -> str:
    return hmac.new(SECRET.encode(), data, hashlib.sha256).hexdigest()


def make_cookie(username: str) -> str:
    expires = int(time.time()) + SESSION_HOURS * 3600
    body = json.dumps({"u": username, "v": staff_auth.session_version(username),
                       "s": state.new_session(username, expires), "exp": expires}).encode()
    return base64.urlsafe_b64encode(body).decode() + "." + _sign(body)


def _cookie_data(value: str | None) -> dict | None:
    try:
        encoded, sig = (value or "").rsplit(".", 1)
        body = base64.urlsafe_b64decode(encoded.encode())
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    return json.loads(body)


def read_cookie(value: str | None) -> str | None:
    """The username in a valid, unexpired, not signed-out cookie whose login hasn't been reset or changed since."""
    data = _cookie_data(value)
    if (not data or data["exp"] < time.time() or not staff_auth.is_current(data["u"], data["v"])
            or not state.session_open(data.get("s", ""), data["u"])):
        return None
    return data["u"]


def end_session(request: Request) -> None:
    data = _cookie_data(request.cookies.get(COOKIE))
    if data and data.get("s"):
        state.end_session(data["s"])


def set_session(response: Response, username: str) -> None:
    response.set_cookie(COOKIE, make_cookie(username), max_age=SESSION_HOURS * 3600,
                        httponly=True, samesite="strict", secure=os.getenv("CRM_HTTPS") == "1")


class Staff:
    def __init__(self, username: str):
        self.username = username
        self.name = staff_auth.load_staff()[username]["name"]


def current_staff(request: Request) -> Staff:
    username = read_cookie(request.cookies.get(COOKIE))
    if not username:
        raise HTTPException(401, SIGNED_OUT)
    return Staff(username)


def ready_staff(request: Request) -> Staff:
    """Signed in and past the first-login password change."""
    staff = current_staff(request)
    if staff_auth.must_change(staff.username):
        raise HTTPException(403, PASSWORD_FIRST)
    return staff


def wants_password_change(text: str) -> bool:
    t = text.lower()
    return "password" in t and any(w in t for w in ("change", "reset", "new", "update"))


# --- app ---------------------------------------------------------------------

class LoginIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    current: str | None = None
    new: str
    confirm: str


class ChatIn(BaseModel):
    message: str
    conversation_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(SECRET) < 32:
        raise RuntimeError("Set CRM_SESSION_SECRET in frontend/.env to a long random value "
                           "(python -c 'import secrets; print(secrets.token_hex(32))').")
    _open_write_log()
    yield


app = FastAPI(title="CRM Assistant (staff)", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


async def backend(fn, *args) -> dict:
    try:
        return await fn(*args)
    except api.BackendError as exc:
        if exc.refused:
            raise HTTPException(409, f"Not saved. {exc.refused}") from None
        raise HTTPException(504 if exc.timed_out else 502, CLARIFY_SLOW if exc.timed_out else CLARIFY_DOWN) from None


@app.post("/api/login")
def login(body: LoginIn, response: Response):
    username = body.username.strip().lower()
    now = time.time()
    if state.recent_failures(username, since=now - LOCK_SECONDS) >= MAX_FAILS:
        raise HTTPException(429, TOO_MANY_TRIES)
    name = staff_auth.verify(username, body.password)
    if not name:
        state.add_failure(username, now)
        raise HTTPException(401, "That username and password don't match. Please try again.")
    state.clear_failures(username)
    set_session(response, username)
    return {"name": name, "must_change": staff_auth.must_change(username)}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    end_session(request)
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    staff = current_staff(request)
    return {"name": staff.name, "must_change": staff_auth.must_change(staff.username)}


@app.post("/api/password")
def change_password(body: PasswordIn, request: Request, response: Response):
    staff = current_staff(request)
    forced = staff_auth.must_change(staff.username)
    problem = staff_auth.change_password(staff.username, None if forced else (body.current or ""),
                                         body.new, body.confirm)
    if problem:
        raise HTTPException(400, problem)
    end_session(request)
    set_session(response, staff.username)  # every other session ends; this one carries on
    write_log.info("staff=%r changed their password", staff.name)
    return {"ok": True}


@app.post("/api/chat")
async def chat(body: ChatIn, request: Request):
    staff = ready_staff(request)
    text = body.message.strip()
    if wants_password_change(text):
        # Answered here, so the password form never involves the CRM backend.
        return {"type": "change_password", "text": "Sure. Fill this in to change your password."}
    # Namespaced, so nobody can continue another person's conversation by guessing its id.
    session_id = f"{staff.username}:{body.conversation_id[:64]}"
    reply = await backend(api.chat, text, staff.name, session_id)
    update = reply.get("update")
    if reply.get("type") == "confirm_update" and update and update.get("update_id"):
        state.add_pending(update["update_id"], staff.username, update)
    return reply


@app.get("/api/at-risk")
async def at_risk(request: Request):
    staff = ready_staff(request)
    return await backend(api.at_risk, staff.name)


@app.get("/api/cooling-leads")
async def cooling_leads(request: Request):
    staff = ready_staff(request)
    return await backend(api.cooling_leads, staff.name)


async def resolve(update_id: str, request: Request, confirmed: bool) -> dict:
    staff = ready_staff(request)
    u = state.take_pending(update_id, staff.username)  # first: a double click can't save twice
    if not u:
        raise HTTPException(404, "That change has already been handled.")
    fn = api.confirm_update if confirmed else api.cancel_update
    result = await backend(fn, update_id, staff.name)
    if confirmed:
        write_log.info("staff=%r student=%r field=%r old=%r new=%r update_id=%s", staff.name,
                       u.get("student_name"), u.get("field"), u.get("old_value"), u.get("new_value"), update_id)
    return {"ok": True, "text": result.get("text") or ("Saved." if confirmed else "Cancelled. Nothing was changed.")}


@app.post("/api/updates/{update_id}/confirm")
async def confirm(update_id: str, request: Request):
    return await resolve(update_id, request, confirmed=True)


@app.post("/api/updates/{update_id}/cancel")
async def cancel(update_id: str, request: Request):
    return await resolve(update_id, request, confirmed=False)


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
def unknown_api(path: str):
    raise HTTPException(404, "Not found")


@app.get("/{path:path}")
def ui(path: str):
    """The built React app. Unknown paths get index.html, so a page reload works anywhere."""
    file = (UI_DIR / path).resolve()
    if path and file.is_file() and UI_DIR.resolve() in file.parents:
        return FileResponse(file)
    index = UI_DIR / "index.html"
    if not index.exists():
        return JSONResponse({"detail": "The UI isn't built yet. Run: cd frontend/ui && npm install && npm run build"},
                            status_code=503)
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
