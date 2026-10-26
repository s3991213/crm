"""Trains the at-risk model on past enrolments and checks it against what actually happened.

    python -m backend.train_risk                       # college_db/out/college.db (./run.sh make-data)
    python -m backend.train_risk --source other.db --today 2026-10-25

Every 4 weeks of each past or current enrolment is a snapshot: the student's attendance, last contact and payments
as they stood that day, and whether they withdrew in the 90 days after it. Deferrals are left out (the outcome is
unclear). A logistic regression learns from the snapshots; the hand-written rule score it replaces is measured on
the same snapshots, so the two can be compared:

- cross-validation grouped by student (no student is in both the training and the test part), and
- a check over time: trained only on what was known 9 months ago, tested on the snapshots since.

Writes backend/risk_model.json (the weights, read by risk_model.py) and evals/results/risk-model.md (the report).
Needs scikit-learn (requirements-dev.txt); the backend itself doesn't.
"""

import argparse
import json
import sqlite3
from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from .risk_model import MODEL_FILE, features

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "college_db" / "out" / "college.db"
REPORT = ROOT / "evals" / "results" / "risk-model.md"
STEP = timedelta(weeks=4)
HORIZON = timedelta(days=90)
RULE_THRESHOLD = 0.4
# Flag anyone with at least a 1 in 10 chance of withdrawing in the next 90 days: several times the usual rate, and a
# line staff can understand. A policy choice, not tuned to the data; the report shows what it catches.
FLAG_AT = 0.10


def _date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _rows(conn, sql: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def snapshots(conn, today: date) -> list[dict]:
    """One row per enrolment every 4 weeks: features as of that day, and whether they withdrew within 90 days."""
    weeks = defaultdict(list)
    for w in _rows(conn, "SELECT enrolment_id, week_start, scheduled_hours, attended_hours FROM attendance_weeks "
                         "ORDER BY enrolment_id, week_start"):
        weeks[w["enrolment_id"]].append((_date(w["week_start"]), w["scheduled_hours"], w["attended_hours"]))
    notes = defaultdict(list)
    for n in _rows(conn, "SELECT student_id, noted_on FROM contact_notes ORDER BY student_id, noted_on"):
        notes[n["student_id"]].append(_date(n["noted_on"]))
    fees = defaultdict(list)
    for f in _rows(conn, "SELECT e.student_id, f.due_date, f.amount, f.amount_paid, f.paid_on FROM fee_instalments f "
                         "JOIN enrolments e ON e.id = f.enrolment_id"):
        fees[f["student_id"]].append((_date(f["due_date"]), float(f["amount"]), float(f["amount_paid"]),
                                      _date(f["paid_on"]) if f["paid_on"] else None))

    def payment_status(student_id: int, on: date) -> str:
        status = "Paid"
        for due, amount, paid, paid_on in fees[student_id]:
            if due > on:
                continue
            paid = paid if paid_on and paid_on <= on else 0.0
            if paid == 0:
                return "Overdue"
            if paid < amount:
                status = "Partial"
        return status

    enrolments = _rows(conn, "SELECT id, student_id, start_date, status, status_changed_on FROM enrolments")
    left = defaultdict(list)  # a student counts as withdrawing whichever of their enrolments they left
    for e in enrolments:
        if e["status"] == "Withdrawn":
            left[e["student_id"]].append(_date(e["status_changed_on"]))

    out = []
    for e in enrolments:
        if e["status"] == "Deferred":
            continue
        start = _date(e["start_date"])
        until = _date(e["status_changed_on"]) if e["status"] in ("Withdrawn", "Completed") else today
        on = start + STEP
        while on < until and on + HORIZON <= today:
            done = [w for w in weeks[e["id"]] if w[0] + timedelta(days=7) <= on]
            seen = notes[e["student_id"]][:bisect_right(notes[e["student_id"]], on)]
            if done and seen:
                attendance = 100 * sum(w[2] for w in done) / sum(w[1] for w in done)
                out.append({
                    "student_id": e["student_id"], "on": on, "attendance": attendance,
                    "days_since_contact": (on - seen[-1]).days, "payment_status": payment_status(e["student_id"], on),
                    "withdrew": any(on < d <= on + HORIZON for d in left[e["student_id"]])})
            on += STEP
    return out


def rule_score(s: dict) -> float:
    """The hand-written score the model replaces (from backend/store.py before it), kept as the baseline."""
    score, days, att = 0.0, s["days_since_contact"], s["attendance"]
    score += 0.35 if days >= 45 else 0.2 if days >= 30 else 0
    score += {"Overdue": 0.3, "Partial": 0.15}.get(s["payment_status"], 0)
    score += 0.3 if att < 70 else 0.15 if att < 80 else 0
    return min(1.0, score)


def matrix(rows: list[dict]) -> tuple[list[str], np.ndarray]:
    xs = [features(r["attendance"], r["days_since_contact"], r["payment_status"]) for r in rows]
    names = list(xs[0])
    return names, np.array([[x[n] for n in names] for x in xs])


def fit(x: np.ndarray, y: np.ndarray) -> LogisticRegression:
    return LogisticRegression(C=1.0, max_iter=1000).fit(x, y)


def signed_features(x: np.ndarray, y: np.ndarray) -> list[int]:
    """The columns to keep: every feature should only ever raise the risk (less attendance, longer silence, unpaid
    fees). One the data says lowers it is a side effect of something else, and would read as nonsense to staff,
    so it's dropped and the rest refitted."""
    keep = list(range(x.shape[1]))
    while keep:
        weights = fit(x[:, keep], y).coef_[0]
        if (weights > 0).all():
            break
        keep = [k for k, w in zip(keep, weights) if w > 0]
    return keep


def evaluate(rows: list[dict], today: date, keep: list[int], folds: int = 5) -> dict:
    names, x = matrix(rows)
    x = x[:, keep]
    y = np.array([r["withdrew"] for r in rows], dtype=int)
    groups = np.array([r["student_id"] for r in rows])
    rule = np.array([rule_score(r) for r in rows])

    oof = np.zeros(len(rows))
    for train, test in GroupKFold(n_splits=folds).split(x, y, groups):
        oof[test] = fit(x[train], y[train]).predict_proba(x[test])[:, 1]
    threshold = FLAG_AT

    def stats(flag: np.ndarray) -> dict:
        return {"flagged": int(flag.sum()), "precision": round(float(precision_score(y, flag, zero_division=0)), 3),
                "recall": round(float(recall_score(y, flag, zero_division=0)), 3)}

    # Over time: fit on what was known 9 months ago (outcome already seen), test on the snapshots since.
    cutoff = today - timedelta(days=270)
    on = np.array([r["on"] for r in rows])
    past = np.array([d + HORIZON <= cutoff for d in on])
    later = on >= cutoff
    over_time = None
    if y[past].sum() >= 5 and len(set(y[later])) == 2:
        p_later = fit(x[past], y[past]).predict_proba(x[later])[:, 1]
        over_time = {"cutoff": cutoff.isoformat(), "train": int(past.sum()), "test": int(later.sum()),
                     "test_withdrew": int(y[later].sum()),
                     "model_auc": round(float(roc_auc_score(y[later], p_later)), 3),
                     "rule_auc": round(float(roc_auc_score(y[later], rule[later])), 3)}

    bands = []
    for lo, hi in [(0, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 0.4), (0.4, 1.01)]:
        m = (oof >= lo) & (oof < hi)
        if m.any():
            bands.append({"band": f"{lo:.0%}-{min(hi, 1):.0%}", "snapshots": int(m.sum()),
                          "predicted": round(float(oof[m].mean()), 3), "actual": round(float(y[m].mean()), 3)})

    return {
        "snapshots": len(rows), "students": len(set(groups)), "withdrew": int(y.sum()),
        "base_rate": round(float(y.mean()), 3), "threshold": threshold,
        "model_auc": round(float(roc_auc_score(y, oof)), 3), "rule_auc": round(float(roc_auc_score(y, rule)), 3),
        "model_at_threshold": stats(oof >= threshold), "rule_at_threshold": stats(rule >= RULE_THRESHOLD),
        "over_time": over_time, "calibration": bands,
    }


def train(conn, today: date) -> dict:
    rows = snapshots(conn, today)
    names, x = matrix(rows)
    y = np.array([r["withdrew"] for r in rows], dtype=int)
    keep = signed_features(x, y)
    metrics = evaluate(rows, today, keep)
    model = fit(x[:, keep], y)
    weights = dict.fromkeys(names, 0.0) | {names[k]: round(float(w), 4) for k, w in zip(keep, model.coef_[0])}
    return {"weights": weights, "intercept": round(float(model.intercept_[0]), 4), "threshold": metrics["threshold"],
            "dropped": [n for i, n in enumerate(names) if i not in keep],
            "trained": {"today": today.isoformat(), "horizon_days": HORIZON.days}, "metrics": metrics}


def report(result: dict, source: str) -> str:
    m = result["metrics"]
    lines = [
        "# At-risk model: validation", "",
        f"Trained by `python -m backend.train_risk` on `{source}` (synthetic), {result['trained']['today']}.",
        f"Question: will this student withdraw in the next {result['trained']['horizon_days']} days?", "",
        f"- {m['snapshots']} snapshots (every 4 weeks of an enrolment) from {m['students']} students; "
        f"{m['withdrew']} were followed by a withdrawal ({m['base_rate']:.1%}).",
        "- Out-of-fold results from 5-fold cross-validation grouped by student.", "",
        "| | AUC | Flagged | Precision | Recall |", "|---|---|---|---|---|",
        f"| Trained model (flag at {m['threshold']:.0%}) | {m['model_auc']} | {m['model_at_threshold']['flagged']} | "
        f"{m['model_at_threshold']['precision']:.0%} | {m['model_at_threshold']['recall']:.0%} |",
        f"| Old rule score (flag at {RULE_THRESHOLD}) | {m['rule_auc']} | {m['rule_at_threshold']['flagged']} | "
        f"{m['rule_at_threshold']['precision']:.0%} | {m['rule_at_threshold']['recall']:.0%} |", "",
    ]
    if m["over_time"]:
        t = m["over_time"]
        lines += [f"Over time: trained on the {t['train']} snapshots whose outcome was known by {t['cutoff']}, tested "
                  f"on the {t['test']} since ({t['test_withdrew']} withdrawals): model AUC {t['model_auc']}, "
                  f"rule AUC {t['rule_auc']}.", ""]
    lines += ["Calibration (out-of-fold): of the snapshots given each chance, how many withdrew.", "",
              "| Predicted chance | Snapshots | Average predicted | Actually withdrew |", "|---|---|---|---|"]
    lines += [f"| {b['band']} | {b['snapshots']} | {b['predicted']:.1%} | {b['actual']:.1%} |" for b in m["calibration"]]
    lines += ["", "Weights (log-odds per unit; features in `backend/risk_model.py`):", ""]
    lines += [f"- `{k}`: {v:+.3f}" for k, v in result["weights"].items()]
    lines += [f"- intercept: {result['intercept']:+.3f}"]
    if result["dropped"]:
        lines += [f"- dropped (the data said they lowered the risk): {', '.join(result['dropped'])}"]
    lines += ["",
              "The data is synthetic (`college_db/generate.py`), so this shows the method works and how to check it, "
              "not how well it would predict real students. Re-run it on the college's own records before trusting "
              "the numbers.", ""]
    return "\n".join(lines)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--today", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD; the data's today")
    p.add_argument("--out", type=Path, default=MODEL_FILE)
    p.add_argument("--report", type=Path, default=REPORT)
    args = p.parse_args(argv)
    if not args.source.exists():
        raise SystemExit(f"{args.source} doesn't exist. Build it with ./run.sh make-data first.")
    with sqlite3.connect(args.source) as conn:
        result = train(conn, args.today)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        source = args.source.resolve().relative_to(ROOT)
    except ValueError:
        source = args.source.name
    args.report.write_text(report(result, str(source)))
    m = result["metrics"]
    print(f"Wrote {args.out} and {args.report}")
    print(f"  {m['snapshots']} snapshots, {m['withdrew']} withdrew; AUC model {m['model_auc']} vs rule {m['rule_auc']}; "
          f"flag at {m['threshold']:.0%}")


if __name__ == "__main__":
    main()
