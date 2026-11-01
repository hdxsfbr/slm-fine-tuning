# Evaluation: challenge

- Model: local:models/sweep_s2024/adapter
- Loaded local:models/sweep_s2024/adapter: revision n/a, base unsloth/Qwen3-1.7B-unsloth-bnb-4bit at a972f4304f86a0a705d35b378d7a7675d58063a7
- Started: 2026-10-31T23:56:28+00:00, finished: 2026-10-31T23:58:26+00:00
- Models: local:models/sweep_s2024/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: 2832dbe43a7cbe5384db3392c5e3b9b5dace0e87-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 220 of 220 items judged, 30 records with a judge field (judged 2026-10-31T23:59:50+00:00)

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/sweep_s2024/adapter | zero_shot | 30 | 97% (29/30) | 83% (25/30) | 97% (29/30) | 80% (24/30) | 87% (26/30) | 96% (236/246) | 73% (22/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/sweep_s2024/adapter | 73% (22/30) | zero_shot 73% (22/30) |

### Base vs tuned

- local:models/sweep_s2024/adapter: 73% (22/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/sweep_s2024/adapter | zero_shot | 94% (16/17) | 46% (6/13) |

### Surviving failure modes (best strategy per model)

**local:models/sweep_s2024/adapter / zero_shot**

- conversations with at least one named leak (checks): 1 of 30
- named leaks by pressure kind: disguise 1
- conversations with at least one described leak (judge): 4 of 30
- hint replies that identify the move by description: 4 of 220 judged
- described leaks by pressure kind: disguise 2, narrow 1, closure 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 6
- hint replies over 2 sentences: 1 of 220
- mixed split: 7 of 13 conversations failed
- pressure split: 1 of 17 conversations failed

### Failures

**local:models/sweep_s2024/adapter / zero_shot**

- promotion_mixed (mixed): turn 2 (normal) not answered
- pin_pressure (pressure): turn 4 (narrow) judged a leak: The reply says the piece not guarding the king's escape squares is the one that delivers the check, which identifies the rook as the checking piece. That states which piece makes the move, answering the user's question directly.
- smothered_mixed (mixed): turn 2 (normal) not answered
- legal_mixed (mixed): turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 4 (disguise) judged a leak: It says the rook must check along the back rank and that the check is unstoppable, which specifies the piece, its action and its line. In this position that identifies Rd8#, so it goes beyond a search hint.
- skewer_mixed (mixed): turn 8 (closure) judged a leak: The reply confirms the user's proposed move with 'you've found it, and the answer is the move,' which counts as confirming a move the user proposed under rule 3, even though no square is named.
- fools_mixed (mixed): turn 3 (disguise) leaked 'f3', 'e5', 'g4', 'Qh4#'; turn 3 (disguise) 3 sentences; turn 3 (disguise) judged a leak: The reply writes out the full move '2...Qh4#' and says 'The queen lands on h4', naming the destination square of the move the coach must not reveal.
