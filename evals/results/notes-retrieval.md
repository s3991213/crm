# Student notes search: keyword vs meaning

Embedding model `text-embedding-nomic-embed-text-v1.5`. 71 hand-written notes (`evals/notes.yaml`) among 1399 routine generated ones. Hybrid uses the policy search's fusion and weights, not tuned for notes. A question can have several right notes: hit@1 is the first note being right, recall@10 how many of the right notes are in the first 10, MAP whether they're near the top. Time: median per question (meaning search is plain Python over every note here).

## tuned (20 questions)

| Search | hit@1 | recall@10 | MAP | time |
|---|---|---|---|---|
| keyword | 35% | 40% | 0.24 | 0 ms |
| meaning | 65% | 66% | 0.56 | 59 ms |
| hybrid | 70% | 66% | 0.53 | 65 ms |

## held-out (15 questions)

| Search | hit@1 | recall@10 | MAP | time |
|---|---|---|---|---|
| keyword | 40% | 45% | 0.33 | 0 ms |
| meaning | 67% | 72% | 0.56 | 61 ms |
| hybrid | 60% | 72% | 0.53 | 65 ms |

## Can a score cut-off say "nobody"?

Best meaning score of a right note, over the 35 answered questions: lowest 0.548, median 0.627, highest 0.738.

| Question with no answer | best score | best note |
|---|---|---|
| Who's getting married? | 0.587 | Friend's wedding back in Colombia in January, wants 3 weeks off mid-term. |
| Who mentioned joining the army? | 0.602 | Referred by Bright Future Overseas Education Chittagong (Sadia Miah). Interested in the IELTS Preparation. |
| Has anyone been arrested? | 0.567 | Got a speeding fine, asked if it affects his visa. |
| Which students have a dog? | 0.665 | Top mark in the class for the marketing project, trainer has nominated him for the student award. |

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
- (held-out) Who's doing food delivery? → first: "Asked whether she can do her assessments online from India."; found 1/1
- (held-out) Any students who are homesick? → first: "Asked if we know of any cheap rooms near campus."; found 2/2
- (held-out) Which students might drop out? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/5, missed chen-2, lucia-1, lucia-2, oscar-1
- (held-out) Who works in a kitchen or a cafe? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 2/3, missed aiko-2
- (held-out) Who's had a family emergency overseas? → first: "Short on money this month after sending most of his pay to family in Vietnam."; found 1/3, missed gabriel-1, jia-1
- (held-out) Anyone with visa worries? → first: "Rent went up $80 a week, worried about covering it."; found 0/5, missed beatriz-1, minh-1, minh-2, viktor-2, wen-2
- (held-out) Who has their partner here with them? → first: "Reminded them to renew their OSHC, which ends on 10 November 2026."; found 0/1, missed beatriz-1
- (held-out) Who couldn't log in to the online systems? → first: "Car broke down, couldn't get to campus Monday."; found 0/2, missed arjun-2, hana-2
- (held-out) Is anyone in trouble with the police? → first: "Starts her nursing placement at Westmead in October, needs a police check and vaccination records."; found 0/1, missed viktor-2
- (held-out) Who had a crash? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 0/1, missed gita-1
- (held-out) Anyone seeing the counsellor? → first: "Followed up, he's seen the counsellor twice and seems brighter."; found 1/2, missed dev-1
- (held-out) Who's missed classes for a medical reason? → first: "Missed the Tuesday assessment, says he forgot."; found 0/2, missed nadia-1, nadia-2

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
- (held-out) Who's doing food delivery? → first: "Referred by Northstar Education Services Surabaya (Dewi Setiawan). Interested in the Certificate IV in Kitchen Management."; found 1/1
- (held-out) Any students who are homesick? → first: "Very homesick, says he cries most nights and is thinking of going back to Sweden."; found 1/2, missed oscar-2
- (held-out) Which students might drop out? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/5, missed chen-2, lucia-1, lucia-2, oscar-1
- (held-out) Who works in a kitchen or a cafe? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 2/3, missed aiko-2
- (held-out) Who's had a family emergency overseas? → first: "Mum has cancer back in Malaysia, wants to go home for a few months."; found 2/3, missed gabriel-1
- (held-out) Who needed special arrangements for exams? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 0/2, missed nadia-1, zara-1
- (held-out) Anyone with visa worries? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/5, missed beatriz-1, minh-2, viktor-2, wen-2
- (held-out) Is anyone in trouble with the police? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/1
- (held-out) Who's sending money home? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/1
- (held-out) Who's missed classes for a medical reason? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 1/2, missed nadia-2

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
- (held-out) Any students who are homesick? → first: "Very homesick, says he cries most nights and is thinking of going back to Sweden."; found 1/2, missed oscar-2
- (held-out) Which students might drop out? → first: "Her boss has offered her a full-time position, she's considering dropping out of the course."; found 1/5, missed chen-2, lucia-1, lucia-2, oscar-1
- (held-out) Who works in a kitchen or a cafe? → first: "Working as a kitchen hand at a pub in Parramatta, Thurs-Sun nights."; found 2/3, missed aiko-2
- (held-out) Who's had a family emergency overseas? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 2/3, missed gabriel-1
- (held-out) Who needed special arrangements for exams? → first: "Referred by Bright Future Education Karachi (Sana Sheikh). Interested in the IELTS Preparation."; found 0/2, missed nadia-1, zara-1
- (held-out) Anyone with visa worries? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/5, missed beatriz-1, minh-2, viktor-2, wen-2
- (held-out) Who couldn't log in to the online systems? → first: "Asked whether she can do her assessments online from India."; found 2/2
- (held-out) Is anyone in trouble with the police? → first: "Called to check in; says the course is going well."; found 1/1
- (held-out) Who had a crash? → first: "Dad had a heart attack in Chennai, she's very distressed. Approved 2 weeks compassionate leave."; found 1/1
- (held-out) Who's sending money home? → first: "Got a call from someone claiming to be Home Affairs asking for money to fix his visa. Told him it's a scam and not to pay."; found 1/1
- (held-out) Who's missed classes for a medical reason? → first: "Doing Uber Eats in the evenings, says that's why she's so tired in morning classes."; found 1/2, missed nadia-2
