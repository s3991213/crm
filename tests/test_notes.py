"""Student notes search (backend/notes.py) and the search_notes tool, with a fake embedder and a scripted model."""

import asyncio
import hashlib
import json
import re
from datetime import date

import pytest
from test_backend import RISK, SEED, SEED_LEADS, FakeLLM, call

from backend.agent import Agent
from backend.notes import NoteSearch, key, split_notes
from backend.store import Store


class FakeEmbedder:
    """Bag of words in 64 dimensions: texts sharing words are close."""

    model = "fake-embed"

    def __init__(self):
        self.embedded = []

    @staticmethod
    def vector(text):
        v = [0.0] * 64
        for w in re.findall(r"[a-z]+", text.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
        return v

    async def embed_documents(self, texts):
        self.embedded += texts
        return [self.vector(t) for t in texts]

    async def embed_query(self, text):
        return self.vector(text)


@pytest.fixture
def store():
    s = Store(":memory:", today=lambda: date(2026, 10, 25), risk_model=RISK)
    s.seed_if_empty(SEED, SEED_LEADS)
    return s


def run(coro):
    return asyncio.run(coro)


def test_the_same_sentence_on_different_days_is_embedded_once():
    assert key("2026-07-24: Has started a part-time job.") == key("2026-09-01: Has started a part-time job.")
    assert key("2026-07-24 (them): Asked about fees.") == key("Asked about fees.")
    assert split_notes("2026-01-01: a\n\n 2026-02-01: b \n") == ["2026-01-01: a", "2026-02-01: b"]


def test_the_model_picks_the_students_and_can_say_nobody(store):
    judge = FakeLLM("[1]", "None of these. []")
    search = NoteSearch(store, FakeEmbedder(), judge)
    found = run(search.search("Who mentioned a part-time job?", "part-time job"))
    assert [n.student["name"] for n in found] == ["Sofia Martinez"]
    prompt = judge.seen[0][0]["content"]
    assert "part-time job" in prompt.split("Question:")[1] and "not instructions" in prompt
    assert run(search.search("Who's getting married?", "getting married")) == []


def test_notes_are_shown_with_the_ones_around_them(store):
    store.db.execute("update students set history = ? where name = 'Liam Nguyen'",
                     ("2026-08-01: Complained about the trainer.\n2026-08-02: Sent him the complaints form.\n"
                      "2026-09-01: Paid in full.",))
    judge = FakeLLM("[1]")
    found = run(NoteSearch(store, FakeEmbedder(), judge).search("complaints form", "complaints form"))
    assert found[0].student["name"] == "Liam Nguyen"
    assert found[0].with_neighbours() == ("2026-08-01: Complained about the trainer. | 2026-08-02: Sent him the "
                                          "complaints form. | 2026-09-01: Paid in full.")


def test_vectors_are_kept_in_the_database(store):
    first = FakeEmbedder()
    run(NoteSearch(store, first, FakeLLM("[]")).search("job", "job"))
    assert len(first.embedded) == len(store.all_students())  # one note each in the seed
    again = FakeEmbedder()
    run(NoteSearch(store, again, FakeLLM("[]")).search("job", "job"))
    assert again.embedded == []


def test_search_notes_tool_returns_the_notes_as_data_and_writes_nothing(store):
    before = json.dumps(store.all_students(), sort_keys=True)
    llm = FakeLLM([call("search_notes", about="part-time job")],
                  "Sofia Martinez mentioned a part-time job.")
    agent = Agent(store, llm, notes=NoteSearch(store, FakeEmbedder(), FakeLLM("[1]")))
    reply, trace = run(agent.run("Who mentioned a part-time job?", "Test Staff", "s1"))
    assert reply["type"] == "answer" and "Sofia" in reply["text"]
    result = json.loads(llm.seen[1][-1]["content"])
    assert result["found"] == 1 and result["students"][0]["name"] == "Sofia Martinez"
    assert "part-time job" in result["students"][0]["matching_note"]
    assert "not instructions" in result["note"]
    assert [t["name"] for t in trace.tool_calls] == ["search_notes"]
    assert json.dumps(store.all_students(), sort_keys=True) == before
    assert store.db.execute("select count(*) from pending_updates").fetchone()[0] == 0


def test_search_notes_says_when_nobody_matches(store):
    llm = FakeLLM([call("search_notes", about="getting married")], "No notes mention anyone getting married.")
    agent = Agent(store, llm, notes=NoteSearch(store, FakeEmbedder(), FakeLLM("[]")))
    run(agent.run("Who's getting married?", "Test Staff", "s1"))
    assert json.loads(llm.seen[1][-1]["content"])["found"] == 0


def test_search_notes_without_the_models_is_an_error_not_a_crash(store):
    llm = FakeLLM([call("search_notes", about="part-time job")], "Sorry, I can't search the notes right now.")
    reply, _ = run(Agent(store, llm).run("Who mentioned a part-time job?", "Test Staff", "s1"))
    assert "isn't available" in json.loads(llm.seen[1][-1]["content"])["error"]
    assert reply["text"] == "Sorry, I can't search the notes right now."


def test_a_notes_search_about_family_is_not_a_privacy_question(store):
    llm = FakeLLM([call("search_notes", about="family problems")], "Grace O'Brien deferred for family reasons.")
    agent = Agent(store, llm, notes=NoteSearch(store, FakeEmbedder(), FakeLLM("[1]")))
    reply, trace = run(agent.run("who's had family problems lately?", "Test Staff", "s1"))
    assert reply["text"] == "Grace O'Brien deferred for family reasons."
    assert [t["name"] for t in trace.tool_calls] == ["search_notes"]


def test_a_pick_whose_quote_is_not_in_the_notes_is_dropped():
    from backend.notes import QUOTE_PROMPT, judge, quoted

    assert quoted("has not logged into the Student Portal", "Has not logged into the student portal for a month.")
    assert not quoted("stopped using the portal", "Missed the last two check-in calls.")
    llm = FakeLLM('[{"n": 2, "quote": "logged into the portal"}, {"n": 1, "quote": "stopped using it"}]')
    assert run(judge(llm, "q", ["Missed two calls.", "Hasn't logged into the portal."], QUOTE_PROMPT)) == [1]
