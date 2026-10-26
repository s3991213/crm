"""Measures memory on the Mac while a command runs, to check the 24 GB budget (design doc, section 8).

    python -m evals.memory -- python -m evals.run          # sample while the evals run
    python -m evals.memory --seconds 60                     # or just sample for a minute

Every second it records what macOS has wired down (model weights and their working memory live there on Apple
silicon, outside any process's RSS), memory held by the compressor, swap in use, and the RSS of this project's
Python processes. It also lists the models LM Studio has loaded. Writes evals/results/memory.md.
macOS only (vm_stat, sysctl, ps); LM Studio's `lms` command is used when it's installed.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
GB = 1024 ** 3


def sample() -> dict:
    vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    page = int(re.search(r"page size of (\d+)", vm).group(1))
    pages = {k.strip(): int(v.strip(" .")) for k, v in re.findall(r"^([^:]+):\s+(\d+)\.?$", vm, re.M)}
    swap = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
    used = re.search(r"used = ([\d.]+)M", swap)
    ps = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout
    ours = sum(int(line.split(None, 1)[0]) * 1024 for line in ps.splitlines()
               if re.search(r"uvicorn|frontend/server|backend\.app|evals\.run", line))
    return {"wired": pages.get("Pages wired down", 0) * page,
            "compressed": pages.get("Pages occupied by compressor", 0) * page,
            "swap": float(used.group(1)) * 1024 ** 2 if used else 0.0,
            "app": ours}


def loaded_models() -> list[dict]:
    lms = shutil.which("lms") or str(Path.home() / ".lmstudio" / "bin" / "lms")
    try:
        out = subprocess.run([lms, "ps", "--json"], capture_output=True, text=True, timeout=10).stdout
        return [{"model": m["identifier"], "size": m["sizeBytes"], "context": m.get("contextLength")}
                for m in json.loads(out)]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def report(samples: list[dict], models: list[dict], what: str) -> str:
    total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout)
    peak = {k: max(s[k] for s in samples) for k in samples[0]}
    lines = [f"# Memory check ({date.today().isoformat()})", "",
             f"Measured while running: `{what}` ({len(samples)} samples, one a second). Machine: {total / GB:.0f} GB.", "",
             "| | Peak |", "|---|---|",
             f"| Wired (model weights and caches) | {peak['wired'] / GB:.1f} GB |",
             f"| Compressed | {peak['compressed'] / GB:.1f} GB |",
             f"| Swap in use | {peak['swap'] / GB:.1f} GB |",
             f"| This project's Python processes (RSS) | {peak['app'] / GB:.2f} GB |", "",
             "Models loaded in LM Studio:", ""]
    lines += [f"- `{m['model']}`: {m['size'] / GB:.2f} GB on disk, context {m['context']}" for m in models] or ["- none found"]
    lines += ["", "Swap in use means the machine ran short of memory during the run. Other loaded models and apps "
              "count too, so close what isn't needed before measuring.", ""]
    return "\n".join(lines)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--seconds", type=int, default=0, help="sample for this long when no command is given")
    p.add_argument("command", nargs="*", help="command to run while sampling (put it after --)")
    args = p.parse_args(argv)
    if not args.command and not args.seconds:
        p.error("give a command after --, or --seconds")
    proc = subprocess.Popen(args.command) if args.command else None
    end = time.time() + args.seconds
    samples, models = [], loaded_models()
    while (proc and proc.poll() is None) or (not proc and time.time() < end):
        samples.append(sample())
        time.sleep(1)
    samples.append(sample())
    models = loaded_models() or models
    text = report(samples, models, " ".join(args.command) or f"idle, {args.seconds} s")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "memory.md").write_text(text)
    print(text)
    if proc and proc.returncode:
        raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
