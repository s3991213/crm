"""The at-risk model: training snapshots, the trained weights, and scoring."""

import json
import sqlite3
from datetime import date

import pytest

from backend.risk_model import MODEL_FILE, RiskModel, features
from backend.train_risk import HORIZON, main, snapshots, train
from college_db.generate import Generator, to_sql, write_sqlite

TODAY = date(2026, 10, 25)


@pytest.fixture(scope="module")
def college(tmp_path_factory):
    path = tmp_path_factory.mktemp("risk") / "college.db"
    write_sqlite(to_sql(Generator(300, seed=3, today=TODAY).run()), path)
    db = sqlite3.connect(path)
    yield db
    db.close()


def test_weekly_attendance_adds_up_to_the_enrolment_figure(college):
    rows = college.execute(
        "select e.attendance_pct, sum(w.attended_hours), sum(w.scheduled_hours) "
        "from enrolments e join attendance_weeks w on w.enrolment_id = e.id group by e.id").fetchall()
    assert rows and all(pct == round(100 * attended / scheduled) for pct, attended, scheduled in rows)


def test_snapshots_only_use_what_was_known_that_day(college):
    rows = snapshots(college, TODAY)
    left = {sid: date.fromisoformat(d) for sid, d in college.execute(
        "select student_id, status_changed_on from enrolments where status = 'Withdrawn'")}
    assert rows and any(r["withdrew"] for r in rows)
    for r in rows:
        assert r["on"] + HORIZON <= TODAY  # the outcome is known
        assert r["days_since_contact"] >= 0
        if r["student_id"] in left:
            assert r["on"] < left[r["student_id"]]  # never after they left
            assert r["withdrew"] == (left[r["student_id"]] - r["on"] <= HORIZON)  # whichever course it was
        else:
            assert not r["withdrew"]


def test_training_keeps_only_weights_that_raise_the_risk(college):
    result = train(college, TODAY)
    assert all(w >= 0 for w in result["weights"].values())
    assert set(result["weights"]) == set(features(90, 10, "Paid"))
    m = result["metrics"]
    assert m["model_auc"] > 0.7 and m["threshold"] == 0.1
    assert m["calibration"] and m["model_at_threshold"]["flagged"] > 0
    lo, hi = m["boosted_minus_model_auc_95"]  # gradient boosting is measured alongside, never shipped
    assert m["boosted_auc"] > 0.5 and lo <= hi and "boosted_auc" in m["over_time"]


def test_command_line_writes_model_and_report(college, tmp_path):
    source = tmp_path / "college.db"
    college.backup(sqlite3.connect(source))
    main(["--source", str(source), "--today", TODAY.isoformat(), "--out", str(tmp_path / "m.json"),
          "--report", str(tmp_path / "r.md")])
    model = RiskModel.load(tmp_path / "m.json")
    assert model.threshold == 0.1
    assert "| Trained model" in (tmp_path / "r.md").read_text()
    with pytest.raises(SystemExit):
        main(["--source", str(tmp_path / "missing.db")])


def test_committed_model_is_complete():
    data = json.loads(MODEL_FILE.read_text())
    assert set(data["weights"]) == set(features(90, 10, "Paid")) and 0 < data["threshold"] < 1
    model = RiskModel.load()
    worse = model.score(60, 60, "Overdue")[0]
    assert worse > model.score(95, 5, "Paid")[0]


def test_scores_rise_with_each_warning_sign():
    model = RiskModel({"attendance_shortfall": 1.0, "months_since_contact": 0.5, "payment_overdue": 0.7,
                       "payment_partial": 1.0}, intercept=-6, threshold=0.1)
    base = model.score(90, 10, "Paid")[0]
    assert model.score(70, 10, "Paid")[0] > base
    assert model.score(90, 60, "Paid")[0] > base
    assert model.score(90, 10, "Overdue")[0] > base
    p, reasons = model.score(65, 50, "Overdue")
    assert reasons[0] == "Attendance at 65%" and "No contact in 50 days" in reasons and "Payment overdue" in reasons
    assert model.score(95, 3, "Paid")[1] == []
    assert model.score(90, 400, "Paid")[0] == model.score(90, 120, "Paid")[0]  # silence counts up to 4 months
