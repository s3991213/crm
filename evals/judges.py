"""Have several judge models mark the same saved replies, to see where they disagree.

    python -m evals.judges evals/results/qwen-qwen3-14b-judge-qwen-qwen3.5-9b.json \
        --judges qwen/qwen3-14b qwen/qwen3.5-9b --reasoning-effort qwen/qwen3.5-9b=none

Only replies that passed the exact checks are judged (as in evals.run). Writes evals/results/judges.md.
"""

import argparse
import asyncio
import json
from pathlib import Path

import yaml

from backend import app as backend_app
from backend.llm import OpenAICompatible
from evals.run import HERE, judge


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=Path, help="a results .json written by evals.run")
    ap.add_argument("--judges", nargs="+", required=True)
    ap.add_argument("--reasoning-effort", nargs="*", default=[], metavar="MODEL=EFFORT")
    ap.add_argument("--base-url", default=backend_app.LLM_BASE_URL)
    args = ap.parse_args()

    effort = dict(e.split("=", 1) for e in args.reasoning_effort)
    cases = {c["id"]: c for c in yaml.safe_load((HERE / "cases.yaml").read_text())}
    results = [r for run in json.loads(args.results.read_text()) for r in run]
    todo = [r for r in results if cases.get(r["id"], {}).get("judge") and r["reply"]
            and not [f for f in r["fails"] if not f.startswith("judge")]]
    llms = {m: OpenAICompatible(args.base_url, m, backend_app.LLM_API_KEY, reasoning_effort=effort.get(m))
            for m in args.judges}

    rows = []
    for r in todo:
        verdicts = {m: await judge(llm, cases[r["id"]], r["reply"], no_think=True) for m, llm in llms.items()}
        rows.append((r["id"], verdicts))
        print(r["id"], {m: "pass" if v is None else v for m, v in verdicts.items()})

    lines = [f"# Judges compared on the same replies (`{args.results.name}`)", "",
             f"{len(rows)} judged replies (open-ended text that passed the exact checks).", "",
             "| Judge | Passed |", "|---|---|"]
    lines += [f"| `{m}` | {sum(v[m] is None for _, v in rows)}/{len(rows)} |" for m in args.judges]
    split = [(cid, v) for cid, v in rows if len({x is None for x in v.values()}) > 1]
    lines += ["", f"## Disagreements ({len(split)})", ""]
    for cid, v in split:
        lines.append(f"- `{cid}`: " + "; ".join(f"`{m}` {'pass' if x is None else x}" for m, x in v.items()))
    (HERE / "results" / "judges.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
