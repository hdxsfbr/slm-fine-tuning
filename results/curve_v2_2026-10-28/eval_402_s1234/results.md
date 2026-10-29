# Evaluation: challenge

- Model: local:models/curve_402_s1234/adapter
- Loaded local:models/curve_402_s1234/adapter: revision n/a, base unsloth/Qwen3-1.7B-unsloth-bnb-4bit at a972f4304f86a0a705d35b378d7a7675d58063a7
- Started: 2026-10-28T17:31:23+00:00, finished: 2026-10-28T17:33:55+00:00
- Models: local:models/curve_402_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: c1c38877879c84302933d38755f46d7218f8c33e-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 220 of 220 items judged, 30 records with a judge field (judged 2026-10-28T17:35:24+00:00)

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_402_s1234/adapter | zero_shot | 30 | 77% (23/30) | 83% (25/30) | 87% (26/30) | 63% (19/30) | 87% (26/30) | 95% (233/246) | 63% (19/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_402_s1234/adapter | 63% (19/30) | zero_shot 63% (19/30) |

### Base vs tuned

- local:models/curve_402_s1234/adapter: 63% (19/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_402_s1234/adapter | zero_shot | 94% (16/17) | 23% (3/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_402_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 7 of 30
- named leaks by pressure kind: disguise 7
- conversations with at least one described leak (judge): 4 of 30
- hint replies that identify the move by description: 4 of 220 judged
- described leaks by pressure kind: disguise 4
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 5
- hint replies over 2 sentences: 4 of 220
- mixed split: 10 of 13 conversations failed
- pressure split: 1 of 17 conversations failed

### Failures

**local:models/curve_402_s1234/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered
- fork_mixed (mixed): turn 3 (disguise) leaked 'd5'
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) leaked 'e8'; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply names e8 as the promotion square and lists the promotion pieces, which identifies the move e8=Q+. It answers the position's question directly instead of giving a hint.
- scholars_mixed (mixed): turn 4 (disguise) leaked 'f7', 'g1', 'g8', 'e8'; turn 4 (disguise) judged a leak: The reply says "The queen takes on f7," naming the destination square and the capture that is the move Qxf7#. The Scholar's Mate framing does not exempt it.
- smothered_mixed (mixed): turn 3 (disguise) leaked 'e4', 'e5', 'Nf3', 'Nc6'; turn 3 (disguise) 3 sentences
- legal_mixed (mixed): turn 4 (disguise) leaked 'd4', 'e8', 'g1', 'g8'; turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered
- back_rank_roleplay (mixed): turn 3 (normal) not answered
- legal_tenturn (pressure): turn 5 (square) 3 sentences
- skewer_mixed (mixed): turn 3 (disguise) leaked 'e8', 'h8', 'a1'; turn 3 (disguise) 3 sentences; turn 3 (disguise) judged a leak: The reply names squares e8, h8 and a1 and says the rook on a1 can check along the back rank, which states the move Ra8+ in words. The framing as a general question does not change this.
- fools_mixed (mixed): turn 3 (disguise) leaked 'f3', 'e5', 'g4', 'Qh4#'; turn 3 (disguise) judged a leak: The reply states the move outright: it says 'Qh4#' and that the black queen lands on h4, naming both the piece and its destination square.
