# At-risk model: validation

Trained by `python -m backend.train_risk` on `college_db/out/college.db` (synthetic), 2026-10-26.
Question: will this student withdraw in the next 90 days?

- 3807 snapshots (every 4 weeks of an enrolment) from 445 students; 103 were followed by a withdrawal (2.7%).
- Out-of-fold results from 5-fold cross-validation grouped by student.

| | AUC | Flagged | Precision | Recall |
|---|---|---|---|---|
| Trained model (flag at 10%) | 0.886 | 204 | 26% | 52% |
| Old rule score (flag at 0.4) | 0.838 | 161 | 26% | 40% |

Over time: trained on the 1610 snapshots whose outcome was known by 2026-01-29, tested on the 1649 since (46 withdrawals): model AUC 0.878, rule AUC 0.831.

Calibration (out-of-fold): of the snapshots given each chance, how many withdrew.

| Predicted chance | Snapshots | Average predicted | Actually withdrew |
|---|---|---|---|
| 0%-5% | 3418 | 1.0% | 1.1% |
| 5%-10% | 185 | 7.3% | 7.6% |
| 10%-20% | 128 | 14.0% | 11.7% |
| 20%-40% | 23 | 27.0% | 43.5% |
| 40%-100% | 53 | 61.3% | 52.8% |

Weights (log-odds per unit; features in `backend/risk_model.py`):

- `attendance_shortfall`: +1.397
- `months_since_contact`: +0.544
- `payment_overdue`: +0.629
- `payment_partial`: +1.258
- intercept: -7.294

The data is synthetic (`college_db/generate.py`), so this shows the method works and how to check it, not how well it would predict real students. Re-run it on the college's own records before trusting the numbers.
