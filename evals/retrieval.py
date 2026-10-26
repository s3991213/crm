"""Measures the policy search (backend/policies.py): keyword, meaning and hybrid, on evals/retrieval.yaml.

    python -m evals.retrieval                     # embedding model from backend/.env
    python -m evals.retrieval --embed-model text-embedding-nomic-embed-text-v1.5

Reports hit@1, hit@3 (is the right section first / in the top 3, which is what the assistant is given) and MRR,
and saves them to evals/results/retrieval.md.
"""

import argparse
import asyncio
from pathlib import Path

import yaml

from backend import app as backend_app
from backend.llm import OpenAIEmbedder
from backend.policies import PolicyIndex

HERE = Path(__file__).parent
MODES = ("keyword", "meaning", "hybrid")


async def measure(index: PolicyIndex, cases: list[dict]) -> dict[str, dict]:
    out = {}
    for mode in MODES:
        ranks, misses = [], []
        for case in cases:
            got = [p.section for p in await index.search(case["q"], k=10, mode=mode)]
            rank = got.index(case["want"]) + 1 if case["want"] in got else None
            ranks.append(rank)
            if rank != 1:
                misses.append(f"{case['q']} → {got[0] if got else 'nothing'} (wanted {case['want']}, rank {rank})")
        n = len(cases)
        out[mode] = {"hit1": sum(r == 1 for r in ranks) / n, "hit3": sum(r is not None and r <= 3 for r in ranks) / n,
                     "mrr": sum(1 / r for r in ranks if r) / n, "misses": misses}
    return out


def report(results: dict[str, dict], model: str, n: int) -> str:
    lines = ["# Policy search: retrieval eval", "",
             f"{n} staff questions (`evals/retrieval.yaml`), embedding model `{model}`.", "",
             "| Search | hit@1 | hit@3 | MRR |", "|---|---|---|---|"]
    lines += [f"| {m} | {r['hit1']:.0%} | {r['hit3']:.0%} | {r['mrr']:.2f} |" for m, r in results.items()]
    lines += ["", "The assistant is given the top 3. Questions where hybrid search didn't rank the right section first:", ""]
    lines += [f"- {m}" for m in results["hybrid"]["misses"]] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--embed-model", default=backend_app.EMBED_MODEL)
    p.add_argument("--base-url", default=backend_app.LLM_BASE_URL)
    args = p.parse_args(argv)
    cases = yaml.safe_load((HERE / "retrieval.yaml").read_text())
    index = PolicyIndex(OpenAIEmbedder(args.base_url, args.embed_model, backend_app.LLM_API_KEY))
    results = asyncio.run(measure(index, cases))
    if index.vectors is None:
        raise SystemExit("The embedding model didn't answer; is it loaded in LM Studio?")
    text = report(results, args.embed_model, len(cases))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "retrieval.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
