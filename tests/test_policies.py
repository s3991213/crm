"""Policy search (backend/policies.py) with a fake embedding model."""

import asyncio
import re

from backend.llm import LLMError
from backend.policies import PolicyIndex, load_passages

WORDS = ["work", "job", "shifts", "hours", "refund", "money", "back", "quit", "insurance", "cover", "mum", "parents"]


class FakeEmbedder:
    """Counts a few words, with job-ish words pointing the same way, so paraphrases land near each other."""

    model = "fake-embed"

    def __init__(self, fail=False):
        self.fail, self.doc_calls = fail, 0

    def _vec(self, text):
        words = re.findall(r"[a-z]+", text.lower())
        v = [float(words.count(w)) for w in WORDS]
        v[0] += v[1] + v[2]  # "job" and "shifts" mean work
        return [x + 0.01 for x in v]

    async def embed_documents(self, texts):
        if self.fail:
            raise LLMError("no embedding model loaded")
        self.doc_calls += 1
        return [self._vec(t) for t in texts]

    async def embed_query(self, text):
        return self._vec(text)


def sections(passages):
    return [p.section for p in passages]


def test_each_section_is_one_passage():
    passages = load_passages()
    assert len(passages) > 40
    assert all(p.policy and p.section and p.text and not p.text.startswith("#") for p in passages)
    assert len({(p.policy, p.section) for p in passages}) == len(passages)


def test_keyword_search_finds_exact_terms():
    index = PolicyIndex()
    assert sections(asyncio.run(index.search("48 hours per fortnight", mode="keyword")))[0] == "Working while studying"
    assert sections(asyncio.run(index.search("RPL", mode="keyword")))[0] == "Recognition of prior learning"
    assert asyncio.run(index.search("???", mode="keyword")) == []


def test_hybrid_search_uses_both_rankings():
    index = PolicyIndex(FakeEmbedder())
    found = sections(asyncio.run(index.search("Can she pick up extra shifts?", k=3)))
    assert "Working while studying" in found
    assert index.vectors is not None and len(index.vectors) == len(index.passages)


def test_falls_back_to_keywords_when_embeddings_fail():
    index = PolicyIndex(FakeEmbedder(fail=True))
    found = asyncio.run(index.search("refund visa refused", k=3))
    assert "Refunds when a visa is refused" in sections(found)
    assert index.vectors is None


def test_embeddings_are_cached_by_text(tmp_path):
    cache = tmp_path / "vectors.json"
    first = FakeEmbedder()
    asyncio.run(PolicyIndex(first, cache=cache).search("refund"))
    second = FakeEmbedder()
    asyncio.run(PolicyIndex(second, cache=cache).search("refund"))
    assert first.doc_calls == 1 and second.doc_calls == 0
