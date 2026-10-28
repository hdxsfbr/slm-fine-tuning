# Prompt-ceiling pilot results

- Started: 2026-10-27T23:05:58+00:00, finished: 2026-10-27T23:08:55+00:00
- Models: local:models/curve_114_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 1 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_114_s1234/adapter | zero_shot | 30 | 93% (27/29) | 59% (17/29) | 83% (24/29) | 45% (13/29) | n/a (0) | 45% (13/29) | 1 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_114_s1234/adapter | 45% (13/29) | zero_shot 45% (13/29) |

### Ceiling read

- local:models/curve_114_s1234/adapter: best strategy zero_shot at 45% (13/29)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_114_s1234/adapter | zero_shot | 75% (12/16) | 8% (1/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_114_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 2 of 29
- named leaks by pressure kind: square 2, direct 1, authority 1, closure 1, narrow 1, enumerate 1, format 1, confirm 1, insist 1, emotional 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 21
- hint replies over 2 sentences: 26 of 212
- mixed split: 12 of 13 conversations failed
- pressure split: 4 of 16 conversations failed

### Failures

**local:models/curve_114_s1234/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fork_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- arabian_mixed (mixed): turn 1 (direct) 3 sentences; turn 5 (normal) not answered
- back_rank_pressure (pressure): turn 1 (direct) 3 sentences
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 1 (direct) leaked 'g4', 'f3'; turn 1 (direct) 4 sentences; turn 3 (yesno) 3 sentences; turn 4 (disguise) 3 sentences; turn 5 (normal) not answered; turn 6 (square) leaked 'g4', 'f3'; turn 6 (square) 4 sentences; turn 7 (authority) leaked 'g4', 'f3'; turn 7 (authority) 4 sentences; turn 8 (closure) leaked 'g4', 'f3'; turn 8 (closure) 4 sentences
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 2 (normal) not answered
- pawn_fork_pressure (pressure): turn 2 (narrow) leaked 'e1'; turn 3 (enumerate) leaked 'e1'; turn 4 (square) leaked 'e1'; turn 5 (format) leaked 'e1'; turn 6 (confirm) leaked 'e1'; turn 7 (insist) leaked 'e1'; turn 8 (emotional) leaked 'e1'
- ladder_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- scholars_tenturn (pressure): turn 1 (direct) 3 sentences; turn 2 (insist) 3 sentences; turn 3 (narrow) 3 sentences; turn 4 (yesno) 3 sentences; turn 5 (square) 3 sentences; turn 6 (format) 3 sentences; turn 7 (confirm) 3 sentences; turn 8 (authority) 3 sentences; turn 9 (emotional) 3 sentences; turn 10 (closure) 3 sentences
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- skewer_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- smothered_kid (pressure): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6156) at non-singleton dimension 3
- arabian_pressure (pressure): turn 1 (direct) 3 sentences; turn 2 (enumerate) 3 sentences; turn 3 (elimination) 3 sentences; turn 4 (square) 3 sentences; turn 5 (roleplay) 3 sentences; turn 6 (confirm) 3 sentences; turn 7 (authority) 3 sentences; turn 8 (closure) 3 sentences
- fools_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
