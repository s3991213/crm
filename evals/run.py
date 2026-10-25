"""Run the eval cases against a real model and report pass rates and latency.

    python -m evals.run                         # model from backend/.env
    python -m evals.run --model qwen/qwen3-14b --repeat 3
    python -m evals.run --only update-status --verbose

Each case runs on a fresh copy of the seed data. Results go to evals/results/<model>.{md,json}.
"""

import argparse
import asyncio
import json
import re
import statistics
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

from backend import app as backend_app
from backend.agent import NOTHING_SAVED_TEXT, SAVED_CLAIM, Agent
from backend.llm import LLMError, OpenAICompatible
from backend.store import Store

HERE = Path(__file__).parent
TODAY = date(2026, 10, 25)  # fixed, so "days since contact" and risk scores don't drift


def check(expect: dict, reply: dict, tools: list[str], staged: int, wrote: bool) -> list[str]:
    """Every way the reply misses the expectation. Empty means pass."""
    fails = []
    if wrote:
        fails.append("a student record was written")
    if "type" in expect:
        ok = expect["type"] if isinstance(expect["type"], list) else [expect["type"]]
        if reply["type"] not in ok:
            fails.append(f"type {reply['type']!r}, expected {ok}")
    if "student" in expect:
        got = (reply.get("student") or {}).get("name")
        if got != expect["student"]:
            fails.append(f"student card {got!r}, expected {expect['student']!r}")
    for t in expect.get("tools", []):
        if t not in tools:
            fails.append(f"{t} not called")
    for t in expect.get("not_tools", []):
        if t in tools:
            fails.append(f"{t} called")
    if "update" in expect:
        u, want = reply.get("update"), expect["update"]
        if want is None:
            if u:
                fails.append(f"staged a change: {u['student_name']} {u['field']} -> {u['new_value']}")
        elif not u:
            fails.append("no change staged")
        else:
            got = {"student": u["student_name"], "field": u["field"], "new_value": u["new_value"]}
            if {k: str(v).lower() for k, v in got.items()} != {k: str(v).lower() for k, v in want.items()}:
                fails.append(f"staged {got}, expected {want}")
    if "draft_to" in expect and (reply.get("draft") or {}).get("to") != expect["draft_to"]:
        fails.append(f"draft to {(reply.get('draft') or {}).get('to')!r}, expected {expect['draft_to']!r}")
    if "draft_to_not" in expect and (reply.get("draft") or {}).get("to") == expect["draft_to_not"]:
        fails.append(f"draft addressed to {expect['draft_to_not']}")
    if "update_count_max" in expect and staged > expect["update_count_max"]:
        fails.append(f"{staged} changes staged")
    if expect.get("no_saved_claim") and SAVED_CLAIM.search(reply.get("text", "").replace(NOTHING_SAVED_TEXT, "")):
        fails.append("text claims something was saved or sent")
    for word in expect.get("text_has", []):
        if word.lower() not in reply.get("text", "").lower():
            fails.append(f"text lacks {word!r}")
    return fails


async def run_case(case: dict, llm, no_think: bool) -> dict:
    store = Store(":memory:", today=lambda: TODAY)
    store.seed_if_empty(backend_app.HERE / "seed.json")
    before = json.dumps(store.all_students(), sort_keys=True)
    agent = Agent(store, llm, system_suffix="\n/no_think" if no_think else "")
    start = time.perf_counter()
    try:
        for msg in case.get("before", []):
            await agent.run(msg, "Eval Staff", "eval")
        store.db.execute("delete from pending_updates")  # judge only what the final message stages
        reply, trace = await agent.run(case["message"], "Eval Staff", "eval")
    except LLMError as exc:
        return {"id": case["id"], "category": case["category"], "pass": False, "fails": [f"LLM error: {exc}"],
                "ms": 0, "tokens": 0, "reply": None}
    tools = [t["name"] for t in trace.tool_calls]
    staged = store.db.execute("select count(*) from pending_updates").fetchone()[0]
    wrote = json.dumps(store.all_students(), sort_keys=True) != before
    fails = check(case["expect"], reply, tools, staged, wrote)
    return {
        "id": case["id"], "category": case["category"], "pass": not fails, "fails": fails,
        "ms": round((time.perf_counter() - start) * 1000), "final_ms": trace.ms,
        "tokens": sum(c["prompt_tokens"] + c["completion_tokens"] for c in trace.llm_calls),
        "tools": tools, "reply": reply,
    }


def percentile(values: list[int], p: float) -> int:
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p * (len(values) - 1))))] if values else 0


def report(model: str, no_think: bool, repeat: int, results: list[list[dict]]) -> str:
    by_case = defaultdict(list)
    for run in results:
        for r in run:
            by_case[r["id"]].append(r)
    cats = defaultdict(lambda: [0, 0, 0])  # runs passed, runs total, cases passing every run
    for runs in by_case.values():
        c = cats[runs[0]["category"]]
        c[0] += sum(r["pass"] for r in runs)
        c[1] += len(runs)
        c[2] += all(r["pass"] for r in runs)
    flat = [r for run in results for r in run]
    latencies = [r["final_ms"] for r in flat if r.get("final_ms")]
    passed, total = sum(r["pass"] for r in flat), len(flat)
    strict = sum(all(r["pass"] for r in runs) for runs in by_case.values())

    lines = [
        f"# Eval results: `{model}`", "",
        f"- Date: {date.today().isoformat()} · thinking {'off' if no_think else 'on'} · {len(by_case)} cases × {repeat} run(s)",
        f"- **Pass rate: {passed}/{total} ({passed / total:.0%})**"
        + (f" · pass^{repeat} (every run passes): {strict}/{len(by_case)}" if repeat > 1 else ""),
        f"- Latency per request: p50 {percentile(latencies, 0.5) / 1000:.1f}s · p95 {percentile(latencies, 0.95) / 1000:.1f}s",
        f"- Tokens per case (avg): {statistics.mean(r['tokens'] for r in flat):.0f}",
        f"- Records written by the model: **{sum('a student record was written' in r['fails'] for r in flat)}**", "",
        "| Category | Passed | Rate |", "|---|---|---|",
    ]
    for cat, (p, n, _) in cats.items():
        lines.append(f"| {cat} | {p}/{n} | {p / n:.0%} |")
    failing = [(cid, runs) for cid, runs in by_case.items() if not all(r["pass"] for r in runs)]
    if failing:
        lines += ["", "## Failures", ""]
        for cid, runs in failing:
            for r in runs:
                if not r["pass"]:
                    lines.append(f"- `{cid}`: {'; '.join(r['fails'])}")
    return "\n".join(lines) + "\n"


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=backend_app.LLM_MODEL)
    ap.add_argument("--base-url", default=backend_app.LLM_BASE_URL)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", help="run only cases whose id contains this text")
    ap.add_argument("--think", action="store_true", help="let the model think (slower)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cases = yaml.safe_load((HERE / "cases.yaml").read_text())
    if args.only:
        cases = [c for c in cases if args.only in c["id"]]
    llm = OpenAICompatible(args.base_url, args.model, backend_app.LLM_API_KEY)
    no_think = not args.think

    results = []
    for i in range(args.repeat):
        run = []
        for case in cases:
            r = await run_case(case, llm, no_think)
            run.append(r)
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"[{i + 1}/{args.repeat}] {mark} {r['ms'] / 1000:5.1f}s {case['id']:32} {'; '.join(r['fails'])}")
            if args.verbose and r["reply"]:
                print("        ", json.dumps(r["reply"])[:300])
        results.append(run)

    md = report(args.model, no_think, args.repeat, results)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9.]+", "-", args.model.lower()).strip("-") + ("" if no_think else "-think")
    if not args.only:
        (out / f"{slug}.md").write_text(md)
        (out / f"{slug}.json").write_text(json.dumps(results, indent=1))
    print("\n" + md)


if __name__ == "__main__":
    asyncio.run(main())
