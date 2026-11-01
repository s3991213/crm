"""Policy search (backend/policies.py) with a fake embedding model."""

import asyncio
import re

import pytest

from backend.llm import Completion, LLMError
from backend.policies import PolicyIndex, load_passages
from backend.rerank import LLMReranker, make_reranker

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


class Reverse:
    """A reranker that turns the candidates around, and remembers what it was given."""

    def __init__(self, fail=False):
        self.fail, self.got = fail, []

    async def rerank(self, question, texts):
        if self.fail:
            raise LLMError("model not loaded")
        self.got = texts
        return list(range(len(texts)))[::-1]


def test_reranker_reorders_the_top_candidates_only():
    plain = sections(asyncio.run(PolicyIndex().search("refund visa refused", k=20, mode="keyword")))
    reverse = Reverse()
    index = PolicyIndex(reranker=reverse, rerank_top=4)
    found = sections(asyncio.run(index.search("refund visa refused", k=20, mode="hybrid")))
    assert found[:4] == plain[:4][::-1] and found[4:] == plain[4:]
    whole = {p.for_embedding() for p in index.passages}  # policy, section and text, not the text alone
    assert len(reverse.got) == 4 and all(t in whole for t in reverse.got)


def test_reranker_is_left_out_of_the_eval_only_modes():
    index = PolicyIndex(reranker=Reverse())
    assert sections(asyncio.run(index.search("RPL", mode="keyword")))[0] == "Recognition of prior learning"


def test_a_failing_reranker_keeps_the_hybrid_order():
    plain = sections(asyncio.run(PolicyIndex().search("refund visa refused", k=5)))
    assert sections(asyncio.run(PolicyIndex(reranker=Reverse(fail=True)).search("refund visa refused", k=5))) == plain


class Says:
    model = "fake"

    def __init__(self, text):
        self.text, self.prompts = text, []

    async def complete(self, messages, tools):
        assert tools is None
        self.prompts.append(messages[-1]["content"])
        return Completion(content=self.text)


def test_llm_reranker_reads_the_ranking_and_keeps_the_rest_in_place():
    llm = Says("Most relevant first: [3, 1, 3, 9]")
    order = asyncio.run(LLMReranker(llm).rerank("refund?", ["a", "b", "c", "d"]))
    assert order == [2, 0, 1, 3]  # repeats and numbers out of range are ignored
    assert "[3] c" in llm.prompts[0] and llm.prompts[0].endswith("/no_think")


def test_llm_reranker_without_a_ranking_fails_so_the_search_keeps_its_order():
    with pytest.raises(ValueError):
        asyncio.run(LLMReranker(Says("I think the second one.")).rerank("refund?", ["a", "b"]))


def test_make_reranker():
    assert make_reranker("off") is None and make_reranker("") is None
    assert isinstance(make_reranker("llm", Says("[1]")), LLMReranker)
    with pytest.raises(ValueError):
        make_reranker("best-one")
