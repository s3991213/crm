# Memory check (2026-10-26)

Measured while running: `/Users/ukkurala/miniconda3/envs/crmenv/bin/python -m evals.run` (995 samples, one a second). Machine: 24 GB.

| | Peak |
|---|---|
| Wired (model weights and caches) | 13.9 GB |
| Compressed | 4.9 GB |
| Swap in use | 2.5 GB |
| This project's Python processes (RSS) | 0.23 GB |

Models loaded in LM Studio:

- `qwen/qwen3-14b`: 7.75 GB on disk, context 16384

Swap in use means the machine ran short of memory during the run. Other loaded models and apps count too, so close what isn't needed before measuring.

Notes on this run: the 9B was unloaded first, so only the 14B (and, during the policy cases, the nomic embedding
model, which LM Studio loads on demand and isn't in its model list) was in memory. 2.6 GB of swap was already in use
before the run started, left from earlier, so swap did not grow during it. The first run, with the idle 9B loaded
too, peaked at 19.6 GB wired and 9.4 GB swap.
