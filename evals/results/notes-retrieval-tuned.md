# Student notes search: keyword vs meaning

Embedding model `text-embedding-nomic-embed-text-v1.5`. 71 hand-written notes (`evals/notes.yaml`) among 1399 routine generated ones. Hybrid uses the policy search's fusion and weights, not tuned for notes. A question can have several right notes: hit@1 is the first note being right, recall@10 how many of the right notes are in the first 10, MAP whether they're near the top. Time: median per question (meaning search is plain Python over every note here).

"agent phrase": `qwen/qwen3-14b` chose search_notes and wrote what to search for (median 2.9 s, not in the times below). "+ 14B": `qwen/qwen3-14b` read the first 20 notes with the staff question and listed the ones that answer it; kept: how many of its listed notes were right (precision) and how many right notes it listed (recall); "nobody": how many of the questions with no answer it listed none for.

## tuned (20 questions)

| Search | hit@1 | recall@10 | MAP | time | kept precision | kept recall | nobody |
|---|---|---|---|---|---|---|---|
| keyword | 35% | 40% | 0.24 | 0 ms | | | |
| meaning | 65% | 66% | 0.56 | 56 ms | | | |
| hybrid | 70% | 66% | 0.53 | 56 ms | | | |
| keyword, agent phrase | 30% | 30% | 0.23 | 0 ms | | | |
| meaning, agent phrase | 60% | 68% | 0.55 | 62 ms | | | |
| hybrid, agent phrase | 60% | 68% | 0.51 | 61 ms | | | |
| meaning + 14B | 90% | 70% | 0.67 | 3283 ms | 51% | 57% | 4/4 |
| hybrid + 14B | 95% | 70% | 0.68 | 3302 ms | 55% | 57% | 3/4 |
| meaning, agent phrase + 14B | 85% | 71% | 0.68 | 3386 ms | 66% | 62% | 4/4 |
| hybrid, agent phrase + 14B | 85% | 71% | 0.68 | 3244 ms | 69% | 62% | 4/4 |

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

### Not perfect: keyword

- (tuned) Who mentioned a part-time job? → first: "Late three times this week, trains on the T1 line."; found 1/6, missed aiko-2, arjun-1, camila-1, kofi-1, quang-2
- (tuned) Which students are having money troubles? → first: "Collected student card."; found 1/4, missed bilal-1, bilal-2, tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 1/6, missed dev-3, oscar-1, uma-1, ximena-1, zara-1
- (tuned) Who's had trouble finding somewhere to live? → first: "Needs to find another way to get to the Penrith campus."; found 0/3, missed emre-1, emre-2, tariq-1
- (tuned) Has anyone lost a family member? → first: "Short on money this month after sending most of his pay to family in Vietnam."; found 0/1, missed gabriel-1
- (tuned) Who's thinking about leaving for another college? → first: "Thinking about switching to TAFE because it's cheaper."; found 1/2, missed lucia-2
- (tuned) Who's been injured? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 0/1, missed nadia-1
- (tuned) Which students have children or a baby on the way? → first: "Asked about the work limits on the student visa."; found 0/2, missed fatima-1, priyanka-1
- (tuned) Who's finding the English in class hard? → first: "Said she's finding the trainer's accent hard to follow in class, asked if there are slides."; found 1/2, missed rania-1
- (tuned) Any complaints about the trainers? → first: "Spoke to the trainer about changing the groups."; found 2/2
- (tuned) Who had something stolen? → first: "Laptop was stolen from her car. Lent her one of the library loan laptops."; found 1/2, missed arjun-2
- (tuned) Has anyone been targeted by a scam? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 1/1
- (tuned) Which students have a parent who is sick back home? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/2, missed uma-1
- (tuned) Who's had transport problems getting to class? → first: "Needs to find another way to get to the Penrith campus."; found 2/4, missed camila-2, gita-1
- (tuned) Who wants to change course? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/1
- (tuned) Who hasn't been answering us? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 1/1
- (tuned) Anyone with a placement coming up? → first: "Missed a tutorial and caught up with the trainer the next day."; found 1/2, missed elif-2
- (tuned) Who wants time off to travel? → first: "Friend's wedding back in Colombia in January, wants 3 weeks off mid-term."; found 1/2, missed felipe-2
- (tuned) Which students are doing really well? → first: "Called to check in; says the course is going well."; found 0/1, missed sven-1
- (tuned) Is anyone being picked on by classmates? → first: "Landlord is selling the house, has to be out by the end of the month and hasn't found anywhere yet."; found 0/2, missed ximena-1, ximena-2

### Not perfect: meaning

- (tuned) Who mentioned a part-time job? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 3/6, missed arjun-1, camila-1, quang-2
- (tuned) Which students are having money troubles? → first: "Referred by Unity Study Abroad Delhi (Divya Nair). Interested in the Certificate III in Individual Support."; found 0/4, missed bilal-1, bilal-2, quang-1, tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 4/6, missed dev-3, ximena-1
- (tuned) Who's had trouble finding somewhere to live? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/3, missed emre-2, tariq-1
- (tuned) Who's thinking about leaving for another college? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/2, missed lucia-2
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2
- (tuned) Who's had transport problems getting to class? → first: "Doing Uber Eats in the evenings, says that's why she's so tired in morning classes."; found 1/4, missed camila-2, gita-1, gita-2
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2
- (tuned) Which students are doing really well? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 1/1
- (tuned) Is anyone being picked on by classmates? → first: "Two young kids, childcare pick-up at 3 clashes with the afternoon class. Moved her to the morning group."; found 1/2, missed ximena-2

### Not perfect: hybrid

- (tuned) Who mentioned a part-time job? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 3/6, missed arjun-1, camila-1, quang-2
- (tuned) Which students are having money troubles? → first: "Referred by Unity Study Abroad Delhi (Divya Nair). Interested in the Certificate III in Individual Support."; found 0/4, missed bilal-1, bilal-2, quang-1, tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 4/6, missed dev-3, ximena-1
- (tuned) Who's had trouble finding somewhere to live? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 1/3, missed emre-2, tariq-1
- (tuned) Has anyone lost a family member? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/1
- (tuned) Who's thinking about leaving for another college? → first: "Thinking about switching to TAFE because it's cheaper."; found 1/2, missed lucia-2
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2
- (tuned) Who's had transport problems getting to class? → first: "Car broke down, couldn't get to campus Monday."; found 1/4, missed camila-2, gita-1, gita-2
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2
- (tuned) Which students are doing really well? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 1/1
- (tuned) Is anyone being picked on by classmates? → first: "Two young kids, childcare pick-up at 3 clashes with the afternoon class. Moved her to the morning group."; found 1/2, missed ximena-2

### Not perfect: keyword, agent phrase

- (tuned) Who mentioned a part-time job? → first: "Late three times this week, trains on the T1 line."; found 1/6, missed aiko-2, arjun-1, camila-1, kofi-1, quang-2
- (tuned) Which students are having money troubles? → first: "Short on money this month after sending most of his pay to family in Vietnam."; found 1/4, missed bilal-1, bilal-2, tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Hasn't replied to three emails or two calls about his attendance."; found 0/6, missed dev-1, dev-3, oscar-1, uma-1, ximena-1, zara-1
- (tuned) Who's had trouble finding somewhere to live? → first: "Needs to find another way to get to the Penrith campus."; found 0/3, missed emre-1, emre-2, tariq-1
- (tuned) Has anyone lost a family member? → first: "Short on money this month after sending most of his pay to family in Vietnam."; found 0/1, missed gabriel-1
- (tuned) Who's thinking about leaving for another college? → first: "Needs to find another way to get to the Penrith campus."; found 0/2, missed lucia-1, lucia-2
- (tuned) Who's been injured? → first: "nothing"; found 0/1, missed nadia-1
- (tuned) Which students have children or a baby on the way? → first: "Asked about the work limits on the student visa."; found 0/2, missed fatima-1, priyanka-1
- (tuned) Who's finding the English in class hard? → first: "Said she's finding the trainer's accent hard to follow in class, asked if there are slides."; found 1/2, missed rania-1
- (tuned) Any complaints about the trainers? → first: "Spoke to the trainer about changing the groups."; found 2/2
- (tuned) Who had something stolen? → first: "Laptop was stolen from her car. Lent her one of the library loan laptops."; found 1/2, missed arjun-2
- (tuned) Which students have a parent who is sick back home? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/2, missed uma-1
- (tuned) Who's had transport problems getting to class? → first: "nothing"; found 0/4, missed camila-2, gita-1, gita-2, viktor-1
- (tuned) Who wants to change course? → first: "Asked about changing to the evening timetable."; found 0/1, missed yusuf-2
- (tuned) Who hasn't been answering us? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 1/1
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2
- (tuned) Who wants time off to travel? → first: "Late three times this week, trains on the T1 line."; found 1/2, missed felipe-2
- (tuned) Which students are doing really well? → first: "Called to check in; says the course is going well."; found 0/1, missed sven-1
- (tuned) Is anyone being picked on by classmates? → first: "Landlord is selling the house, has to be out by the end of the month and hasn't found anywhere yet."; found 0/2, missed ximena-1, ximena-2

### Not perfect: meaning, agent phrase

- (tuned) Who mentioned a part-time job? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 5/6, missed quang-2
- (tuned) Which students are having money troubles? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 3/4, missed tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Gets panic attacks before exams, asked for a quiet room for assessments. Approved."; found 4/6, missed dev-1, dev-3
- (tuned) Who's had trouble finding somewhere to live? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/3, missed emre-1, emre-2
- (tuned) Who's thinking about leaving for another college? → first: "A classmate says he's gone back to China, nothing official from him."; found 0/2, missed lucia-1, lucia-2
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2
- (tuned) Who's had transport problems getting to class? → first: "Referred by EduBridge Education Services Chiang Mai (Chaiwat Chaiyaporn). Interested in the Certificate III in Light Vehicle Mechanical Technology."; found 0/4, missed camila-2, gita-1, gita-2, viktor-1
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2
- (tuned) Anyone with a placement coming up? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/2, missed elif-2
- (tuned) Which students are doing really well? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 1/1
- (tuned) Is anyone being picked on by classmates? → first: "Two young kids, childcare pick-up at 3 clashes with the afternoon class. Moved her to the morning group."; found 1/2, missed ximena-2

### Not perfect: hybrid, agent phrase

- (tuned) Who mentioned a part-time job? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 5/6, missed quang-2
- (tuned) Which students are having money troubles? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 3/4, missed tariq-2
- (tuned) Anyone been really stressed or anxious lately? → first: "Gets panic attacks before exams, asked for a quiet room for assessments. Approved."; found 4/6, missed dev-1, dev-3
- (tuned) Who's had trouble finding somewhere to live? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/3, missed emre-1, emre-2
- (tuned) Has anyone lost a family member? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 1/1
- (tuned) Who's thinking about leaving for another college? → first: "A classmate says he's gone back to China, nothing official from him."; found 0/2, missed lucia-1, lucia-2
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2
- (tuned) Who's had transport problems getting to class? → first: "Referred by EduBridge Education Services Chiang Mai (Chaiwat Chaiyaporn). Interested in the Certificate III in Light Vehicle Mechanical Technology."; found 0/4, missed camila-2, gita-1, gita-2, viktor-1
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2
- (tuned) Which students are doing really well? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 1/1
- (tuned) Is anyone being picked on by classmates? → first: "Two young kids, childcare pick-up at 3 clashes with the afternoon class. Moved her to the morning group."; found 1/2, missed ximena-2

### Not perfect: meaning + 14B

- (tuned) Who mentioned a part-time job? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 4/6, missed arjun-1, quang-2; kept 4
- (tuned) Which students are having money troubles? → first: "Rang to say he can't pay the term 3 instalment on time, his dad's business in Lahore has gone under."; found 1/4, missed bilal-2, quang-1, tariq-2; kept 1
- (tuned) Anyone been really stressed or anxious lately? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 4/6, missed dev-3, ximena-1; kept 6
- (tuned) Who's had trouble finding somewhere to live? → first: "Lease ended and the new place fell through, staying on a mate's couch for now."; found 2/3, missed emre-2; kept 2
- (tuned) Who's thinking about leaving for another college? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/2, missed lucia-2; kept 4
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1; kept 1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2; kept 2
- (tuned) Who's had transport problems getting to class? → first: "Car broke down, couldn't get to campus Monday."; found 1/4, missed camila-2, gita-1, gita-2; kept 1
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2; kept 4
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2; kept 7
- (tuned) Is anyone being picked on by classmates? → first: "Says the others in her group leave her out and make comments about her accent. Very upset."; found 1/2, missed ximena-2; kept 1

### Not perfect: hybrid + 14B

- (tuned) Who mentioned a part-time job? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 4/6, missed arjun-1, quang-2; kept 3
- (tuned) Which students are having money troubles? → first: "Rang to say he can't pay the term 3 instalment on time, his dad's business in Lahore has gone under."; found 1/4, missed bilal-2, quang-1, tariq-2; kept 1
- (tuned) Anyone been really stressed or anxious lately? → first: "Looked really down today, told me he hasn't been sleeping. Gave him the counselling service details."; found 4/6, missed dev-3, ximena-1; kept 5
- (tuned) Who's had trouble finding somewhere to live? → first: "Lease ended and the new place fell through, staying on a mate's couch for now."; found 2/3, missed emre-2; kept 2
- (tuned) Who's thinking about leaving for another college? → first: "Thinking about switching to TAFE because it's cheaper."; found 1/2, missed lucia-2; kept 4
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1; kept 1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2; kept 2
- (tuned) Who's had transport problems getting to class? → first: "Car broke down, couldn't get to campus Monday."; found 1/4, missed camila-2, gita-1, gita-2; kept 1
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2; kept 4
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2; kept 7
- (tuned) Is anyone being picked on by classmates? → first: "Says the others in her group leave her out and make comments about her accent. Very upset."; found 1/2, missed ximena-2; kept 1
- (tuned) Has anyone been arrested? (no answer) → kept: Got a speeding fine, asked if it affects his visa.

### Not perfect: meaning, agent phrase + 14B

- (tuned) Who mentioned a part-time job? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 5/6, missed quang-2; kept 4
- (tuned) Which students are having money troubles? → first: "Rang to say he can't pay the term 3 instalment on time, his dad's business in Lahore has gone under."; found 3/4, missed tariq-2; kept 2
- (tuned) Anyone been really stressed or anxious lately? → first: "Gets panic attacks before exams, asked for a quiet room for assessments. Approved."; found 4/6, missed dev-1, dev-3; kept 7
- (tuned) Who's had trouble finding somewhere to live? → first: "Landlord is selling the house, has to be out by the end of the month and hasn't found anywhere yet."; found 2/3, missed emre-2; kept 2
- (tuned) Who's thinking about leaving for another college? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 0/2, missed lucia-1, lucia-2; kept 1
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1; kept 1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2; kept 2
- (tuned) Who's had transport problems getting to class? → first: "Doing Uber Eats in the evenings, says that's why she's so tired in morning classes."; found 1/4, missed gita-1, gita-2, viktor-1; kept 2
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2; kept 2
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2; kept 1
- (tuned) Is anyone being picked on by classmates? → first: "Says the others in her group leave her out and make comments about her accent. Very upset."; found 1/2, missed ximena-2; kept 1

### Not perfect: hybrid, agent phrase + 14B

- (tuned) Who mentioned a part-time job? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 5/6, missed quang-2; kept 4
- (tuned) Which students are having money troubles? → first: "Short on money this month after sending most of his pay to family in Vietnam."; found 3/4, missed tariq-2; kept 2
- (tuned) Anyone been really stressed or anxious lately? → first: "Gets panic attacks before exams, asked for a quiet room for assessments. Approved."; found 4/6, missed dev-1, dev-3; kept 7
- (tuned) Who's had trouble finding somewhere to live? → first: "Landlord is selling the house, has to be out by the end of the month and hasn't found anywhere yet."; found 2/3, missed emre-2; kept 2
- (tuned) Who's thinking about leaving for another college? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 0/2, missed lucia-1, lucia-2; kept 1
- (tuned) Which students have children or a baby on the way? → first: "Pregnant, due in April. Wants to know her options for finishing the course."; found 1/2, missed priyanka-1; kept 1
- (tuned) Any complaints about the trainers? → first: "Complained that the trainer for BSB50120 keeps cancelling classes at short notice."; found 1/2, missed ivan-2; kept 2
- (tuned) Who's had transport problems getting to class? → first: "Doing Uber Eats in the evenings, says that's why she's so tired in morning classes."; found 1/4, missed gita-1, gita-2, viktor-1; kept 2
- (tuned) Who wants to change course? → first: "Spoke to the trainer about changing the groups."; found 0/1, missed yusuf-2; kept 3
- (tuned) Anyone with a placement coming up? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 1/2, missed elif-2; kept 1
- (tuned) Is anyone being picked on by classmates? → first: "Says the others in her group leave her out and make comments about her accent. Very upset."; found 1/2, missed ximena-2; kept 1
