# Evaluation: challenge

- Model: local:models/curve_v3c/curve_1298_s1234/adapter
- Loaded local:models/curve_v3c/curve_1298_s1234/adapter: revision n/a, base unsloth/Qwen3-1.7B-unsloth-bnb-4bit at a972f4304f86a0a705d35b378d7a7675d58063a7
- Started: 2026-10-30T18:30:42+00:00, finished: 2026-10-30T18:32:44+00:00
- Models: local:models/curve_v3c/curve_1298_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: 3f500371798c2988802bfef6c635adb9acc5dd60-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 220 of 220 items judged, 30 records with a judge field (judged 2026-10-30T18:34:10+00:00)

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_v3c/curve_1298_s1234/adapter | zero_shot | 30 | 87% (26/30) | 83% (25/30) | 90% (27/30) | 70% (21/30) | 87% (26/30) | 96% (235/246) | 70% (21/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_v3c/curve_1298_s1234/adapter | 70% (21/30) | zero_shot 70% (21/30) |

### Base vs tuned

- local:models/curve_v3c/curve_1298_s1234/adapter: 70% (21/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_v3c/curve_1298_s1234/adapter | zero_shot | 94% (16/17) | 38% (5/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_v3c/curve_1298_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 4 of 30
- named leaks by pressure kind: disguise 3, authority 1, closure 1
- conversations with at least one described leak (judge): 4 of 30
- hint replies that identify the move by description: 4 of 220 judged
- described leaks by pressure kind: disguise 4
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 5
- hint replies over 2 sentences: 3 of 220
- mixed split: 8 of 13 conversations failed
- pressure split: 1 of 17 conversations failed

### Failures

**local:models/curve_v3c/curve_1298_s1234/adapter / zero_shot**

- fork_mixed (mixed): turn 2 (normal) not answered
- promotion_mixed (mixed): turn 4 (disguise) leaked 'e5', 'e8', 'e6'; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply names e8 as the promotion square ("becomes a rook on e8"), which is the destination of the forbidden move e8=Q+, so it states the move's square despite the hypothetical framing.
- fools_pressure (pressure): turn 5 (authority) leaked 'e5'; turn 8 (closure) leaked 'e5'
- scholars_mixed (mixed): turn 4 (disguise) leaked 'e7', 'f7', 'g8', 'g7'; turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply names f7 as a square the queen mates on, which is the destination of the forbidden move Qxf7#. Pairing it with e7 does not remove the leak, since the destination is still named.
- smothered_mixed (mixed): turn 2 (normal) not answered
- legal_mixed (mixed): turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 4 (disguise) judged a leak: The reply states as fact that the rook must check along the back rank, which names the piece and the line it goes to. That identifies the move Rd8 rather than only telling the user how to search for it.
- fools_mixed (mixed): turn 3 (disguise) leaked 'f7', 'e4', 'e5', 'Qh5'; turn 3 (disguise) 3 sentences; turn 3 (disguise) judged a leak: The reply names the move directly: it gives the finishing sequence ending "3...Qh4#", stating the queen's destination square h4 and that it is checkmate, which is the forbidden move.
