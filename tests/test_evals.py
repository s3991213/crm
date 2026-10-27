"""The eval cases and checker stay valid (no model needed)."""

import asyncio
from pathlib import Path

import yaml

from evals.run import check, gate, judge

CASES = yaml.safe_load((Path(__file__).parent.parent / "evals" / "cases.yaml").read_text())
KEYS = {"type", "student", "tools", "not_tools", "update", "draft_to", "draft_to_not", "update_count_max", "text_has",
        "no_saved_claim", "text_lacks", "sources"}


def test_cases_are_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert c["message"] and c["category"]
        assert set(c["expect"]) <= KEYS, c["id"]
        assert set(c) <= {"id", "category", "message", "before", "expect", "judge"}, c["id"]


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


def test_gate_fails_on_any_safety_failure_or_write():
    ok = [{"id": f"c{i}", "category": "lookup", "pass": True, "fails": []} for i in range(30)]
    assert gate(ok) == []
    unsafe = ok + [{"id": "inject", "category": "safety", "pass": False, "fails": ["update staged"]}]
    assert gate(unsafe) == ["safety or update cases failed: inject"]
    wrote = ok + [{"id": "w", "category": "lookup", "pass": False, "fails": ["a student record was written"]}]
    assert gate(wrote) == ["1 records written"]
    assert "pass rate" in gate(ok + [{"id": f"x{i}", "category": "lookup", "pass": False, "fails": []} for i in range(3)])[0]


def test_judge_reads_a_json_verdict():
    class Msg:
        def __init__(self, content):
            self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]

    class FakeJudge:
        model = "fake"
        extra = {}

        def __init__(self, content):
            self.content = content
            self.client = self
            self.chat = self
            self.completions = self

        async def create(self, **kwargs):
            self.prompt = kwargs["messages"][0]["content"]
            return Msg(self.content)

    case = {"message": "summarise Sofia", "judge": "Mentions the visa."}
    reply = {"text": "Her visa was lodged.", "draft": {"to": "a@b", "subject": "Hi", "body": "Hello"}}
    passing = FakeJudge('<think>hm</think>{"pass": true, "reason": "ok"}')
    assert asyncio.run(judge(passing, case, reply, no_think=True)) is None
    assert "Subject: Hi" in passing.prompt and "Mentions the visa." in passing.prompt
    assert asyncio.run(judge(FakeJudge('{"pass": false, "reason": "invents a date"}'), case, reply, False)) \
        == "judge: invents a date"
    assert asyncio.run(judge(FakeJudge("no idea"), case, reply, False)).startswith("judge gave no verdict")
    assert asyncio.run(judge(FakeJudge('{"pass": false, "reason": "omits the "second instalment""}'), case, reply,
                             False)) == 'judge: omits the "second instalment'

