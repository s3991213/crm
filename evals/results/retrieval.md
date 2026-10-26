# Policy search: retrieval eval

32 staff questions (`evals/retrieval.yaml`), embedding model `text-embedding-nomic-embed-text-v1.5`.

| Search | hit@1 | hit@3 | MRR |
|---|---|---|---|
| keyword | 59% | 88% | 0.71 |
| meaning | 78% | 91% | 0.84 |
| hybrid | 91% | 94% | 0.92 |

The assistant is given the top 3. Questions where hybrid search didn't rank the right section first:

- Student wants to quit, does she get any money back? → If the college can't deliver the course (wanted Refunds when a student withdraws, rank 8)
- What's the maximum break a student can take from their course? → Working while studying (wanted How long a deferral can be, rank 3)
- Her mum called asking about her grades, can I tell her? → Referrals (wanted Who can see a student's information, rank None)
