"""The LLM backend with a scripted fake model: tool routing, safety rules, and the API contract."""

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as backend_app
from backend.agent import CONFIRM_TEXT
from backend.llm import Completion, LLMError, ToolCall, strip_thinking
from backend.store import Store, StoreError

SEED = Path(backend_app.__file__).parent / "seed.json"
STAFF = {"X-Staff-Name": "Test Staff"}
CARD_KEYS = {"name", "status", "course", "last_contact", "payment_status"}


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
    s = Store(":memory:", today=lambda: date(2026, 10, 25))
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
    assert [r["name"] for r in rows] == ["Liam Nguyen", "Priya Kapoor", "Sofia Martinez"]
    assert rows[0]["reasons"] == ["No contact in 53 days", "Payment overdue"]
    assert all(len(r["reasons"]) <= 2 for r in rows)


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
    assert data["update"]["student_name"] == "Liam Nguyen"
    assert store.db.execute("select count(*) from pending_updates").fetchone()[0] == 1


def test_ambiguous_name_asks(store, traces):
    client, llm = client_for(store, [call("find_student", name="Priya")], "Do you mean Priya Sharma or Priya Kapoor?")
    data = chat(client, "find Priya")
    assert data["type"] == "clarify"
    assert "student" not in data
    tool_result = json.loads(llm.seen[1][-1]["content"])
    assert "Priya Sharma" in tool_result["error"] and "Priya Kapoor" in tool_result["error"]


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
    assert data["type"] == "at_risk" and data["students"][0]["name"] == "Liam Nguyen"
    assert client.get("/at-risk").json()["students"] == data["students"]


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
