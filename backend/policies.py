"""Search over the college's policy documents (backend/policies/*.md), for questions like "what's the refund rule?".

Hybrid retrieval: a keyword search (SQLite FTS5, BM25) and a meaning search (embeddings from the same
OpenAI-compatible server as the chat model) each rank the sections, and the two rankings are merged with
reciprocal rank fusion. Keywords catch exact terms ("RPL", "PRISMS"); embeddings catch paraphrases ("can she
work more hours?"). If the embedding model is unavailable the keyword search still works on its own.

Each section under a "##" heading is one passage. Embeddings are cached in a JSON file by the text's hash,
so the policies are only re-embedded when they change. The policies are sample documents for a fictional college.
"""

import asyncio
import hashlib
import json
import logging
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

FOLDER = Path(__file__).parent / "policies"
RRF_K = 60  # the usual constant for reciprocal rank fusion
CANDIDATES = 20  # how many each search passes to the fusion
# The keyword ranking counts half as much as the meaning one: a weak keyword match ("what", "student") otherwise
# pulls the wrong section up. Chosen on evals/retrieval.yaml (hit@1 81% -> 91%), so it may flatter that set.
KEYWORD_WEIGHT = 0.5

log = logging.getLogger("crm.policies")


@dataclass
class Passage:
    policy: str
    section: str
    text: str

    @property
    def key(self) -> str:
        return hashlib.sha256(f"{self.policy}\n{self.section}\n{self.text}".encode()).hexdigest()[:16]

    def for_embedding(self) -> str:
        return f"{self.policy}. {self.section}. {self.text}"


def load_passages(folder: Path = FOLDER) -> list[Passage]:
    out = []
    for path in sorted(folder.glob("*.md")):
        policy, section, lines = path.stem, "", []
        for line in path.read_text().splitlines() + ["## "]:
            if line.startswith("# "):
                policy = line[2:].strip()
            elif line.startswith("## "):
                if section and "".join(lines).strip():
                    out.append(Passage(policy, section, "\n".join(lines).strip()))
                section, lines = line[3:].strip(), []
            else:
                lines.append(line)
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)


class PolicyIndex:
    def __init__(self, embedder=None, folder: Path = FOLDER, cache: Path | None = None):
        self.embedder, self.cache = embedder, cache
        self.passages = load_passages(folder)
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.execute("create virtual table fts using fts5(policy, section, text, tokenize='porter')")
        self.db.executemany("insert into fts (rowid, policy, section, text) values (?, ?, ?, ?)",
                            [(i, p.policy, p.section, p.text) for i, p in enumerate(self.passages)])
        self.vectors: list[list[float]] | None = None
        self._lock = asyncio.Lock()

    # --- keyword search ----------------------------------------------------

    def keyword(self, query: str, limit: int = CANDIDATES) -> list[int]:
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 1]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in words)
        rows = self.db.execute("select rowid from fts where fts match ? order by bm25(fts, 2.0, 3.0, 1.0) limit ?",
                               (match, limit)).fetchall()
        return [r[0] for r in rows]

    # --- meaning search ----------------------------------------------------

    async def _ensure_vectors(self) -> bool:
        if self.vectors is not None:
            return True
        if self.embedder is None:
            return False
        async with self._lock:
            if self.vectors is not None:
                return True
            cached = {}
            if self.cache and self.cache.exists():
                data = json.loads(self.cache.read_text())
                if data.get("model") == self.embedder.model:
                    cached = data["vectors"]
            missing = [p for p in self.passages if p.key not in cached]
            if missing:
                try:
                    new = await self.embedder.embed_documents([p.for_embedding() for p in missing])
                except Exception as exc:  # the chat still works with keyword search alone
                    log.warning("Policy embeddings unavailable, using keyword search only: %s", exc)
                    return False
                cached.update({p.key: v for p, v in zip(missing, new)})
                if self.cache:
                    self.cache.parent.mkdir(parents=True, exist_ok=True)
                    keep = {p.key for p in self.passages}
                    self.cache.write_text(json.dumps({"model": self.embedder.model,
                                                      "vectors": {k: v for k, v in cached.items() if k in keep}}))
            self.vectors = [cached[p.key] for p in self.passages]
            return True

    async def meaning(self, query: str, limit: int = CANDIDATES) -> list[int]:
        if not await self._ensure_vectors():
            return []
        try:
            q = await self.embedder.embed_query(query)
        except Exception as exc:
            log.warning("Query embedding failed, using keyword search only: %s", exc)
            return []
        scored = sorted(range(len(self.passages)), key=lambda i: -_cosine(q, self.vectors[i]))
        return scored[:limit]

    # --- both --------------------------------------------------------------

    async def search_with_context(self, query: str, k: int = 3) -> list[Passage]:
        """The best `k` passages, plus every other section of the best one's policy: a rule is often split
        across sections ("Deferring a course", then "How long a deferral can be"), and a policy is short."""
        found = await self.search(query, k)
        if not found:
            return []
        same = [p for p in self.passages if p.policy == found[0].policy]
        return same + [p for p in found if p not in same]

    async def search(self, query: str, k: int = 3, mode: str = "hybrid") -> list[Passage]:
        """The `k` passages that best answer `query`. mode: hybrid, keyword or meaning (for the retrieval eval)."""
        rankings = []
        if mode in ("hybrid", "keyword"):
            rankings.append((KEYWORD_WEIGHT, self.keyword(query)))
        if mode in ("hybrid", "meaning"):
            rankings.append((1.0, await self.meaning(query)))
        fused: dict[int, float] = {}
        for weight, ranking in rankings:
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0) + weight / (RRF_K + rank + 1)
        best = sorted(fused, key=lambda i: -fused[i])[:k]
        return [self.passages[i] for i in best]
