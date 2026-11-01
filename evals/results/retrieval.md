# Policy search: retrieval eval

Embedding model `text-embedding-nomic-embed-text-v1.5`. Rerankers re-order the hybrid search's top 10: llm (`qwen/qwen3-14b`), minilm (`cross-encoder/ms-marco-MiniLM-L6-v2:onnx/model.onnx`), mxbai (`mixedbread-ai/mxbai-rerank-xsmall-v1:onnx/model.onnx`), bge (`Xenova/bge-reranker-base:onnx/model_int8.onnx`).

Two question sets: `retrieval.yaml` (32, which the keyword weight was tuned on) and `retrieval_holdout.yaml` (held out: nothing is tuned on it). policy@1: the right section's policy came first, so it was in what the assistant is given. Time: median per question.

## tuned (32 questions)

| Search | hit@1 | hit@3 | MRR | policy@1 | time |
|---|---|---|---|---|---|
| keyword | 59% | 88% | 0.71 | 69% | 0 ms |
| meaning | 78% | 91% | 0.84 | 84% | 19 ms |
| hybrid | 91% | 94% | 0.92 | 94% | 27 ms |
| hybrid + llm | 91% | 97% | 0.94 | 100% | 5493 ms |
| hybrid + minilm | 88% | 91% | 0.91 | 91% | 70 ms |
| hybrid + mxbai | 81% | 94% | 0.87 | 88% | 161 ms |
| hybrid + bge | 78% | 94% | 0.85 | 88% | 257 ms |

## held-out (32 questions)

| Search | hit@1 | hit@3 | MRR | policy@1 | time |
|---|---|---|---|---|---|
| keyword | 41% | 66% | 0.53 | 56% | 0 ms |
| meaning | 59% | 88% | 0.75 | 72% | 26 ms |
| hybrid | 66% | 88% | 0.76 | 75% | 25 ms |
| hybrid + llm | 91% | 97% | 0.94 | 94% | 5923 ms |
| hybrid + minilm | 75% | 91% | 0.82 | 84% | 72 ms |
| hybrid + mxbai | 75% | 88% | 0.84 | 81% | 158 ms |
| hybrid + bge | 56% | 91% | 0.73 | 72% | 261 ms |

### Missed first place: hybrid

- (tuned) Student wants to quit, does she get any money back? → If the college can't deliver the course (wanted Refunds when a student withdraws, rank 8)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 3)
- (tuned) Her mum called asking about her grades, can I tell her? → Referrals (wanted Who can see a student's information, rank None)
- (held-out) If she gets credit for three units, does she pay less? → Recognition of prior learning (wanted Effect on the course, rank 3)
- (held-out) What paperwork does a student need to put off their start date? → Keeping details up to date (wanted Applying for a deferral, rank 10)
- (held-out) What has to happen before an applicant's place is locked in? → When to apply (wanted Letter of offer, rank 3)
- (held-out) Someone rang claiming to be Liam, what should I ask before talking about his record? → Referrals (wanted Checking identity, rank 4)
- (held-out) A 17-year-old wants to rent a flat with friends, is that allowed? → Who can see a student's information (wanted Students under 18, rank 2)
- (held-out) A student can't get into Moodle, who sorts that out? → Raising a concern informally (wanted Login and portal help, rank 10)
- (held-out) We said no to her transfer, can she challenge that? → The six-month rule (wanted If the request is refused, rank 3)
- (held-out) Can she keep coming to class while she waits for her new visa? → Visa extensions and new visas (wanted Bridging visas, rank 2)
- (held-out) Can we give an agent his attendance report? → Reporting to the government (wanted Education agents, rank 2)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → When attendance drops (wanted Who can see a student's information, rank None)
- (held-out) Her insurance runs out next month, do we chase that? → The six-month rule (wanted Health cover, rank 2)

### Missed first place: hybrid + llm

- (tuned) What's the maximum break a student can take from their course? → Deferring a course (wanted How long a deferral can be, rank 2)
- (tuned) Her mum called asking about her grades, can I tell her? → Correcting records (wanted Who can see a student's information, rank None)
- (tuned) Can I tell the agent about his attendance? → Who can see a student's information (wanted Education agents, rank 2)
- (held-out) Can she keep studying while her appeal is being looked at? → Bridging visas (wanted During the process, rank 2)
- (held-out) What paperwork does a student need to put off their start date? → Deferring a course (wanted Applying for a deferral, rank 2)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → Attendance requirement (wanted Who can see a student's information, rank None)

### Missed first place: hybrid + minilm

- (tuned) How many hours a week can international students work? → Attendance requirement (wanted Working while studying, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 4)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 4)
- (tuned) Her mum called asking about her grades, can I tell her? → Correcting records (wanted Who can see a student's information, rank None)
- (held-out) What paperwork does a student need to put off their start date? → Visa extensions and new visas (wanted Applying for a deferral, rank 9)
- (held-out) Student says she's leaving the college, what's the first step? → Changing course (wanted Withdrawing from a course, rank 3)
- (held-out) What has to happen before an applicant's place is locked in? → When to apply (wanted Letter of offer, rank 3)
- (held-out) Do we pass enrolment details on to the Department? → Confirmation of Enrolment (wanted Sharing with government, rank 6)
- (held-out) Her date of birth is wrong in our system, can she get it fixed? → Checking identity (wanted Correcting records, rank 2)
- (held-out) A student can't get into Moodle, who sorts that out? → Raising a concern informally (wanted Login and portal help, rank 3)
- (held-out) His course end date moved and his visa runs out first, what now? → Health cover (wanted Visa extensions and new visas, rank 3)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → Correcting records (wanted Who can see a student's information, rank None)

### Missed first place: hybrid + mxbai

- (tuned) Can Sofia pick up extra shifts at her café during the semester? → Orientation (wanted Working while studying, rank 3)
- (tuned) What do we do when a student's attendance falls under 80 percent? → Reporting to the government (wanted When attendance drops, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 2)
- (tuned) What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 4)
- (tuned) Her mum called asking about her grades, can I tell her? → Reporting to the government (wanted Who can see a student's information, rank None)
- (tuned) Can I tell the agent about his attendance? → Sharing with government (wanted Education agents, rank 3)
- (held-out) What paperwork does a student need to put off their start date? → Deferring a course (wanted Applying for a deferral, rank 4)
- (held-out) Student says she's leaving the college, what's the first step? → Changing course (wanted Withdrawing from a course, rank 2)
- (held-out) He wants to switch from business to IT here, how does that work? → Login and portal help (wanted Changing course, rank 4)
- (held-out) The college is shutting down the cookery course, what happens to the students' money? → Withdrawing from a course (wanted If the college can't deliver the course, rank 2)
- (held-out) Her date of birth is wrong in our system, can she get it fixed? → Checking identity (wanted Correcting records, rank 2)
- (held-out) Can we give an agent his attendance report? → Reporting to the government (wanted Education agents, rank 4)
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → Attendance requirement (wanted Who can see a student's information, rank None)
- (held-out) Her insurance runs out next month, do we chase that? → Payment plans (wanted Health cover, rank 2)

### Missed first place: hybrid + bge

- (tuned) How many hours a week can international students work? → Attendance requirement (wanted Working while studying, rank 2)
- (tuned) Can Sofia pick up extra shifts at her café during the semester? → Orientation (wanted Working while studying, rank 9)
- (tuned) What do we do when a student's attendance falls under 80 percent? → Reporting to the government (wanted When attendance drops, rank 2)
- (tuned) Student wants to quit, does she get any money back? → Withdrawing from a course (wanted Refunds when a student withdraws, rank 3)
- (tuned) What's the maximum break a student can take from their course? → Deferring a course (wanted How long a deferral can be, rank 2)
- (tuned) When do we give a release letter? → Asking for a release letter (wanted When a release letter is given, rank 3)
- (tuned) Her mum called asking about her grades, can I tell her? → Reporting to the government (wanted Who can see a student's information, rank None)
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
- (held-out) Her dad keeps emailing asking how she's doing in class. What can I say? → Making a formal complaint or appeal (wanted Who can see a student's information, rank None)
- (held-out) Can a student work full time over the summer holidays? → Deferring a course (wanted Working while studying, rank 2)
