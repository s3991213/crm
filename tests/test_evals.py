"""The eval cases and checker stay valid (no model needed)."""

from pathlib import Path

import yaml

from evals.run import check

CASES = yaml.safe_load((Path(__file__).parent.parent / "evals" / "cases.yaml").read_text())
KEYS = {"type", "student", "tools", "not_tools", "update", "draft_to", "draft_to_not", "update_count_max", "text_has"}


def test_cases_are_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert c["message"] and c["category"]
        assert set(c["expect"]) <= KEYS, c["id"]


def test_check_catches_writes_and_wrong_update():
    reply = {"type": "confirm_update", "text": "",
             "update": {"student_name": "Liam Nguyen", "field": "Status", "new_value": "Deferred"}}
    want = {"type": "confirm_update", "update": {"student": "Liam Nguyen", "field": "Status", "new_value": "Withdrawn"}}
    assert check(want, reply, [], 1, wrote=False) == [
        "staged {'student': 'Liam Nguyen', 'field': 'Status', 'new_value': 'Deferred'}, expected "
        "{'student': 'Liam Nguyen', 'field': 'Status', 'new_value': 'Withdrawn'}"]
    assert "a student record was written" in check({}, {"type": "answer", "text": ""}, [], 0, wrote=True)


def test_check_passes_matching_reply():
    reply = {"type": "answer", "text": "He is in Hospitality.", "student": {"name": "Omar Haddad"}}
    want = {"type": "answer", "student": "Omar Haddad", "text_has": ["hospitality"], "update": None}
    assert check(want, reply, ["find_student"], 0, wrote=False) == []
