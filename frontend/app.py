"""CRM Assistant: staff-facing chat frontend.

Kept deliberately thin. Every request goes to the FastAPI backend, and this
file only decides how to *show* what comes back.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import chainlit as cl  # noqa: E402

import api  # noqa: E402
import staff_auth  # noqa: E402

AT_RISK_PROMPT = "Show at-risk students"

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
write_log = logging.getLogger("crm.writes")
write_log.setLevel(logging.INFO)
_handler = logging.FileHandler(LOG_DIR / "writes.log")
_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
write_log.addHandler(_handler)

CLARIFY_UNCLEAR = (
    "I'm not quite sure what you'd like me to do. Could you say it another way? "
    "For example: *\"Show me Priya Sharma's record\"*."
)
CLARIFY_SLOW = "That took longer than expected. Would you like me to try again?"
CLARIFY_DOWN = (
    "I couldn't reach the student records just now. Would you like to try again in a minute? "
    "If it keeps happening, please let your manager know."
)
SIGNED_OUT = (
    "Your login has been changed or removed, so this session has ended. "
    "Please sign out (top right) and sign in again."
)


def staff_name() -> str:
    user = cl.user_session.get("user")
    return user.display_name if user else "Unknown"


def staff_username() -> str:
    user = cl.user_session.get("user")
    return user.identifier if user else ""


def session_ok() -> bool:
    """False once this login is removed or its password reset or changed elsewhere."""
    user = cl.user_session.get("user")
    return bool(user) and staff_auth.is_current(user.identifier, (user.metadata or {}).get("version"))


def wants_password_change(text: str) -> bool:
    t = text.lower()
    return "password" in t and any(w in t for w in ("change", "reset", "new", "update"))


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    name = staff_auth.verify(username, password)
    if name:
        username = username.strip().lower()
        version = staff_auth.session_version(username)
        return cl.User(identifier=username, display_name=name, metadata={"name": name, "version": version})
    return None


@cl.set_starters
async def set_starters(user=None, language=None):
    return [
        cl.Starter(label="Find a student", message="Find a student", icon="/public/icons/search.svg"),
        cl.Starter(
            label="Summarise a student's history",
            message="Summarise a student's history",
            icon="/public/icons/history.svg",
        ),
        cl.Starter(label=AT_RISK_PROMPT, message=AT_RISK_PROMPT, icon="/public/icons/alert.svg"),
        cl.Starter(
            label="Draft a follow-up email",
            message="Draft a follow-up email",
            icon="/public/icons/mail.svg",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    if not session_ok():
        await ask(SIGNED_OUT)
        return
    if staff_auth.must_change(staff_username()):
        await show_password_form(forced=True)


async def show_password_form(forced: bool, text: str | None = None) -> None:
    form = cl.CustomElement(name="ChangePassword", props={"forced": forced}, display="inline")
    if text:
        pass
    elif forced:
        text = (
            f"Welcome, {staff_name()}! Before you start, please choose your own password. "
            "You'll use it from now on instead of the temporary one."
        )
    else:
        text = "Sure. Fill this in to change your password."
    await cl.Message(content=text, elements=[form]).send()


@cl.action_callback("change_password")
async def on_change_password(action: cl.Action):
    # Called straight from the ChangePassword form, so the password never appears in the chat
    # and is never sent to the CRM backend.
    if not session_ok():
        return {"ok": False, "error": SIGNED_OUT}
    username = staff_username()
    forced = staff_auth.must_change(username)
    p = action.payload or {}
    problem = staff_auth.change_password(
        username,
        None if forced else p.get("current", ""),
        p.get("new", ""),
        p.get("confirm", ""),
    )
    if problem:
        return {"ok": False, "error": problem}
    # Changing the password ends every other session; keep this one going.
    cl.user_session.get("user").metadata["version"] = staff_auth.session_version(username)
    write_log.info("staff=%r changed their password", staff_name())
    if forced:
        await ask(
            "All set. How can I help? Try something like *\"Find Liam Nguyen\"* or *\"Show at-risk students\"*."
        )
    return {"ok": True}


async def ask(message: str) -> None:
    await cl.Message(content=message).send()


async def call_backend(fn, *args) -> dict | None:
    """Run a backend call behind a short status line. Returns None on failure."""
    status = await cl.Message(content="Working on it…").send()
    try:
        return await fn(*args)
    except api.BackendError as exc:
        await ask(CLARIFY_SLOW if exc.timed_out else CLARIFY_DOWN)
        return None
    finally:
        await status.remove()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if not text:
        return

    if not session_ok():
        await ask(SIGNED_OUT)
        return

    if staff_auth.must_change(staff_username()):
        await show_password_form(forced=True, text="Please choose your new password first. It only takes a moment.")
        return

    if wants_password_change(text):
        await show_password_form(forced=False)
        return

    if text.lower() == AT_RISK_PROMPT.lower():
        data = await call_backend(api.at_risk, staff_name())
        if data is not None:
            await show_at_risk(data)
        return

    data = await call_backend(api.chat, text, staff_name(), cl.context.session.thread_id)
    if data is not None:
        await render(data)


async def render(data: dict) -> None:
    kind = data.get("type")
    text = (data.get("text") or "").strip()

    if data.get("student"):
        await show_student_card(data["student"])

    if kind == "confirm_update" and data.get("update"):
        await show_confirmation(data["update"], text)
    elif kind == "at_risk":
        await show_at_risk(data)
    elif kind == "draft_email" and data.get("draft"):
        await show_draft(data["draft"], text)
    elif kind in ("answer", "clarify") and text:
        await ask(text)
    else:
        await ask(text or CLARIFY_UNCLEAR)


async def show_student_card(student: dict) -> None:
    card = cl.CustomElement(name="StudentCard", props=student, display="inline")
    await cl.Message(content="", elements=[card]).send()


async def show_at_risk(data: dict) -> None:
    students = sorted(data.get("students") or [], key=lambda s: s.get("risk_score", 0), reverse=True)
    if not students:
        await ask("Good news: no students are flagged as at risk right now.")
        return
    rows = [
        {"name": s.get("name", ""), "risk_score": s.get("risk_score", 0), "reasons": (s.get("reasons") or [])[:2]}
        for s in students
    ]
    table = cl.CustomElement(name="AtRiskTable", props={"students": rows}, display="inline")
    intro = data.get("text") or f"{len(rows)} students may need attention, highest risk first."
    await cl.Message(content=intro, elements=[table]).send()


async def show_draft(draft: dict, text: str) -> None:
    element = cl.CustomElement(
        name="EmailDraft",
        props={"to": draft.get("to", ""), "subject": draft.get("subject", ""), "body": draft.get("body", "")},
        display="inline",
    )
    note = text or "Here's a draft. Edit anything you like, then copy it into your email."
    await cl.Message(content=f"{note}\n\n*Nothing has been sent.*", elements=[element]).send()


async def show_confirmation(update: dict, text: str) -> None:
    card = cl.CustomElement(
        name="ConfirmCard",
        props={
            "student_name": update.get("student_name", ""),
            "field": update.get("field", ""),
            "old_value": update.get("old_value", ""),
            "new_value": update.get("new_value", ""),
            "status": "pending",
        },
        display="inline",
    )
    payload = {"update_id": update["update_id"]}
    actions = [
        cl.Action(name="confirm_update", payload=payload, label="Confirm", icon="check"),
        cl.Action(name="cancel_update", payload=payload, label="Cancel", icon="x"),
    ]
    msg = cl.Message(
        content=text or "Please check this change. Nothing is saved until you click **Confirm**.",
        elements=[card],
        actions=actions,
    )
    await msg.send()
    pending = cl.user_session.get("pending_updates") or {}
    pending[update["update_id"]] = {"message": msg, "card": card, "update": update}
    cl.user_session.set("pending_updates", pending)


async def resolve_update(action: cl.Action, confirmed: bool) -> None:
    if not session_ok():
        await ask(SIGNED_OUT)
        return
    update_id = action.payload.get("update_id")
    pending = cl.user_session.get("pending_updates") or {}
    entry = pending.pop(update_id, None)
    cl.user_session.set("pending_updates", pending)
    if not entry:
        await ask("That change has already been handled.")
        return

    # Remove the buttons first so a second click can't save twice.
    await entry["message"].remove_actions()
    card, update = entry["card"], entry["update"]

    try:
        fn = api.confirm_update if confirmed else api.cancel_update
        result = await fn(update_id, staff_name())
    except api.BackendError:
        card.props["status"] = "failed"
        await card.update()
        await ask(
            "I couldn't save that change, so the record has **not** been updated. "
            "Would you like to ask for the change again?"
        )
        return

    if confirmed:
        write_log.info(
            "staff=%r student=%r field=%r old=%r new=%r update_id=%s",
            staff_name(), update.get("student_name"), update.get("field"),
            update.get("old_value"), update.get("new_value"), update_id,
        )
    card.props["status"] = "saved" if confirmed else "cancelled"
    await card.update()
    default = "Saved." if confirmed else "Cancelled. Nothing was changed."
    await ask(result.get("text") or default)


@cl.action_callback("confirm_update")
async def on_confirm(action: cl.Action):
    await resolve_update(action, confirmed=True)


@cl.action_callback("cancel_update")
async def on_cancel(action: cl.Action):
    await resolve_update(action, confirmed=False)
