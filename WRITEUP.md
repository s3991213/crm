# CRM Assistant: a local chat assistant for college front-desk staff

**The problem.** Front-desk staff at a small college spend much of the day looking up records, writing routine
emails and editing fields by hand. What they need to know about a student is spread across records and notes, and
students who are drifting away can go unnoticed. The staff aren't technical, and the records shouldn't leave the office.

**What I built.** A chat assistant staff use in plain English: "summarise Sofia's history", "who's at risk?", "draft
a reminder about her overdue fee", "change Arjun's status to Withdrawn", "can she get a refund if she withdraws
after 5 weeks?". It runs on one 24 GB Mac: Qwen3-14B in LM Studio, a FastAPI backend over SQLite, and a small React
app with staff sign-in. I built and tested it against a synthetic database of 600 students, modelled on what an
Australian CRICOS college has to keep, so moving to the real records is a mapping job rather than a redesign.

## Design choices

**A tool loop, with safety in code.** My original design had the model classify each request once, a Python router
pick the action, and the model write the reply: safe because the pipeline was rigid. I built a tool-calling loop
instead (7 tools, at most 5 steps), because follow-ups like "change her status" would otherwise need routing rules
for every combination. That gives the model more freedom, so the safety rules moved into code, where they don't
depend on the model behaving. No tool can write: the only write happens when a person clicks **Confirm** on a
proposed change, and it's refused if the record changed in the meantime. Values are checked against allowed lists,
there's one change per request, a name matching two students comes back as a question, and email drafts are
addressed from the record and never sent.

**Measured, not assumed.** Whether a free-running loop is reliable enough is a question for tests. I wrote 79 eval
cases from realistic staff requests (typos, paraphrases, multi-turn chats, a planted prompt injection) and set a bar
a model or prompt change has to clear: 95% overall, every safety and update case, and no record written.

**Simpler where the data allowed.** I dropped parts of the design that measurement showed weren't needed: no vector
database or reranker (keyword search plus embeddings found the right policy first 91% of the time), and a logistic
regression for at-risk students rather than gradient boosting, which scored lower and is harder to explain to staff.

## What testing caught

Most safety rules beyond the original plan exist because an eval or a browser session caught the model at it:

- answering about a student **from memory** with no lookup, inventing the record;
- staging a **made-up email address**;
- saying "**the email has been saved**" when nothing had been;
- picking **one of two Priyas** without asking;
- quoting policy **numbers the policy didn't contain**, and getting a refund question wrong because it didn't work
  out that 5 weeks is more than 28 days (that date maths is now done in code);
- at 600 students, **500 students couldn't have a change staged** at all, because every name part was shared.

Each is now enforced in code and has an eval case. The evals had a weakness too: the model judged its own written
replies. A second model as judge caught an overdue-payment email the 14B had passed in itself (it left out which
instalment and how late), but also failed a correct summary for a reason the rubric doesn't give. So I read judge
disagreements rather than trusting either judge.

## Results

All on synthetic data, Qwen3-14B, on a 24 GB Mac.

| What | Result |
|---|---|
| Evals, 79 cases | 79/79, median 6.1 s per reply, 0 records written |
| Same, judged by a different model (Qwen3.5 9B) | 77/79, bar still passed |
| Smaller model (Qwen3.5 9B) on the same evals | 58/79: never unsafe, but asked "shall I?" instead of proposing changes |
| Policy search, right policy first | 91% (keywords 59%, embeddings 78%) |
| At-risk model, cross-validated by student | AUC 0.886, vs 0.838 for a hand-written score |
| Memory during a full eval run | 13.9 GB peak |
| Tests without a model | 156 pytest, UI unit tests, 9 browser tests, in CI |

## What's left

The data is synthetic and shaped by my own assumptions, so the at-risk numbers show the method works, not that it
predicts real students. Next: a read-only connection to the college's records, re-checking the at-risk model on
them, and https on the office network before staff use it.
