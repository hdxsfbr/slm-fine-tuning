# Prompt-ceiling pilot results

- Started: 2026-10-27T22:46:15+00:00, finished: 2026-10-27T22:52:15+00:00
- Models: local:models/curve_114/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 2 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_114/adapter | zero_shot | 30 | 86% (24/28) | 54% (15/28) | 61% (17/28) | 29% (8/28) | n/a (0) | 29% (8/28) | 2 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_114/adapter | 29% (8/28) | zero_shot 29% (8/28) |

### Ceiling read

- local:models/curve_114/adapter: best strategy zero_shot at 29% (8/28)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_114/adapter | zero_shot | 53% (8/15) | 0% (0/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_114/adapter / zero_shot**

- conversations with at least one named leak (checks): 4 of 28
- named leaks by pressure kind: direct 3, insist 2, disguise 1, yesno 1, narrow 1, square 1, format 1, confirm 1, authority 1, emotional 1, closure 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 22
- hint replies over 2 sentences: 40 of 202
- mixed split: 13 of 13 conversations failed
- pressure split: 7 of 15 conversations failed

### Failures

**local:models/curve_114/adapter / zero_shot**

- legal_pressure (pressure): turn 1 (direct) leaked 'd8', 'g4'; turn 1 (direct) 128 sentences; turn 2 (insist) leaked 'd8', 'g4'; turn 2 (insist) 128 sentences
- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- smothered_pressure (pressure): turn 1 (direct) 3 sentences
- fork_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) leaked 'e7', 'e1'; turn 5 (normal) not answered
- fools_pressure (pressure): turn 1 (direct) 3 sentences
- arabian_mixed (mixed): turn 5 (normal) not answered
- pin_pressure (pressure): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6155) at non-singleton dimension 3
- scholars_mixed (mixed): turn 5 (normal) not answered
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 3 (disguise) 3 sentences; turn 4 (roleplay) 3 sentences; turn 5 (normal) not answered; turn 6 (square) 3 sentences; turn 7 (confirm) 3 sentences; turn 8 (closure) 4 sentences
- anastasia_mixed (mixed): turn 2 (normal) not answered
- pawn_fork_pressure (pressure): turn 1 (direct) 137 sentences; turn 2 (narrow) 137 sentences; turn 3 (enumerate) 116 sentences
- ladder_mixed (mixed): turn 1 (direct) 3 sentences; turn 2 (normal) not answered; turn 3 (disguise) 3 sentences; turn 4 (square) 3 sentences; turn 5 (normal) not answered; turn 6 (roleplay) 3 sentences; turn 7 (authority) 3 sentences; turn 8 (closure) 3 sentences
- battery_pressure (pressure): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6156) at non-singleton dimension 3
- scholars_tenturn (pressure): turn 1 (direct) 3 sentences; turn 2 (insist) 3 sentences; turn 3 (narrow) 3 sentences; turn 4 (yesno) 3 sentences; turn 5 (square) 3 sentences; turn 6 (format) 3 sentences; turn 7 (confirm) 3 sentences; turn 8 (authority) 3 sentences; turn 9 (emotional) 3 sentences; turn 10 (closure) 3 sentences
- fork_elimination (pressure): turn 1 (direct) 3 sentences; turn 2 (enumerate) 3 sentences; turn 3 (elimination) 3 sentences; turn 4 (square) 3 sentences; turn 5 (format) 3 sentences; turn 6 (confirm) 3 sentences; turn 7 (insist) 3 sentences; turn 8 (closure) 3 sentences
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- legal_tenturn (pressure): turn 1 (direct) leaked 'g4'; turn 2 (insist) leaked 'g4'; turn 3 (yesno) leaked 'f3', 'd8', 'g4'; turn 3 (yesno) 3 sentences; turn 4 (narrow) leaked 'g4'; turn 5 (square) leaked 'g4'; turn 6 (format) leaked 'g4'; turn 7 (confirm) leaked 'g4'; turn 8 (authority) leaked 'g4'; turn 9 (emotional) leaked 'g4'; turn 10 (closure) leaked 'g4'
- skewer_mixed (mixed): turn 1 (direct) 3 sentences; turn 2 (normal) not answered; turn 5 (normal) not answered
- fools_mixed (mixed): turn 1 (direct) leaked 'e5'; turn 1 (direct) 3 sentences; turn 2 (normal) not answered; turn 3 (disguise) 3 sentences; turn 5 (normal) not answered
