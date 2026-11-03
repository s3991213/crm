# Student notes search: keyword vs meaning

Embedding model `text-embedding-nomic-embed-text-v1.5`. 71 hand-written notes (`evals/notes.yaml`) among 1399 routine generated ones. Hybrid uses the policy search's fusion and weights, not tuned for notes. A question can have several right notes: hit@1 is the first note being right, recall@10 how many of the right notes are in the first 10, MAP whether they're near the top. Time: median per question (meaning search is plain Python over every note here).

"agent phrase": `qwen/qwen3-14b` chose search_notes and wrote what to search for (median 3.1 s, not in the times below). "+ 14B": `qwen/qwen3-14b` read the first 20 notes with the staff question and listed the ones that answer it; kept: how many of its listed notes were right (precision) and how many right notes it listed (recall); "nobody": how many of the questions with no answer it listed none for. "by student": the first 20 students by their best note, each shown to the model with that note and the notes just before and after it; the model picks students, and those rows count students, not notes (a student is right if any of their notes answers).

## tuned (20 questions)

| Search | hit@1 | recall@10 | MAP | time | kept precision | kept recall | nobody |
|---|---|---|---|---|---|---|---|
| meaning, agent phrase + 14B by student | 85% | 81% | 0.78 | 3912 ms | 57% | 74% | 4/4 |
| meaning, question + agent phrase + 14B by student | 90% | 84% | 0.84 | 3863 ms | 57% | 82% | 4/4 |

## Can a score cut-off say "nobody"?

Best meaning score of a right note, over the 35 answered questions: lowest 0.548, median 0.627, highest 0.738.

| Question with no answer | best score | best note |
|---|---|---|
| Who's getting married? | 0.587 | Friend's wedding back in Colombia in January, wants 3 weeks off mid-term. |
| Who mentioned joining the army? | 0.602 | Referred by Bright Future Overseas Education Chittagong (Sadia Miah). Interested in the IELTS Preparation. |
| Has anyone been arrested? | 0.567 | Got a speeding fine, asked if it affects his visa. |
| Which students have a dog? | 0.665 | Top mark in the class for the marketing project, trainer has nominated him for the student award. |

## What the model searched for

- Who mentioned a part-time job? → 'part-time job'
- Which students are having money troubles? → 'money troubles'
- Anyone been really stressed or anxious lately? → 'stressed or anxious'
- Who's had trouble finding somewhere to live? → 'trouble finding somewhere to live'
- Has anyone lost a family member? → (didn't call search_notes; the question was searched)
- Who's thinking about leaving for another college? → 'leaving for another college'
- Who's been injured? → 'injured'
- Which students have children or a baby on the way? → (didn't call search_notes; the question was searched)
- Who's finding the English in class hard? → 'finding English in class hard'
- Any complaints about the trainers? → 'complaints about the trainers'
- Who had something stolen? → 'stolen'
- Has anyone been targeted by a scam? → 'scam'
- Which students have a parent who is sick back home? → (didn't call search_notes; the question was searched)
- Who's had transport problems getting to class? → 'transport problems'
- Who wants to change course? → 'change course'
- Who hasn't been answering us? → (didn't call search_notes; the question was searched)
- Anyone with a placement coming up? → 'placement'
- Who wants time off to travel? → 'time off to travel'
- Which students are doing really well? → (didn't call search_notes; the question was searched)
- Is anyone being picked on by classmates? → (didn't call search_notes; the question was searched)
- Who's getting married? → (didn't call search_notes; the question was searched)
- Who mentioned joining the army? → 'joining the army'
- Has anyone been arrested? → 'arrested'
- Which students have a dog? → (didn't call search_notes; the question was searched)

### Not perfect: meaning, agent phrase + 14B by student

- (tuned) Who mentioned a part-time job? → first: "kofi"; found 5/6, missed quang; kept 4
- (tuned) Which students are having money troubles? → first: "bilal"; found 2/3, missed tariq; kept 3
- (tuned) Anyone been really stressed or anxious lately? → first: "zara"; found 4/5, missed dev; kept 8
- (tuned) Who's thinking about leaving for another college? → first: "wen"; found 0/1, missed lucia; kept 2
- (tuned) Which students have children or a baby on the way? → first: "fatima"; found 1/2, missed priyanka; kept 1
- (tuned) Who's had transport problems getting to class? → first: "camila"; found 1/3, missed gita, viktor; kept 1
- (tuned) Who wants to change course? → first: "bg-0"; found 0/1, missed yusuf; kept 2
- (tuned) Anyone with a placement coming up? → first: "wen"; found 1/1; kept 3

### Not perfect: meaning, question + agent phrase + 14B by student

- (tuned) Which students are having money troubles? → first: "bilal"; found 2/3, missed tariq; kept 2
- (tuned) Who's thinking about leaving for another college? → first: "wen"; found 0/1, missed lucia; kept 2
- (tuned) Which students have children or a baby on the way? → first: "fatima"; found 1/2, missed priyanka; kept 1
- (tuned) Who's had transport problems getting to class? → first: "camila"; found 2/3, missed gita; kept 2
- (tuned) Who wants to change course? → first: "wen"; found 0/1, missed yusuf; kept 2
