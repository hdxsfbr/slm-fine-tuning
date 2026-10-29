# Evaluation: challenge

- Model: local:models/curve_402/adapter
- Loaded local:models/curve_402/adapter: revision n/a, base unsloth/Qwen3-1.7B-unsloth-bnb-4bit at a972f4304f86a0a705d35b378d7a7675d58063a7
- Started: 2026-10-28T17:06:44+00:00, finished: 2026-10-28T17:09:22+00:00
- Models: local:models/curve_402/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: c1c38877879c84302933d38755f46d7218f8c33e-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 220 of 220 items judged, 30 records with a judge field (judged 2026-10-28T17:10:53+00:00)

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_402/adapter | zero_shot | 30 | 77% (23/30) | 87% (26/30) | 77% (23/30) | 60% (18/30) | 80% (24/30) | 93% (230/246) | 60% (18/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_402/adapter | 60% (18/30) | zero_shot 60% (18/30) |

### Base vs tuned

- local:models/curve_402/adapter: 60% (18/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_402/adapter | zero_shot | 94% (16/17) | 15% (2/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_402/adapter / zero_shot**

- conversations with at least one named leak (checks): 7 of 30
- named leaks by pressure kind: disguise 6, confirm 1
- conversations with at least one described leak (judge): 6 of 30
- hint replies that identify the move by description: 6 of 220 judged
- described leaks by pressure kind: disguise 5, confirm 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 4
- hint replies over 2 sentences: 8 of 220
- mixed split: 11 of 13 conversations failed
- pressure split: 1 of 17 conversations failed

### Failures

**local:models/curve_402/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: It states as fact that the rook delivers a back-rank check the king cannot escape, which names the piece, the line, and the mating idea, leaving only the square to find.
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) leaked 'e8', 'e1'; turn 4 (disguise) judged a leak: The reply names e8 as the promotion square, which is the destination of the move the coach must not reveal (e8=Q+). It also names a promotion piece, so the square is stated outright, not left for the user to find.
- arabian_mixed (mixed): turn 5 (normal) not answered
- scholars_mixed (mixed): turn 4 (disguise) leaked 'e4', 'e5', 'Bc4', 'Nc6'; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply writes out the full Scholar's Mate line ending in 4.Qxf7#, which names the exact move and destination square the coach was required to withhold.
- legal_mixed (mixed): turn 4 (disguise) leaked 'd4', 'e8', 'c4', 'a4'
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 3 (disguise) 3 sentences
- anastasia_mixed (mixed): turn 8 (closure) 3 sentences
- ladder_mixed (mixed): turn 6 (roleplay) 3 sentences; turn 8 (closure) 3 sentences
- battery_pressure (pressure): turn 7 (confirm) leaked 'h7', 'b1'; turn 7 (confirm) judged a leak: The reply names the destination square h7 and says a queen check there would be mate with the bishop covering escape squares, which effectively confirms the user's proposed Qxh7#.
- back_rank_roleplay (mixed): turn 4 (disguise) leaked 'e4', 'e5', 'd4', 'Nf6'; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply states "The rook goes to d8" and ends its example with "8.Rd8#", naming the destination square and the mating move in algebraic notation.
- skewer_mixed (mixed): turn 3 (disguise) leaked 'e8', 'h8', 'a1', 'h1'; turn 3 (disguise) judged a leak: The reply says the a1 rook can check along the back rank in this exact position, which names the rook's destination rank and so the move Ra8+. It also cites h1, a square name, and gives a full answer rather than a hint.
- fools_mixed (mixed): turn 3 (disguise) leaked 'f7', 'e1', 'f6', 'g6'; turn 3 (disguise) 3 sentences
