# Policy search: retrieval eval

Embedding model `text-embedding-nomic-embed-text-v1.5`. Rerankers re-order the hybrid search's top 10: minilm (`cross-encoder/ms-marco-MiniLM-L6-v2:onnx/model.onnx`), mxbai (`mixedbread-ai/mxbai-rerank-xsmall-v1:onnx/model.onnx`), bge (`Xenova/bge-reranker-base:onnx/model_int8.onnx`), llm (`qwen/qwen3-14b`).

Two question sets: `retrieval.yaml` (32, which the keyword weight was tuned on) and `retrieval_holdout.yaml` (held out: nothing is tuned on it). policy@1: the right section's policy came first, so it was in what the assistant is given. Time: median per question.

## tuned (32 questions)

| Search | hit@1 | hit@3 | MRR | policy@1 | time |
|---|---|---|---|---|---|
| keyword | 62% | 91% | 0.74 | 72% | 0 ms |
| meaning | 78% | 91% | 0.84 | 84% | 18 ms |
| hybrid | 91% | 94% | 0.93 | 94% | 28 ms |
| hybrid + minilm | 91% | 94% | 0.94 | 91% | 71 ms |
| hybrid + mxbai | 84% | 97% | 0.90 | 91% | 182 ms |
| hybrid + bge | 81% | 97% | 0.88 | 91% | 286 ms |
| hybrid + llm | 94% | 100% | 0.97 | 100% | 6045 ms |

## held-out (38 questions)

| Search | hit@1 | hit@3 | MRR | policy@1 | time |
|---|---|---|---|---|---|
| keyword | 39% | 71% | 0.55 | 55% | 0 ms |
| meaning | 61% | 87% | 0.75 | 71% | 17 ms |
| hybrid | 68% | 87% | 0.78 | 76% | 25 ms |
| hybrid + minilm | 76% | 95% | 0.84 | 84% | 76 ms |
| hybrid + mxbai | 71% | 87% | 0.82 | 76% | 185 ms |
| hybrid + bge | 63% | 95% | 0.79 | 79% | 296 ms |
| hybrid + llm | 92% | 100% | 0.96 | 95% | 5248 ms |

### Missed first place: hybrid

- (tuned) Student wants to quit, does she get any money back? → If the college can't deliver the course (wanted Refunds when a student withdraws, rank 8)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 3)
- (tuned) Her mum called asking about her grades, can I tell her? → Making a formal complaint or appeal (wanted Who can see a student's information, rank 4)
- (held-out) If she gets credit for three units, does she pay less? → Recognition of prior learning (wanted Effect on the course, rank 3)
- (held-out) What paperwork does a student need to put off their start date? → Keeping details up to date (wanted Applying for a deferral, rank 10)
- (held-out) What has to happen before an applicant's place is locked in? → When to apply (wanted Letter of offer, rank 3)
- (held-out) Someone rang claiming to be Liam, what should I ask before talking about his record? → Referrals (wanted Checking identity, rank 4)
- (held-out) A 17-year-old wants to rent a flat with friends, is that allowed? → Who can see a student's information (wanted Students under 18, rank 2)
- (held-out) A student can't get into Moodle, who sorts that out? → Raising a concern informally (wanted Login and portal help, rank 10)
- (held-out) We said no to her transfer, can she challenge that? → The six-month rule (wanted If the request is refused, rank 3)
- (held-out) Can she keep coming to class while she waits for her new visa? → Visa extensions and new visas (wanted Bridging visas, rank 2)
- (held-out) Can we give an agent his attendance report? → Reporting to the government (wanted Education agents, rank 2)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → When attendance drops (wanted Who can see a student's information, rank 9)
- (held-out) Her insurance runs out next month, do we chase that? → The six-month rule (wanted Health cover, rank 2)
- (held-out) Her brother rang wanting to know if she's been turning up to class. → Keeping details up to date (wanted Who can see a student's information, rank None)

### Missed first place: hybrid + minilm

- (tuned) How many hours a week can international students work? → Attendance requirement (wanted Working while studying, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 4)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 4)
- (held-out) What paperwork does a student need to put off their start date? → Visa extensions and new visas (wanted Applying for a deferral, rank 9)
- (held-out) Student says she's leaving the college, what's the first step? → Changing course (wanted Withdrawing from a course, rank 3)
- (held-out) What has to happen before an applicant's place is locked in? → When to apply (wanted Letter of offer, rank 3)
- (held-out) Do we pass enrolment details on to the Department? → Confirmation of Enrolment (wanted Sharing with government, rank 6)
- (held-out) Her date of birth is wrong in our system, can she get it fixed? → Checking identity (wanted Correcting records, rank 2)
- (held-out) A student can't get into Moodle, who sorts that out? → Raising a concern informally (wanted Login and portal help, rank 3)
- (held-out) His course end date moved and his visa runs out first, what now? → Health cover (wanted Visa extensions and new visas, rank 3)
- (held-out) Her brother rang wanting to know if she's been turning up to class. → Students under 18 (wanted Who can see a student's information, rank 3)
- (held-out) Her husband is coming over on her visa, does she need health cover for him too? → Bridging visas (wanted Health cover, rank 2)

### Missed first place: hybrid + mxbai

- (tuned) Can Sofia pick up extra shifts at her café during the semester? → Orientation (wanted Working while studying, rank 3)
- (tuned) What do we do when a student's attendance falls under 80 percent? → Reporting to the government (wanted When attendance drops, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 2)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 4)
- (tuned) Can I tell the agent about his attendance? → Sharing with government (wanted Education agents, rank 3)
- (held-out) What paperwork does a student need to put off their start date? → Deferring a course (wanted Applying for a deferral, rank 4)
- (held-out) Student says she's leaving the college, what's the first step? → Changing course (wanted Withdrawing from a course, rank 2)
- (held-out) He wants to switch from business to IT here, how does that work? → Login and portal help (wanted Changing course, rank 4)
- (held-out) The college is shutting down the cookery course, what happens to the students' money? → Withdrawing from a course (wanted If the college can't deliver the course, rank 2)
- (held-out) Her date of birth is wrong in our system, can she get it fixed? → Checking identity (wanted Correcting records, rank 2)
- (held-out) Can we give an agent his attendance report? → Reporting to the government (wanted Education agents, rank 4)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → Login and portal help (wanted Who can see a student's information, rank 8)
- (held-out) Her insurance runs out next month, do we chase that? → Payment plans (wanted Health cover, rank 2)
- (held-out) Her brother rang wanting to know if she's been turning up to class. → Attendance requirement (wanted Who can see a student's information, rank 4)
- (held-out) Can I tell his wife what marks he got? → Entry requirements (wanted Who can see a student's information, rank 2)
- (held-out) Her father wants a copy of her report card, is that allowed? → Medical certificates and approved absences (wanted Who can see a student's information, rank 2)

### Missed first place: hybrid + bge

- (tuned) How many hours a week can international students work? → Attendance requirement (wanted Working while studying, rank 2)
- (tuned) Can Sofia pick up extra shifts at her café during the semester? → Orientation (wanted Working while studying, rank 9)
- (tuned) What do we do when a student's attendance falls under 80 percent? → Reporting to the government (wanted When attendance drops, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 3)
- (tuned) What's the maximum break a student can take from their course? → Deferring a course (wanted How long a deferral can be, rank 2)
- (tuned) When do we give a release letter? → Asking for a release letter (wanted When a release letter is given, rank 3)
- (held-out) Does the attendance rule apply to local students as well, or just visa holders? → Working while studying (wanted Who this applies to, rank 2)
- (held-out) He's annoyed with his trainer, should he go straight to a formal complaint? → Making a formal complaint or appeal (wanted Raising a concern informally, rank 2)
- (held-out) Can she keep studying while her appeal is being looked at? → Bridging visas (wanted During the process, rank 2)
- (held-out) If she gets credit for three units, does she pay less? → Course progress (wanted Effect on the course, rank 3)
- (held-out) What paperwork does a student need to put off their start date? → Deferring a course (wanted Applying for a deferral, rank 2)
- (held-out) Student says she's leaving the college, what's the first step? → Suspension or cancellation by the college (wanted Withdrawing from a course, rank 7)
- (held-out) What has to happen before an applicant's place is locked in? → When to apply (wanted Letter of offer, rank 2)
- (held-out) He wants to switch from business to IT here, how does that work? → Asking for a release letter (wanted Changing course, rank 3)
- (held-out) Do we pass enrolment details on to the Department? → Confirmation of Enrolment (wanted Sharing with government, rank 5)
- (held-out) Her date of birth is wrong in our system, can she get it fixed? → Checking identity (wanted Correcting records, rank 2)
- (held-out) A student can't get into Moodle, who sorts that out? → Raising a concern informally (wanted Login and portal help, rank 2)
- (held-out) His course end date moved and his visa runs out first, what now? → Health cover (wanted Visa extensions and new visas, rank 2)
- (held-out) Can a student work full time over the summer holidays? → Deferring a course (wanted Working while studying, rank 2)
- (held-out) Her husband is coming over on her visa, does she need health cover for him too? → Keeping details up to date (wanted Health cover, rank 3)

### Missed first place: hybrid + llm

- (tuned) What's the maximum break a student can take from their course? → Deferring a course (wanted How long a deferral can be, rank 2)
- (tuned) Can I tell the agent about his attendance? → Who can see a student's information (wanted Education agents, rank 2)
- (held-out) Can she keep studying while her appeal is being looked at? → Bridging visas (wanted During the process, rank 2)
- (held-out) What paperwork does a student need to put off their start date? → Deferring a course (wanted Applying for a deferral, rank 2)
- (held-out) Her brother rang wanting to know if she's been turning up to class. → Attendance requirement (wanted Who can see a student's information, rank 2)
