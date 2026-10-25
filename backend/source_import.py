"""Copies students from the college's student database into the assistant's crm.db.

The source is the college's own system (MySQL in the office). The tables expected are those in
college_db/schema.sql; college_db/generate.py makes a synthetic copy. Each student becomes one row
with the fields the assistant works with:

- course, status, attendance: from their latest enrolment
- payment_status: Overdue when an instalment that is due has had nothing paid, Partial when one is
  part-paid, otherwise Paid (everything due so far is paid; later instalments may be outstanding)
- last_contact: the newest contact note
- history: every contact note, oldest first, one dated line each

Only reads the source, with plain SELECTs on any DB-API connection (sqlite3 here, PyMySQL for MySQL).
"""

from datetime import date


def _rows(conn, sql: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))  # MySQL gives dates, SQLite text


def student_rows(conn, today: date) -> list[dict]:
    courses = {c["id"]: c["name"] for c in _rows(conn, "SELECT id, name FROM courses")}
    latest = {}
    for e in _rows(conn, "SELECT id, student_id, course_id, start_date, status, attendance_pct FROM enrolments "
                         "ORDER BY student_id, start_date, id"):
        latest[e["student_id"]] = e
    owing = {}
    for f in _rows(conn, "SELECT e.student_id, f.due_date, f.amount, f.amount_paid FROM fee_instalments f "
                         "JOIN enrolments e ON e.id = f.enrolment_id"):
        paid, amount = float(f["amount_paid"]), float(f["amount"])
        if _date(f["due_date"]) <= today and paid < amount and owing.get(f["student_id"]) != "Overdue":
            owing[f["student_id"]] = "Overdue" if paid == 0 else "Partial"
    notes: dict[int, list[dict]] = {}
    for n in _rows(conn, "SELECT student_id, noted_on, note FROM contact_notes ORDER BY student_id, noted_on, id"):
        notes.setdefault(n["student_id"], []).append(n)

    rows = []
    for s in _rows(conn, "SELECT id, given_name, family_name, email FROM students ORDER BY id"):
        e = latest.get(s["id"])
        if not e:
            continue  # an enquiry that never enrolled
        ns = notes.get(s["id"], [])
        rows.append({
            "id": s["id"], "name": f"{s['given_name']} {s['family_name']}", "status": e["status"],
            "course": courses[e["course_id"]], "email": s["email"], "payment_status": owing.get(s["id"], "Paid"),
            "attendance": int(e["attendance_pct"]),
            "last_contact": (_date(ns[-1]["noted_on"]) if ns else min(_date(e["start_date"]), today)).isoformat(),
            "history": "\n".join(f"{_date(n['noted_on']).isoformat()}: {n['note']}" for n in ns),
        })
    return rows


def import_students(conn, store, today: date | None = None) -> int:
    """Load the source's students into an empty crm.db. Returns how many were loaded."""
    return store.load_students(student_rows(conn, today or date.today()))
