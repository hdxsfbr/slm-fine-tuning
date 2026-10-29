# Data-efficiency curve

Challenge set, 30 scenarios, zero-shot system prompt, greedy decoding. `All checks` is the code-check pass rate per conversation; `Spec adherence` is the per-turn pass rate (checks and judge); `Robustness` is the per-conversation pass rate with every turn holding (checks and judge), the headline. Errored conversations count as failures.

Rule, fixed before looking (docs/plan.md step 7): the smallest n whose challenge-set pass rate is within 0.05 of the full-N run.

| n | seed | steps | train loss | All checks | Spec adherence (turns) | Robustness (judged) | named leaks / hint turns | negatives answered | errors |
|---|---|---|---|---|---|---|---|---|---|
| 455 (full) | 1234 | 114 | 1.685 | 67% | 94% | n/a | 0 / 220 | 12 / 26 | 0 |
| 455 (full) | 3407 | 114 | 1.683 | 63% | 90% | 50% | 1 / 220 | 14 / 26 | 0 |
| 228 | 1234 | 58 | 2.148 | 50% | 88% | n/a | 3 / 220 | 10 / 26 | 0 |
| 228 | 3407 | 58 | 2.155 | 47% | 89% | n/a | 5 / 220 | 11 / 26 | 0 |
| 114 | 1234 | 30 | 2.702 | 43% | 75% | n/a | 11 / 212 | 5 / 26 | 1 |
| 114 | 3407 | 30 | 2.727 | 27% | 63% | n/a | 14 / 202 | 4 / 26 | 2 |
| 57 | 1234 | 16 | 3.338 | 43% | 71% | n/a | 29 / 204 | 0 / 24 | 2 |
| 57 | 3407 | 16 | 3.347 | 43% | 74% | n/a | 28 / 212 | 1 / 26 | 1 |

All checks: full-N (seed 3407) 63%; mean over seeds per size: 455 65%, 228 48%, 114 35%, 57 43%; sizes within 0.05: 455; smallest: 455.
Spec adherence: full-N (seed 3407) 90%; mean over seeds per size: 455 92%, 228 88%, 114 69%, 57 73%; sizes within 0.05: 228, 455; smallest: 228.
Robustness: full-N (seed 3407) 50%; mean over seeds per size: 455 50%; sizes within 0.05: 455; smallest: 455.
