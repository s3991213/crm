"""The at-risk model: how likely a student is to withdraw in the next 90 days, and why.

It's a logistic regression trained on past enrolments by backend/train_risk.py, which also checks it against what
actually happened. The weights are saved to risk_model.json and scored here in plain Python, so the backend doesn't
need scikit-learn and every score can be explained: each feature's share of the score is a reason staff can read.
"""

import json
import math
from pathlib import Path

MODEL_FILE = Path(__file__).parent / "risk_model.json"
# A reason is shown when its feature adds at least this much to the score (on the log-odds scale) compared with
# a student who is on track, so "Attendance at 94%" is never given as a reason.
MIN_REASON = 0.3


def features(attendance: float, days_since_contact: int, payment_status: str) -> dict[str, float]:
    """The model's inputs. Training and scoring both build them here, so they always mean the same thing."""
    return {
        "attendance_shortfall": max(0.0, 100 - attendance) / 10,  # points below 100%, in tens
        "months_since_contact": min(days_since_contact, 120) / 30,
        "payment_overdue": float(payment_status == "Overdue"),
        "payment_partial": float(payment_status == "Partial"),
    }


ON_TRACK = features(attendance=90, days_since_contact=14, payment_status="Paid")


def reason_text(name: str, attendance: float, days_since_contact: int) -> str:
    return {
        "attendance_shortfall": f"Attendance at {attendance:.0f}%",
        "months_since_contact": f"No contact in {days_since_contact} days",
        "payment_overdue": "Payment overdue",
        "payment_partial": "Only partly paid",
    }[name]


class RiskModel:
    def __init__(self, weights: dict[str, float], intercept: float, threshold: float):
        self.weights, self.intercept, self.threshold = weights, intercept, threshold

    @classmethod
    def load(cls, path: str | Path = MODEL_FILE) -> "RiskModel":
        data = json.loads(Path(path).read_text())
        return cls(data["weights"], data["intercept"], data["threshold"])

    def score(self, attendance: float, days_since_contact: int, payment_status: str) -> tuple[float, list[str]]:
        """The chance of withdrawing in the next 90 days (0-1), and the reasons behind it, biggest first."""
        x = features(attendance, days_since_contact, payment_status)
        p = 1 / (1 + math.exp(-(self.intercept + sum(self.weights[k] * v for k, v in x.items()))))
        above = {k: self.weights[k] * (v - ON_TRACK[k]) for k, v in x.items()}
        reasons = [reason_text(k, attendance, days_since_contact)
                   for k, v in sorted(above.items(), key=lambda kv: -kv[1]) if v >= MIN_REASON]
        return p, reasons
