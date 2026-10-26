"""The LLM backend with a scripted fake model: tool routing, safety rules, and the API contract."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as backend_app
from backend.agent import CONFIRM_TEXT, NOT_IN_POLICY_TEXT, NOT_STAGED_TEXT, NOTHING_SAVED_TEXT
from backend.llm import Completion, LLMError, ToolCall, strip_thinking
from backend.risk_model import RiskModel
from backend.store import Store, StoreError

SEED = Path(backend_app.__file__).parent / "seed.json"
STAFF = {"X-Staff-Name": "Test Staff"}
CARD_KEYS = {"name", "status", "course", "last_contact", "payment_status"}
# Fixed weights, so retraining backend/risk_model.json doesn't change these tests.
RISK = RiskModel({"attendance_shortfall": 1.48, "months_since_contact": 0.53, "payment_overdue": 0.67,
                  "payment_partial": 1.27}, intercept=-7.61, threshold=0.1)


def call(_tool, **args):
    return ToolCall(id=f"call_{_tool}", name=_tool, arguments=json.dumps(args))


class FakeLLM:
    """Replays a script: each entry is a list of tool calls, or a final text reply."""

    model = "fake"

    def __init__(self, *script):
        self.script = list(script)
        self.seen = []

    async def complete(self, messages, tools):
        self.seen.append(list(messages))
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            return Completion(content=step, ms=5, prompt_tokens=100, completion_tokens=10)
        return Completion(content="", tool_calls=step, ms=5, prompt_tokens=100, completion_tokens=10)


@pytest.fixture
def store():
    s = Store(":memory:", today=lambda: date(2026, 10, 25), risk_model=RISK)
    s.seed_if_empty(SEED)
    return s


@pytest.fixture
def traces(tmp_path, monkeypatch):
    path = tmp_path / "traces.jsonl"
    monkeypatch.setattr(backend_app, "TRACE_FILE", path)
    return path


def client_for(store, *script):
    llm = FakeLLM(*script)
    return TestClient(backend_app.create_app(store, llm)), llm


def chat(client, message, session="s1"):
    r = client.post("/chat", json={"message": message, "session_id": session}, headers=STAFF)
    assert r.status_code == 200, r.text
    return r.json()


def snapshot(store):
    return json.dumps(store.all_students(), sort_keys=True)


# --- store -----------------------------------------------------------------

def test_find_handles_partial_possessive_and_ambiguous(store):
    assert [s["name"] for s in store.find("liam's")] == ["Liam Nguyen"]
    assert [s["name"] for s in store.find("Grace O'Brien")] == ["Grace O'Brien"]
    assert {s["name"] for s in store.find("Priya")} == {"Priya Sharma", "Priya Kapoor"}
    assert [s["name"] for s in store.find("priya sharma")] == ["Priya Sharma"]
    assert store.find("Zoe Williams") == []


def test_risk_scores_are_explained(store):
    rows = store.at_risk()
    assert [r["name"] for r in rows] == ["Sofia Martinez", "Priya Kapoor", "Liam Nguyen"]
    assert rows[0] == {"name": "Sofia Martinez", "risk_score": 0.42, "reasons": ["Attendance at 62%", "Only partly paid"]}
    assert rows[2]["reasons"] == ["Attendance at 71%", "No contact in 53 days"]
    assert all(len(r["reasons"]) <= 2 for r in rows)


def test_on_track_students_get_no_reasons(store):
    mei = store.find("Mei Chen")[0]
    score, reasons = store.risk(mei)
    assert score < 0.01 and reasons == []


def test_inactive_students_are_never_at_risk(store):
    tom = store.find("Tom Becker")[0]
    assert store.risk(tom) == (0.0, [])


def test_stage_validates(store):
    liam = store.find("Liam")[0]["id"]
    with pytest.raises(StoreError, match="valid status"):
        store.stage(liam, "status", "Banana", "x")
    with pytest.raises(StoreError, match="can't be changed"):
        store.stage(liam, "name", "Bob", "x")
    with pytest.raises(StoreError, match="already Active"):
        store.stage(liam, "status", "active", "x")
    with pytest.raises(StoreError, match="email"):
        store.stage(liam, "email", "not an email", "x")
    assert store.stage(liam, "status", "withdrawn", "x")["new_value"] == "Withdrawn"


def test_confirm_refuses_if_record_changed_since_staging(store):
    liam = store.find("Liam")[0]["id"]
    first = store.stage(liam, "status", "Withdrawn", "a")
    second = store.stage(liam, "status", "Deferred", "b")
    store.confirm(first["update_id"], "a")
    with pytest.raises(StoreError, match="changed after"):
        store.confirm(second["update_id"], "b")
    assert store.get(liam)["status"] == "Withdrawn"
    assert [a["action"] for a in store.audit_log()] == ["staged", "staged", "confirmed", "conflict"]


def test_confirm_refuses_an_old_proposal(store):
    clock = [datetime(2026, 10, 25, 9, 0)]
    store.now = lambda: clock[0]
    liam = store.find("Liam")[0]["id"]
    old = store.stage(liam, "status", "Withdrawn", "a")
    fresh = store.stage(liam, "status", "Deferred", "a")
    clock[0] += timedelta(minutes=61)
    with pytest.raises(StoreError, match="more than 60 minutes"):
        store.confirm(old["update_id"], "a")
    assert store.get(liam)["status"] == "Active"
    clock[0] = datetime(2026, 10, 25, 9, 59)
    store.confirm(fresh["update_id"], "a")
    assert [a["action"] for a in store.audit_log()][-2:] == ["expired", "confirmed"]


# --- agent via /chat ---------------------------------------------------------

def test_find_returns_card(store, traces):
    client, _ = client_for(store, [call("find_student", name="Liam")], "Here's Liam's record.")
    data = chat(client, "find Liam")
    assert data["type"] == "answer"
    assert set(data["student"]) == CARD_KEYS
    assert data["student"]["name"] == "Liam Nguyen"


def test_stage_update_never_writes(store, traces):
    before = snapshot(store)
    client, _ = client_for(store, [call("stage_update", name="Arjun Patel", field="status", new_value="Withdrawn")],
                           "Done! I've saved Arjun as Withdrawn.")
    data = chat(client, "change Arjun's status to Withdrawn")
    assert data["type"] == "confirm_update"
    assert data["text"] == CONFIRM_TEXT  # the model's false "saved" claim is not shown
    assert data["update"]["old_value"] == "Active" and data["update"]["new_value"] == "Withdrawn"
    assert snapshot(store) == before


def test_confirm_then_cancel_flow(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Arjun Patel", field="status", new_value="Withdrawn")], "")
    update = chat(client, "change Arjun's status to Withdrawn")["update"]
    r = client.post(f"/updates/{update['update_id']}/confirm", json={}, headers=STAFF)
    assert r.status_code == 200 and "Withdrawn" in r.json()["text"]
    assert store.find("Arjun")[0]["status"] == "Withdrawn"
    assert client.post(f"/updates/{update['update_id']}/confirm", json={}, headers=STAFF).status_code == 404
    assert store.audit_log()[-1]["staff"] == "Test Staff"


def test_cancel_discards(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Liam", field="payment_status", new_value="Paid")], "")
    update = chat(client, "mark Liam as paid")["update"]
    assert client.post(f"/updates/{update['update_id']}/cancel", json={}, headers=STAFF).json()["ok"]
    assert store.find("Liam")[0]["payment_status"] == "Overdue"
    assert client.post(f"/updates/{update['update_id']}/confirm", json={}, headers=STAFF).status_code == 404


def test_conflict_is_409(store, traces):
    client, _ = client_for(store,
                           [call("stage_update", name="Liam", field="status", new_value="Withdrawn")], "",
                           [call("stage_update", name="Liam", field="status", new_value="Deferred")], "")
    a = chat(client, "withdraw Liam")["update"]["update_id"]
    b = chat(client, "defer Liam")["update"]["update_id"]
    client.post(f"/updates/{a}/confirm", json={}, headers=STAFF)
    r = client.post(f"/updates/{b}/confirm", json={}, headers=STAFF)
    assert r.status_code == 409


def test_only_one_change_per_request(store, traces):
    client, _ = client_for(store, [
        call("stage_update", name="Liam", field="status", new_value="Withdrawn"),
        call("stage_update", name="Sofia", field="status", new_value="Withdrawn"),
    ], "")
    data = chat(client, "withdraw Liam and Sofia")
    assert data["type"] == "clarify" and "update" not in data
    assert store.db.execute("select count(*) from pending_updates").fetchone()[0] == 0
    assert [a["action"] for a in store.audit_log()] == ["staged", "cancelled"]


def test_invented_email_is_refused(store, traces):
    client, llm = client_for(store, [call("stage_update", name="Omar", field="email", new_value="omar.smith@college.edu")],
                             "What should Omar's new email address be?")
    data = chat(client, "rename Omar to Omar Smith")
    assert data["type"] == "clarify" and "update" not in data
    assert "make up" in json.loads(llm.seen[1][-1]["content"])["error"]


def test_typed_email_is_staged_even_from_an_earlier_turn(store, traces):
    client, _ = client_for(store, "Which student is that for?",
                           [call("stage_update", name="Mei", field="email", new_value="Mei@Chen.net")], "")
    chat(client, "the new email is mei@chen.net")
    assert chat(client, "it's for Mei Chen")["update"]["new_value"] == "Mei@Chen.net"


def test_change_needs_a_student_staff_clearly_named(store, traces):
    # Seen in the browser: after the at-risk list, "Priya" was taken to mean Priya Kapoor.
    client, llm = client_for(store, [call("stage_update", name="Priya Kapoor", field="status", new_value="Deferred")],
                             "Which Priya do you mean?",
                             [call("stage_update", name="Priya Kapoor", field="status", new_value="Deferred")], "")
    data = chat(client, "change Priya's status to Deferred")
    assert data["type"] == "clarify" and "update" not in data
    assert "full name" in json.loads(llm.seen[1][-1]["content"])["error"]
    assert chat(client, "Priya Kapoor")["update"]["student_name"] == "Priya Kapoor"


def test_full_name_counts_when_each_part_is_shared(store, traces):
    # With hundreds of students, both "Liam" and "Nguyen" belong to others too.
    for name in ("Liam Kapoor", "Arjun Nguyen"):
        store.db.execute("insert into students (name, status, course, email, payment_status, attendance, last_contact,"
                         " history) values (?, 'Active', 'X', 'x@example.com', 'Paid', 90, '2026-10-20', '')", (name,))
    client, _ = client_for(store, [call("stage_update", name="Liam Nguyen", field="status", new_value="Deferred")], "",
                           [call("stage_update", name="Liam Nguyen", field="status", new_value="Deferred")], "")
    assert chat(client, "change Liam Nguyen's status to Deferred")["update"]["student_name"] == "Liam Nguyen"
    assert "update" not in chat(client, "change Liam's status to Deferred", session="s2")


def test_hyphenated_names_count_as_named(store, traces):
    for name in ("Jae-won Park", "Jae-won Cho", "Min-jun Park"):
        store.db.execute("insert into students (name, status, course, email, payment_status, attendance, last_contact,"
                         " history) values (?, 'Active', 'X', 'x@example.com', 'Paid', 90, '2026-10-20', '')", (name,))
    client, _ = client_for(store, [call("stage_update", name="Jae-won Park", field="status", new_value="Deferred")], "")
    assert chat(client, "change Jae-won Park's status to Deferred")["update"]["student_name"] == "Jae-won Park"


def test_short_words_do_not_name_a_student(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Tom Becker", field="status", new_value="Withdrawn")], "")
    assert "update" not in chat(client, "change the status to Withdrawn")


def test_typo_in_name_still_counts_as_naming(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Arjun Patel", field="status", new_value="Deferred")], "")
    assert chat(client, "change Arjun Patle's status to Deferred")["update"]["student_name"] == "Arjun Patel"


def test_claim_that_something_was_saved_is_replaced(store, traces):
    client, _ = client_for(store, "The email has been saved as a draft!", "A welcome email was sent in May.")
    assert chat(client, "yes, save it")["text"] == NOTHING_SAVED_TEXT
    assert chat(client, "any emails lately?")["text"] == "A welcome email was sent in May."


def test_answer_from_memory_gets_one_nudge_to_use_a_tool(store, traces):
    client, llm = client_for(store, "Mei Chen is doing IT and owes fees.",
                             [call("find_student", name="Mei Chen")], "Mei Chen is doing the Diploma of Marketing.")
    data = chat(client, "and what about Mei?")
    assert data["type"] == "answer" and data["student"]["name"] == "Mei Chen"
    assert "Mei Chen" in llm.seen[1][-1]["content"] and llm.seen[1][-1]["role"] == "user"


def test_answer_from_memory_twice_is_replaced(store, traces):
    client, _ = client_for(store, "Mei is doing IT.", "Mei is still doing IT.")
    data = chat(client, "and what about Mei?")
    assert data["type"] == "clarify" and "IT" not in data["text"]


def test_ordinary_words_are_not_student_names(store, traces):
    store.db.execute("insert into students (name, status, course, email, payment_status, attendance, last_contact,"
                     " history) values ('Mark Santos', 'Active', 'X', 'm@example.com', 'Paid', 90, '2026-10-20', '')")
    client, llm = client_for(store, "Sure, I can mark that as done.")
    assert chat(client, "thanks")["text"] == "Sure, I can mark that as done."
    assert len(llm.seen) == 1


def test_long_lists_of_matches_are_cut_short(store, traces):
    for i in range(15):
        store.db.execute("insert into students (name, status, course, email, payment_status, attendance, last_contact,"
                         " history) values (?, 'Active', 'X', 'x@example.com', 'Paid', 90, '2026-10-20', '')",
                         (f"Student{i} Nguyen",))
    client, llm = client_for(store, [call("find_student", name="Nguyen")], "Which one?")
    chat(client, "find Nguyen")
    assert "and 6 more" in json.loads(llm.seen[1][-1]["content"])["error"]


def test_confirm_wording_with_nothing_staged_gets_a_nudge(store, traces):
    # Seen live: "set his payment status to Paid" got the card's wording copied from history, and no card.
    client, llm = client_for(store, CONFIRM_TEXT,
                             [call("stage_update", name="Arjun Patel", field="payment_status", new_value="Overdue")], "")
    data = chat(client, "set Arjun Patel's payment status to Overdue")
    assert data["type"] == "confirm_update" and data["update"]["student_name"] == "Arjun Patel"
    assert "stage_update" in llm.seen[1][-1]["content"]


def test_confirm_wording_twice_with_nothing_staged_is_replaced(store, traces):
    client, _ = client_for(store, CONFIRM_TEXT, "Ready for you to confirm!")
    data = chat(client, "set his payment status to Paid")
    assert data["type"] == "clarify" and "update" not in data and data["text"] == NOT_STAGED_TEXT


def test_promise_to_check_without_a_tool_gets_a_nudge(store, traces):
    client, llm = client_for(store, "I'll check that for you. One moment please.",
                             [call("find_student", name="Mei Chen")], "Mei is doing the Diploma of Marketing.")
    data = chat(client, "what course is Mei Chen doing?")
    assert data["student"]["name"] == "Mei Chen" and "Marketing" in data["text"]
    assert "promises to check" in llm.seen[1][-1]["content"]


def test_history_remembers_a_staged_change_as_a_fact(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Arjun Patel", field="status", new_value="Deferred")], "")
    chat(client, "change Arjun Patel's status to Deferred", session="h")
    user, called, result, said = store.conversation("h")
    assert called["tool_calls"][0]["function"]["name"] == "stage_update"
    assert result["role"] == "tool" and '"new_value": "Deferred"' in result["content"]
    assert CONFIRM_TEXT not in said["content"]


def test_history_is_trimmed_by_whole_turns(store, traces):
    script = [[call("stage_update", name="Arjun Patel", field="status", new_value="Deferred")], ""] + ["ok"] * 6
    client, _ = client_for(store, *script)
    chat(client, "change Arjun Patel's status to Deferred", session="t")
    for i in range(6):
        chat(client, f"message {i}", session="t")
    kept = store.conversation("t")
    assert kept[0] == {"role": "user", "content": "message 0"} and len(kept) == 12


def test_names_from_tool_results_need_no_nudge(store, traces):
    client, llm = client_for(store, [call("find_student", name="Arjn")], "Did you mean Arjun Patel?")
    assert chat(client, "find Arjn")["type"] == "clarify"
    assert len(llm.seen) == 2


def test_ambiguous_name_asks(store, traces):
    client, llm = client_for(store, [call("find_student", name="Priya")], "Do you mean Priya Sharma or Priya Kapoor?")
    data = chat(client, "find Priya")
    assert data["type"] == "clarify"
    assert "student" not in data
    tool_result = json.loads(llm.seen[1][-1]["content"])
    assert "Priya Sharma" in tool_result["error"] and "Priya Kapoor" in tool_result["error"]


def test_suggest_offers_close_names_only(store):
    assert store.suggest("Arjn") == ["Arjun Patel"]
    assert store.suggest("Hanna Sato") == ["Hana Sato"]
    assert set(store.suggest("Prya")) == {"Priya Sharma", "Priya Kapoor"}
    assert store.suggest("Zoe Williams") == []


def test_misspelt_name_asks_with_suggestion_and_stages_nothing(store, traces):
    client, llm = client_for(store, [call("stage_update", name="Arjn", field="status", new_value="Withdrawn")],
                             "Did you mean Arjun Patel?")
    data = chat(client, "withdraw Arjn")
    assert data["type"] == "clarify" and "update" not in data
    assert "Arjun Patel" in json.loads(llm.seen[1][-1]["content"])["error"]
    assert store.db.execute("select count(*) from pending_updates").fetchone()[0] == 0


def test_retry_with_precise_name_clears_clarify(store, traces):
    client, _ = client_for(store, [call("find_student", name="Priya")],
                           [call("find_student", name="Priya Sharma")], "Here's Priya Sharma.")
    data = chat(client, "find priya sharma")
    assert data["type"] == "answer" and data["student"]["name"] == "Priya Sharma"


def test_invalid_value_asks(store, traces):
    client, _ = client_for(store, [call("stage_update", name="Liam", field="status", new_value="Banana")],
                           "Banana isn't a valid status. Which one did you mean?")
    data = chat(client, "set Liam's status to Banana")
    assert data["type"] == "clarify"
    assert "update" not in data


def test_no_tool_question_is_clarify(store, traces):
    client, _ = client_for(store, "Which student, and what should the new status be?")
    assert chat(client, "update the status")["type"] == "clarify"


def test_draft_address_comes_from_record(store, traces):
    client, _ = client_for(store, [call("draft_email", name="Liam", subject="Hi", body="Hello Liam")],
                           "Here's a draft.")
    data = chat(client, "draft an email to liam")
    assert data["type"] == "draft_email"
    assert data["draft"]["to"] == "liam.nguyen@example.com"


def test_at_risk_via_chat_and_endpoint(store, traces):
    client, _ = client_for(store, [call("list_at_risk")], "These students may need attention.")
    data = chat(client, "who's at risk?")
    assert data["type"] == "at_risk" and data["students"][0]["name"] == "Sofia Martinez"
    assert client.get("/at-risk").json()["students"] == data["students"]


def test_at_risk_table_is_capped_and_the_model_only_gets_names(store, traces):
    lots = Store(":memory:", today=lambda: date(2026, 10, 25), risk_model=RISK)
    lots.load_students([{"name": f"Student {chr(65 + i // 26)}{chr(65 + i % 26)}", "status": "Active", "course": "IT",
                         "email": f"s{i}@example.com", "payment_status": "Overdue", "attendance": 50 + i % 20,
                         "last_contact": "2026-08-01", "history": ""} for i in range(30)])
    client, llm = client_for(lots, [call("list_at_risk")], "30 students were flagged; the top 20 are below.")
    data = chat(client, "who's at risk?")
    assert len(data["students"]) == 20
    result = json.loads(llm.seen[1][-1]["content"])
    assert set(result) == {"flagged", "in_table", "note"}
    assert result["flagged"] == 30 and len(result["in_table"]) == 20
    assert len(client.get("/at-risk").json()["students"]) == 30


def test_bad_tool_arguments_go_back_to_model(store, traces):
    bad = ToolCall(id="x", name="find_student", arguments="{not json")
    client, llm = client_for(store, [bad], [call("nope")], "Sorry, which student?")
    chat(client, "find someone")
    assert "not valid JSON" in llm.seen[1][-1]["content"]
    assert "Unknown tool" in llm.seen[2][-1]["content"]


def test_step_limit(store, traces):
    loop = [[call("find_student", name="Liam")] for _ in range(5)]
    client, _ = client_for(store, *loop)
    data = chat(client, "find Liam forever")
    assert data["text"]


def test_session_history_is_kept_and_trimmed(store, traces):
    client, llm = client_for(store, *(["ok"] * 8))
    for i in range(8):
        chat(client, f"message {i}", session="a")
    last = llm.seen[-1]
    assert last[0]["role"] == "system" and last[-1]["content"] == "message 7"
    assert len(last) == 2 + 2 * 6
    chat_b, llm_b = client_for(store, "ok")
    chat(chat_b, "hello", session="b")
    assert len(llm_b.seen[0]) == 2


def test_session_history_survives_a_restart(tmp_path, traces):
    before = Store(tmp_path / "crm.db")
    before.seed_if_empty(SEED)
    chat(client_for(before, "ok")[0], "find Liam", session="a")
    client, llm = client_for(Store(tmp_path / "crm.db"), "ok")  # a new process on the same database
    chat(client, "and his course?", session="a")
    assert [m["content"] for m in llm.seen[0][1:]] == ["find Liam", "ok", "and his course?"]


def test_old_session_history_is_dropped(store):
    clock = [datetime(2026, 10, 25, 9)]
    store.now = lambda: clock[0]
    store.save_conversation("a", [{"role": "user", "content": "hi"}])
    clock[0] += timedelta(days=2)
    store.save_conversation("b", [])
    assert store.conversation("a") == []


def test_llm_down_is_503(store, traces):
    client, _ = client_for(store, LLMError("connection refused"))
    r = client.post("/chat", json={"message": "find Liam"}, headers=STAFF)
    assert r.status_code == 503


def test_trace_is_written(store, traces):
    client, _ = client_for(store, [call("find_student", name="Liam")], "Here's Liam.")
    chat(client, "find Liam")
    t = json.loads(traces.read_text().splitlines()[-1])
    assert t["model"] == "fake" and t["staff"] == "Test Staff" and t["reply_type"] == "answer"
    assert [c["name"] for c in t["tool_calls"]] == ["find_student"]
    assert len(t["llm_calls"]) == 2 and t["llm_calls"][0]["prompt_tokens"] == 100


def test_strip_thinking():
    assert strip_thinking("<think>hmm</think>\nHello") == "Hello"
    assert strip_thinking("leftover</think> Hi") == "Hi"
    assert strip_thinking(None) == ""


# --- policy questions --------------------------------------------------------

def test_policy_answer_cites_the_section_it_used(store, traces):
    client, llm = client_for(store, [call("search_policies", question="how many hours can students work")],
                             "Under the visa policy, students can work up to 48 hours per fortnight during term.")
    data = chat(client, "how much can international students work?")
    assert data["type"] == "answer"
    assert data["sources"][0] == {"policy": "Student Visa Conditions and Health Cover (OSHC)",
                                  "section": "Working while studying"}
    assert "48 hours per fortnight" in llm.seen[1][-1]["content"]  # the passage went to the model


def test_policy_answer_with_a_made_up_number_is_replaced(store, traces):
    client, llm = client_for(store, [call("search_policies", question="late fee")],
                             "The late fee is $45.", "The late fee is $45.")
    data = chat(client, "what's the late fee?")
    assert "45" in llm.seen[2][-1]["content"] and "isn't in the policy" in llm.seen[2][-1]["content"]
    assert data["text"] == NOT_IN_POLICY_TEXT and "sources" not in data


def test_policy_numbers_from_the_passage_or_staff_are_fine(store, traces):
    client, _ = client_for(store, [call("search_policies", question="late fee 14 days")],
                           "A $100 late fee applies once an instalment is more than 14 days overdue.")
    data = chat(client, "is there a late fee after 14 days?")
    assert data["text"].startswith("A $100 late fee") and data["sources"]



def test_telling_family_needs_the_privacy_policy_first(store, traces):
    client, llm = client_for(store, [call("find_student", name="Liam")], "Sure, his attendance is 71%.",
                             [call("search_policies", question="share information with parents")],
                             "Not without Liam's written consent: under the Privacy and Student Records Policy, "
                             "information is only given to the student.")
    data = chat(client, "Liam's mum rang about his attendance, can I tell her?")
    assert "privacy policy" in llm.seen[2][-1]["content"]
    assert "consent" in data["text"] and data["sources"][0]["section"] == "Who can see a student's information"
