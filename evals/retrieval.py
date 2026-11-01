"""Measures the policy search (backend/policies.py): keyword, meaning, hybrid, and hybrid with each reranker.

    python -m evals.retrieval                          # embedding model from backend/.env, no rerankers
    python -m evals.retrieval --rerankers minilm,mxbai,bge,llm --rerank-top 10

Runs on evals/retrieval.yaml (the set KEYWORD_WEIGHT was tuned on) and evals/retrieval_holdout.yaml (never tuned
on). Reports hit@1, hit@3 (is the right section first / in the top 3), MRR, policy@1 (is the right section's policy
first: the assistant is given that whole policy) and the median time per question, and saves them to
evals/results/retrieval.md.
"""

import argparse
import asyncio
import statistics
import time
from pathlib import Path

import yaml

from backend import app as backend_app
from backend.llm import OpenAICompatible, OpenAIEmbedder
from backend.policies import PolicyIndex
from backend.rerank import CROSS_ENCODERS, make_reranker

HERE = Path(__file__).parent
SETS = {"tuned": "retrieval.yaml", "held-out": "retrieval_holdout.yaml"}
MODES = ("keyword", "meaning", "hybrid")


async def measure(index: PolicyIndex, cases: list[dict], mode: str) -> dict:
    policy_of = {p.section: p.policy for p in index.passages}
    ranks, policy_hits, ms, misses = [], 0, [], []
    for case in cases:
        start = time.perf_counter()
        found = await index.search(case["q"], k=10, mode=mode)
        ms.append((time.perf_counter() - start) * 1000)
        got = [p.section for p in found]
        rank = got.index(case["want"]) + 1 if case["want"] in got else None
        ranks.append(rank)
        policy_hits += bool(found) and found[0].policy == policy_of[case["want"]]
        if rank != 1:
            misses.append(f"{case['q']} → {got[0] if got else 'nothing'} (wanted {case['want']}, rank {rank})")
    n = len(cases)
    return {"hit1": sum(r == 1 for r in ranks) / n, "hit3": sum(r is not None and r <= 3 for r in ranks) / n,
            "mrr": sum(1 / r for r in ranks if r) / n, "policy1": policy_hits / n, "ms": statistics.median(ms),
            "misses": misses}


async def run(args) -> dict[str, dict[str, dict]]:
    sets = {name: yaml.safe_load((HERE / f).read_text()) for name, f in SETS.items()}
    index = PolicyIndex(OpenAIEmbedder(args.base_url, args.embed_model, backend_app.LLM_API_KEY),
                        rerank_top=args.rerank_top)
    if not await index._ensure_vectors():
        raise SystemExit("The embedding model didn't answer; is it loaded in LM Studio?")
    configs = [(m, m, None) for m in MODES] + [(f"hybrid + {r}", "hybrid", r) for r in args.rerankers]
    out = {}
    for label, mode, reranker in configs:
        llm = OpenAICompatible(args.base_url, args.llm_model, backend_app.LLM_API_KEY)
        index.reranker = make_reranker(reranker, llm) if reranker else None
        if reranker:  # first call loads the model; keep that out of the timings
            await index.search("warm up", mode="hybrid")
        out[label] = {name: await measure(index, cases, mode) for name, cases in sets.items()}
        print(label, {n: f"{r['hit1']:.0%}" for n, r in out[label].items()}, flush=True)
    return out


def report(results: dict[str, dict[str, dict]], args) -> str:
    rerankers = ", ".join(f"{r} (`{':'.join(CROSS_ENCODERS[r])}`)" if r in CROSS_ENCODERS else f"{r} (`{args.llm_model}`)"
                          for r in args.rerankers)
    lines = ["# Policy search: retrieval eval", "",
             f"Embedding model `{args.embed_model}`. Rerankers re-order the hybrid search's top {args.rerank_top}"
             + (f": {rerankers}." if rerankers else "."), "",
             "Two question sets: `retrieval.yaml` (32, which the keyword weight was tuned on) and "
             "`retrieval_holdout.yaml` (held out: nothing is tuned on it). policy@1: the right section's policy came "
             "first, so it was in what the assistant is given. Time: median per question.", ""]
    for name in SETS:
        n = len(yaml.safe_load((HERE / SETS[name]).read_text()))
        lines += [f"## {name} ({n} questions)", "", "| Search | hit@1 | hit@3 | MRR | policy@1 | time |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| {label} | {r[name]['hit1']:.0%} | {r[name]['hit3']:.0%} | {r[name]['mrr']:.2f} | "
                  f"{r[name]['policy1']:.0%} | {r[name]['ms']:.0f} ms |" for label, r in results.items()]
        lines += [""]
    for label, r in results.items():
        if label == "hybrid" or label.startswith("hybrid +"):
            lines += [f"### Missed first place: {label}", ""]
            for name in SETS:
                lines += [f"- ({name}) {m}" for m in r[name]["misses"]]
            lines += [""]
    return "\n".join(lines)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--embed-model", default=backend_app.EMBED_MODEL)
    p.add_argument("--base-url", default=backend_app.LLM_BASE_URL)
    p.add_argument("--rerankers", default="", type=lambda s: [r for r in s.split(",") if r],
                   help=f"comma-separated: {', '.join(CROSS_ENCODERS)}, llm")
    p.add_argument("--rerank-top", type=int, default=10)
    p.add_argument("--llm-model", default=backend_app.LLM_MODEL, help="for the llm reranker")
    args = p.parse_args(argv)
    text = report(asyncio.run(run(args)), args)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "retrieval.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
