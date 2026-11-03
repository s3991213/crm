# Student notes search: keyword vs meaning

Embedding model `text-embedding-nomic-embed-text-v1.5`. 71 hand-written notes (`evals/notes.yaml`) among 1399 routine generated ones. Hybrid uses the policy search's fusion and weights, not tuned for notes. A question can have several right notes: hit@1 is the first note being right, recall@10 how many of the right notes are in the first 10, MAP whether they're near the top. Time: median per question (meaning search is plain Python over every note here).

"agent phrase": `qwen/qwen3-14b` chose search_notes and wrote what to search for (median 3.2 s, not in the times below). "+ 14B": `qwen/qwen3-14b` read the first 20 notes with the staff question and listed the ones that answer it; kept: how many of its listed notes were right (precision) and how many right notes it listed (recall); "nobody": how many of the questions with no answer it listed none for. "by student": the first 20 students by their best note, each shown to the model with that note and the notes just before and after it; the model picks students, and those rows count students, not notes (a student is right if any of their notes answers).

## held-out (15 questions)

| Search | hit@1 | recall@10 | MAP | time | kept precision | kept recall | nobody |
|---|---|---|---|---|---|---|---|
| meaning, question + agent phrase + 14B by student | 87% | 72% | 0.72 | 4488 ms | 73% | 59% | 4/4 |

## Can a score cut-off say "nobody"?

Best meaning score of a right note, over the 35 answered questions: lowest 0.548, median 0.627, highest 0.738.

| Question with no answer | best score | best note |
|---|---|---|
| Who's getting married? | 0.587 | Friend's wedding back in Colombia in January, wants 3 weeks off mid-term. |
| Who mentioned joining the army? | 0.602 | Referred by Bright Future Overseas Education Chittagong (Sadia Miah). Interested in the IELTS Preparation. |
| Has anyone been arrested? | 0.567 | Got a speeding fine, asked if it affects his visa. |
| Which students have a dog? | 0.665 | Top mark in the class for the marketing project, trainer has nominated him for the student award. |

## What the model searched for

- Who's doing food delivery? → 'food delivery'
- Any students who are homesick? → 'homesick'
- Who's worried about rent? → 'rent'
- Which students might drop out? → (didn't call search_notes; the question was searched)
- Who works in a kitchen or a cafe? → (didn't call search_notes; the question was searched)
- Who's had a family emergency overseas? → 'family emergency overseas'
- Who needed special arrangements for exams? → 'special arrangements for exams'
- Anyone with visa worries? → 'visa worries'
- Who has their partner here with them? → (didn't call search_notes; the question was searched)
- Who couldn't log in to the online systems? → (didn't call search_notes; the question was searched)
- Is anyone in trouble with the police? → 'trouble with the police'
- Who had a crash? → (didn't call search_notes; the question was searched)
- Who's sending money home? → 'sending money home'
- Anyone seeing the counsellor? → 'counsellor'
- Who's missed classes for a medical reason? → 'missed classes medical reason'
- Who's getting married? → (didn't call search_notes; the question was searched)
- Who mentioned joining the army? → 'joining the army'
- Has anyone been arrested? → 'arrested'
- Which students have a dog? → (didn't call search_notes; the question was searched)

### Not perfect: meaning, question + agent phrase + 14B by student

- (held-out) Which students might drop out? → first: "wen"; found 1/4, missed chen, lucia, oscar; kept 1
- (held-out) Who works in a kitchen or a cafe? → first: "kofi"; found 2/3, missed aiko; kept 2
- (held-out) Who's had a family emergency overseas? → first: "jia"; found 2/3, missed gabriel; kept 2
- (held-out) Who needed special arrangements for exams? → first: "bg-787"; found 0/2, missed nadia, zara; kept 0
- (held-out) Anyone with visa worries? → first: "minh"; found 1/4, missed beatriz, viktor, wen; kept 1
- (held-out) Who's missed classes for a medical reason? → first: "uma"; found 0/1, missed nadia; kept 2
