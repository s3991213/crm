"""Mock CRM Assistant backend.

Implements the same API contract as the real FastAPI backend (see README.md),
with keyword matching standing in for the LLM intent step. For UI development
only. Run:  uvicorn main:app --port 8000
"""

import logging
import re
import uuid
from datetime import date

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(filename="audit.log", level=logging.INFO, format="%(asctime)s  %(message)s")
audit = logging.getLogger("audit")

app = FastAPI(title="CRM Assistant (mock)")

STUDENTS = {
    1: {"name": "Priya Sharma", "status": "Active", "course": "Diploma of Business",
        "last_contact": "2026-10-15", "payment_status": "Paid", "email": "priya.sharma@example.com",
        "risk_score": 0.18, "reasons": ["Regular attendance", "Payments up to date"],
        "history": "Enrolled in February. Visa granted in March. Attends regularly; last call was about "
                   "a timetable change."},
    2: {"name": "Liam Nguyen", "status": "Active", "course": "Certificate IV in IT",
        "last_contact": "2026-08-30", "payment_status": "Overdue", "email": "liam.nguyen@example.com",
        "risk_score": 0.84, "reasons": ["No contact in 53 days", "Second instalment overdue"],
        "history": "Enrolled in July. Missed the last two check-in calls. Second instalment is 3 weeks overdue."},
    3: {"name": "Sofia Martinez", "status": "Visa pending", "course": "General English",
        "last_contact": "2026-10-02", "payment_status": "Partial", "email": "sofia.m@example.com",
        "risk_score": 0.57, "reasons": ["Attendance dropped to 62%", "Partial payment only"],
        "history": "Applied in August. Visa application lodged 2 October. Attendance has dipped this month."},
    4: {"name": "Arjun Patel", "status": "Active", "course": "Bachelor of Nursing (pathway)",
        "last_contact": "2026-09-12", "payment_status": "Paid", "email": "arjun.patel@example.com",
        "risk_score": 0.66, "reasons": ["No contact in 40 days", "Low portal engagement"],
        "history": "Started in June. Strong first term results. Has not logged into the portal for a month."},
}
FIELDS = {"status": "status", "course": "course", "payment": "payment_status",
          "payment status": "payment_status", "email": "email"}
PENDING: dict[str, dict] = {}


class ChatIn(BaseModel):
    message: str
    staff_name: str | None = None
    session_id: str | None = None


class StaffIn(BaseModel):
    staff_name: str | None = None


def card(s: dict) -> dict:
    return {k: s[k] for k in ("name", "status", "course", "last_contact", "payment_status")}


def find_student(text: str) -> tuple[int, dict] | None:
    t = text.lower()
    for sid, s in STUDENTS.items():
        first, last = s["name"].lower().split(" ", 1)
        if s["name"].lower() in t or re.search(rf"\b({first}|{last})\b", t):
            return sid, s
    return None


@app.post("/chat")
def chat(body: ChatIn, x_staff_name: str = Header("Unknown")):
    text = body.message.lower()
    match = find_student(text)

    if "at risk" in text or "at-risk" in text:
        return at_risk()

    if "lead" in text or "enquir" in text:
        return cooling_leads()

    if "policy" in text or "refund" in text:
        return {"type": "answer",
                "text": "If a student withdraws 28 days or more before the course starts, 70% of the tuition paid "
                        "is refunded. After that, tuition for the current term isn't refunded.",
                "sources": [{"policy": "Fees, Payment Plans and Refunds Policy",
                             "section": "Refunds when a student withdraws"}]}

    m = re.search(r"(?:change|update|set)\s.*?\b(status|course|payment status|payment|email)\b.*?\bto\s+(.+)$", text)
    if m:
        if not match:
            return {"type": "clarify", "text": "Which student's record should I update?"}
        sid, s = match
        field = FIELDS[m.group(1)]
        new_value = body.message[m.start(2):].strip().rstrip(".")
        update_id = uuid.uuid4().hex
        PENDING[update_id] = {"student_id": sid, "field": field, "new_value": new_value, "staged_by": x_staff_name}
        return {
            "type": "confirm_update",
            "text": "Please check this change. Nothing is saved until you click **Confirm**.",
            "student": card(s),
            "update": {"update_id": update_id, "student_id": sid, "student_name": s["name"],
                       "field": field.replace("_", " ").capitalize(), "old_value": s[field],
                       "new_value": new_value},
        }

    if "draft" in text or "email" in text:
        if not match:
            return {"type": "clarify", "text": "Who should the email be for?"}
        sid, s = match
        first = s["name"].split()[0]
        return {
            "type": "draft_email",
            "text": f"Here's a follow-up email for {s['name']}.",
            "student": card(s),
            "draft": {
                "to": s["email"],
                "subject": "Checking in on your studies",
                "body": f"Hi {first},\n\nI hope you're settling in well. I wanted to check in and see how "
                        f"things are going with your {s['course']}.\n\nIf there's anything we can help with, "
                        "just reply to this email or give us a call.\n\nKind regards,\n" + x_staff_name,
            },
        }

    if "summar" in text or "history" in text:
        if not match:
            return {"type": "clarify", "text": "Which student's history would you like a summary of?"}
        return {"type": "answer", "text": match[1]["history"], "student": card(match[1])}

    if "find" in text or "show" in text or "look up" in text or match:
        if not match:
            return {"type": "clarify", "text": "Which student are you looking for? A name is enough."}
        s = match[1]
        return {"type": "answer", "text": f"Here's {s['name']}'s record.", "student": card(s)}

    return {"type": "clarify", "text": "Sorry, I'm not sure what you need. Is this about a particular student?"}


LEADS = [
    {"name": "Ji-ho Park", "status": "Offer sent", "course": "Diploma of Business", "days_quiet": 25,
     "reason": "No reply for 25 days after 2 follow-ups"},
    {"name": "Daniel Okoro", "status": "Contacted", "course": "Certificate III in Carpentry", "days_quiet": 21,
     "reason": "No reply for 21 days after 1 follow-up"},
]


@app.get("/cooling-leads")
def cooling_leads():
    return {"type": "cooling_leads", "text": f"{len(LEADS)} enquiries have gone quiet, furthest along first.",
            "leads": LEADS}


@app.get("/at-risk")
def at_risk():
    rows = [{"name": s["name"], "risk_score": s["risk_score"], "reasons": s["reasons"]}
            for s in STUDENTS.values() if s["risk_score"] >= 0.4]
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return {"type": "at_risk", "text": f"{len(rows)} students may need attention, highest risk first.",
            "students": rows}


@app.post("/updates/{update_id}/confirm")
def confirm(update_id: str, body: StaffIn, x_staff_name: str = Header("Unknown")):
    p = PENDING.pop(update_id, None)
    if not p:
        raise HTTPException(404, "No pending change with that id")
    s = STUDENTS[p["student_id"]]
    old = s[p["field"]]
    s[p["field"]] = p["new_value"]
    s["last_contact"] = s["last_contact"] if p["field"] != "status" else date.today().isoformat()
    audit.info("WRITE staff=%r student=%r field=%s old=%r new=%r", x_staff_name, s["name"], p["field"], old, p["new_value"])
    return {"ok": True, "text": f"Saved. {s['name']}'s {p['field'].replace('_', ' ')} is now **{p['new_value']}**."}


@app.post("/updates/{update_id}/cancel")
def cancel(update_id: str, body: StaffIn, x_staff_name: str = Header("Unknown")):
    PENDING.pop(update_id, None)
    audit.info("CANCEL staff=%r update_id=%s", x_staff_name, update_id)
    return {"ok": True, "text": "Cancelled. Nothing was changed."}
