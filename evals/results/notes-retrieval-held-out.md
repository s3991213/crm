# Student notes search: keyword vs meaning

Embedding model `text-embedding-nomic-embed-text-v1.5`. 71 hand-written notes (`evals/notes.yaml`) among 1399 routine generated ones. Hybrid uses the policy search's fusion and weights, not tuned for notes. A question can have several right notes: hit@1 is the first note being right, recall@10 how many of the right notes are in the first 10, MAP whether they're near the top. Time: median per question (meaning search is plain Python over every note here).

"agent phrase": `qwen/qwen3-14b` chose search_notes and wrote what to search for (median 2.9 s, not in the times below). "+ 14B": `qwen/qwen3-14b` read the first 20 notes with the staff question and listed the ones that answer it; kept: how many of its listed notes were right (precision) and how many right notes it listed (recall); "nobody": how many of the questions with no answer it listed none for.

## held-out (15 questions)

| Search | hit@1 | recall@10 | MAP | time | kept precision | kept recall | nobody |
|---|---|---|---|---|---|---|---|
| meaning, agent phrase + 14B | 80% | 62% | 0.62 | 3319 ms | 53% | 50% | 4/4 |

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

### Not perfect: meaning, agent phrase + 14B

- (held-out) Any students who are homesick? → first: "Very homesick, says he cries most nights and is thinking of going back to Sweden."; found 1/2, missed oscar-2; kept 1
- (held-out) Which students might drop out? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/5, missed chen-2, lucia-1, lucia-2, oscar-1; kept 1
- (held-out) Who works in a kitchen or a cafe? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 2/3, missed aiko-2; kept 2
- (held-out) Who's had a family emergency overseas? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 2/3, missed gabriel-1; kept 2
- (held-out) Who needed special arrangements for exams? → first: "Referred by Southern Cross Study Abroad Hanoi (Thanh Pham). Interested in the IELTS Preparation."; found 0/2, missed nadia-1, zara-1; kept 0
- (held-out) Anyone with visa worries? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/5, missed beatriz-1, minh-2, viktor-2, wen-2; kept 1
- (held-out) Is anyone in trouble with the police? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 0/1, missed viktor-2; kept 1
- (held-out) Who's missed classes for a medical reason? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 0/2, missed nadia-1, nadia-2; kept 2
