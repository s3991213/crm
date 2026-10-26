"""Student records in SQLite. The only module that reads or writes the database.

Nothing here is called by the model directly: the agent's tools go through
these methods, and only `confirm()` changes a student record.
"""

import difflib
import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from .risk_model import RiskModel

STATUSES = ["Active", "Visa pending", "Deferred", "Withdrawn", "Completed"]
PAYMENT_STATUSES = ["Paid", "Partial", "Overdue"]

# Fields staff may change, and the values each accepts (None means free text).
EDITABLE = {"status": STATUSES, "payment_status": PAYMENT_STATUSES, "course": None, "email": None}
FIELD_LABELS = {"status": "Status", "payment_status": "Payment status", "course": "Course", "email": "Email"}
# A proposed change can be confirmed for this long; after that staff ask again, so a forgotten card can't be clicked.
PENDING_TTL = timedelta(minutes=60)
# Chat memory is kept this long after the last message, so a restart doesn't make the assistant forget.
CONVERSATION_TTL = timedelta(days=1)

SCHEMA = """
create table if not exists students (
    id integer primary key, name text not null, status text, course text, email text,
    payment_status text, attendance integer, last_contact text, history text
);
create table if not exists pending_updates (
    id text primary key, student_id integer not null, field text not null,
    old_value text, new_value text, staged_by text, staged_at text
);
create table if not exists audit (
    id integer primary key autoincrement, at text, staff text, action text,
    student_id integer, field text, old_value text, new_value text
);
create table if not exists conversations (
    session_id text primary key, messages text not null, updated_at text not null
);
"""


class StoreError(Exception):
    """A request the store refuses, with a message that can be shown to staff."""


class Store:
    def __init__(self, path: str | Path = ":memory:", today=date.today, now=datetime.now,
                 risk_model: RiskModel | None = None):
        self.today, self.now = today, now
        self.risk_model = risk_model or RiskModel.load()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # --- setup -------------------------------------------------------------

    def seed_if_empty(self, seed_file: str | Path) -> None:
        if self.db.execute("select count(*) from students").fetchone()[0]:
            return
        self.load_students([
            {**s, "last_contact": (self.today() - timedelta(days=s["last_contact_days_ago"])).isoformat()}
            for s in json.loads(Path(seed_file).read_text())])

    def load_students(self, rows: list[dict]) -> int:
        """Fill an empty students table, from the seed file or an import. Never touches existing records."""
        if self.db.execute("select count(*) from students").fetchone()[0]:
            raise StoreError("The students table already has records, so nothing was loaded.")
        self.db.executemany(
            "insert into students (id, name, status, course, email, payment_status, attendance, last_contact, history)"
            " values (:id, :name, :status, :course, :email, :payment_status, :attendance, :last_contact, :history)",
            [{"id": None, **r} for r in rows])
        self.db.commit()
        return len(rows)

    # --- reads -------------------------------------------------------------

    def get(self, student_id: int) -> dict:
        return dict(self.db.execute("select * from students where id = ?", (student_id,)).fetchone())

    def find(self, name: str) -> list[dict]:
        """Students whose full name contains `name`, or whose first or last name equals a word in it."""
        words = [w[:-2] if w.endswith(("'s", "’s")) else w for w in name.lower().split()]
        query = " ".join(words)
        words = set(words)
        rows = [dict(r) for r in self.db.execute("select * from students order by id")]
        exact = [r for r in rows if r["name"].lower() == query]
        if exact:
            return exact
        return [r for r in rows if query in r["name"].lower() or words & set(r["name"].lower().split())]

    def suggest(self, name: str, limit: int = 3) -> list[str]:
        """Names close to a misspelt `name`, best first. Only ever offered as a question, never used."""
        words = [w[:-2] if w.endswith(("'s", "’s")) else w for w in name.lower().split()]
        query = " ".join(words)
        scored = []
        for r in self.all_students():
            full = r["name"].lower()
            parts = [full, *full.split()]
            score = max(difflib.SequenceMatcher(None, w, part).ratio() for w in [query, *words] for part in parts)
            if score >= 0.75:
                scored.append((score, r["name"]))
        return [n for _, n in sorted(scored, key=lambda t: -t[0])[:limit]]

    def all_students(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("select * from students order by id")]

    @staticmethod
    def card(s: dict) -> dict:
        return {k: s[k] for k in ("name", "status", "course", "last_contact", "payment_status")}

    def risk(self, s: dict) -> tuple[float, list[str]]:
        """The chance (0-1) that a current student withdraws in the next 90 days, and why, biggest reason first."""
        if s["status"] in ("Withdrawn", "Completed", "Deferred"):
            return 0.0, []
        days = (self.today() - date.fromisoformat(s["last_contact"])).days
        return self.risk_model.score(s["attendance"], days, s["payment_status"])

    def at_risk(self) -> list[dict]:
        """Current students at or above the model's flag line, highest chance first."""
        rows = []
        for s in self.all_students():
            score, reasons = self.risk(s)
            if score >= self.risk_model.threshold:
                rows.append({"name": s["name"], "risk_score": round(score, 2), "reasons": reasons[:2]})
        return sorted(rows, key=lambda r: r["risk_score"], reverse=True)

    # --- staged changes ----------------------------------------------------

    def stage(self, student_id: int, field: str, new_value: str, staff: str) -> dict:
        """Record a proposed change. The student record is not touched."""
        if field not in EDITABLE:
            raise StoreError(f"'{field}' can't be changed here. Allowed fields: {', '.join(EDITABLE)}.")
        new_value = new_value.strip()
        allowed = EDITABLE[field]
        if allowed is not None:
            match = next((v for v in allowed if v.lower() == new_value.lower()), None)
            if match is None:
                raise StoreError(f"'{new_value}' isn't a valid {FIELD_LABELS[field].lower()}. "
                                 f"Choose one of: {', '.join(allowed)}.")
            new_value = match
        if not new_value:
            raise StoreError("The new value is empty.")
        if field == "email" and ("@" not in new_value or " " in new_value):
            raise StoreError(f"'{new_value}' doesn't look like an email address.")
        s = self.get(student_id)
        if s[field] == new_value:
            raise StoreError(f"{s['name']}'s {FIELD_LABELS[field].lower()} is already {new_value}.")
        update_id = uuid.uuid4().hex
        self.db.execute(
            "insert into pending_updates values (?, ?, ?, ?, ?, ?, ?)",
            (update_id, student_id, field, s[field], new_value, staff, self.now().isoformat(timespec="seconds")),
        )
        self._audit(staff, "staged", student_id, field, s[field], new_value)
        self.db.commit()
        return {"update_id": update_id, "student_id": student_id, "student_name": s["name"],
                "field": FIELD_LABELS[field], "old_value": s[field], "new_value": new_value}

    def confirm(self, update_id: str, staff: str) -> dict:
        """Apply a staged change. The only method that writes to a student record."""
        p = self._take_pending(update_id)
        s = self.get(p["student_id"])
        if self.now() - datetime.fromisoformat(p["staged_at"]) > PENDING_TTL:
            self._audit(staff, "expired", s["id"], p["field"], p["old_value"], p["new_value"])
            self.db.commit()
            raise StoreError(f"This change was proposed more than {PENDING_TTL.seconds // 60} minutes ago, "
                             "so nothing was saved. Please ask for it again.")
        if s[p["field"]] != p["old_value"]:
            self._audit(staff, "conflict", s["id"], p["field"], s[p["field"]], p["new_value"])
            self.db.commit()
            raise StoreError(f"{s['name']}'s record changed after this was staged, so nothing was saved. "
                             "Please ask for the change again.")
        self.db.execute(f"update students set {p['field']} = ? where id = ?", (p["new_value"], s["id"]))
        self._audit(staff, "confirmed", s["id"], p["field"], p["old_value"], p["new_value"])
        self.db.commit()
        return {"student_name": s["name"], "field": FIELD_LABELS[p["field"]], "new_value": p["new_value"]}

    def cancel(self, update_id: str, staff: str) -> None:
        p = self._take_pending(update_id)
        self._audit(staff, "cancelled", p["student_id"], p["field"], p["old_value"], p["new_value"])
        self.db.commit()

    def _take_pending(self, update_id: str) -> dict:
        row = self.db.execute("select * from pending_updates where id = ?", (update_id,)).fetchone()
        if not row:
            raise KeyError(update_id)
        self.db.execute("delete from pending_updates where id = ?", (update_id,))
        return dict(row)

    def _audit(self, staff, action, student_id, field, old, new) -> None:
        self.db.execute(
            "insert into audit (at, staff, action, student_id, field, old_value, new_value) values (?, ?, ?, ?, ?, ?, ?)",
            (self.now().isoformat(timespec="seconds"), staff, action, student_id, field, old, new),
        )

    # --- chat memory (not student records) --------------------------------

    def conversation(self, session_id: str) -> list[dict]:
        row = self.db.execute("select messages from conversations where session_id = ?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else []

    def save_conversation(self, session_id: str, messages: list[dict]) -> None:
        now = self.now()
        self.db.execute("delete from conversations where updated_at < ?",
                        ((now - CONVERSATION_TTL).isoformat(timespec="seconds"),))
        self.db.execute("insert or replace into conversations values (?, ?, ?)",
                        (session_id, json.dumps(messages), now.isoformat(timespec="seconds")))
        self.db.commit()

    def audit_log(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("select * from audit order by id")]
