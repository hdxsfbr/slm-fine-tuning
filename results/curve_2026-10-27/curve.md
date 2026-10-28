# Data-efficiency curve

Challenge set, 30 scenarios, zero-shot system prompt, greedy decoding. `All checks` is the code-check pass rate; `Final` adds the judge where it has run.

Rule, fixed before looking (docs/plan.md step 7): the smallest n whose challenge-set pass rate is within 0.05 of the full-N run.

| n | seed | steps | train loss | All checks | Final (judged) | named leaks / hint turns | negatives answered |
|---|---|---|---|---|---|---|---|
| 455 (full) | 1234 | 114 | 1.685 | 67% | n/a | 0 / 220 | 12 / 26 |
| 455 (full) | 3407 | 114 | 1.683 | 63% | 50% | 1 / 220 | 14 / 26 |
| 228 | 1234 | 58 | 2.148 | 50% | n/a | 3 / 220 | 10 / 26 |
| 228 | 3407 | 58 | 2.155 | 47% | n/a | 5 / 220 | 11 / 26 |
| 114 | 1234 | 30 | 2.702 | 45% | n/a | 11 / 212 | 5 / 26 |
| 114 | 3407 | 30 | 2.727 | 29% | n/a | 14 / 202 | 4 / 26 |
| 57 | 1234 | 16 | 3.338 | 46% | n/a | 29 / 204 | 0 / 24 |
| 57 | 3407 | 16 | 3.347 | 45% | n/a | 28 / 212 | 1 / 26 |

All checks: full-N (seed 3407) 63%; mean over seeds per size: 455 65%, 228 48%, 114 37%, 57 46%; sizes within 0.05: 455; smallest: 455.
Final: full-N (seed 3407) 50%; mean over seeds per size: 455 50%; sizes within 0.05: 455; smallest: 455.
