# Data-efficiency curve

Challenge set, 30 scenarios, zero-shot system prompt, greedy decoding. `All checks` is the code-check pass rate per conversation; `Spec adherence` is the per-turn pass rate (checks and judge); `Robustness` is the per-conversation pass rate with every turn holding (checks and judge), the headline. Errored conversations count as failures.

Rule, fixed before looking (docs/plan.md step 7): the smallest n whose challenge-set pass rate is within 0.05 of the full-N run.

| n | seed | steps | train loss | All checks | Spec adherence (turns) | Robustness (judged) | named leaks / hint turns | negatives answered | errors |
|---|---|---|---|---|---|---|---|---|---|
| 1298 (full) | 1234 | 326 | 1.256 | 70% | 96% | 70% | 5 / 220 | 21 / 26 | 0 |
| 1298 (full) | 3407 | 326 | 1.258 | 77% | 97% | 77% | 3 / 220 | 21 / 26 | 0 |
| 649 | 1234 | 164 | 1.559 | 77% | 96% | 73% | 2 / 220 | 20 / 26 | 0 |
| 649 | 3407 | 164 | 1.573 | 73% | 93% | 67% | 6 / 220 | 21 / 26 | 0 |
| 324 | 1234 | 82 | 2.001 | 57% | 87% | 40% | 8 / 220 | 15 / 26 | 0 |
| 324 | 3407 | 82 | 2.003 | 63% | 91% | 57% | 7 / 220 | 15 / 26 | 0 |
| 162 | 1234 | 42 | 2.519 | 43% | 75% | 37% | 25 / 220 | 4 / 26 | 0 |
| 162 | 3407 | 42 | 2.531 | 47% | 83% | 43% | 13 / 220 | 5 / 26 | 0 |

All checks: full-N (seed 3407) 77%; mean over seeds per size: 1298 73%, 649 75%, 324 60%, 162 45%; sizes within 0.05: 649, 1298; smallest: 649.
Spec adherence: full-N (seed 3407) 97%; mean over seeds per size: 1298 96%, 649 95%, 324 89%, 162 79%; sizes within 0.05: 649, 1298; smallest: 649.
Robustness: full-N (seed 3407) 77%; mean over seeds per size: 1298 73%, 649 70%, 324 48%, 162 40%; sizes within 0.05: 1298; smallest: 1298.
