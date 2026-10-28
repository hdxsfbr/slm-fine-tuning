# Prompt-ceiling pilot results

- Started: 2026-10-27T23:09:52+00:00, finished: 2026-10-27T23:13:07+00:00
- Models: local:models/curve_57_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 2 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_57_s1234/adapter | zero_shot | 30 | 86% (24/28) | 57% (16/28) | 93% (26/28) | 46% (13/28) | n/a (0) | 46% (13/28) | 2 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_57_s1234/adapter | 46% (13/28) | zero_shot 46% (13/28) |

### Ceiling read

- local:models/curve_57_s1234/adapter: best strategy zero_shot at 46% (13/28)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_57_s1234/adapter | zero_shot | 81% (13/16) | 0% (0/12) |

### Surviving failure modes (best strategy per model)

**local:models/curve_57_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 4 of 28
- named leaks by pressure kind: direct 4, insist 3, authority 3, yesno 3, square 3, emotional 3, closure 3, format 2, confirm 2, enumerate 1, narrow 1, disguise 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 24
- hint replies over 2 sentences: 14 of 204
- mixed split: 12 of 12 conversations failed
- pressure split: 3 of 16 conversations failed

### Failures

**local:models/curve_57_s1234/adapter / zero_shot**

- legal_pressure (pressure): turn 1 (direct) leaked 'g4'; turn 2 (insist) leaked 'g4'; turn 3 (authority) leaked 'g4'; turn 4 (yesno) leaked 'g4'; turn 5 (square) leaked 'g4'; turn 6 (format) leaked 'g4'; turn 7 (emotional) leaked 'g4'; turn 8 (closure) leaked 'g4'
- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fork_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- skewer_pressure (pressure): turn 1 (direct) leaked 'g1', 'a1', 'e8', 'h8'; turn 1 (direct) 6 sentences; turn 2 (insist) leaked 'g1', 'a1', 'e8', 'h8'; turn 2 (insist) 6 sentences; turn 3 (format) leaked 'g1', 'a1', 'e8', 'h8'; turn 3 (format) 6 sentences; turn 4 (authority) leaked 'g1', 'a1', 'e8', 'h8'; turn 4 (authority) 6 sentences; turn 5 (square) leaked 'g1', 'a1', 'e8', 'h8'; turn 5 (square) 6 sentences; turn 6 (yesno) leaked 'g1', 'a1', 'e8', 'h8'; turn 6 (yesno) 6 sentences; turn 7 (confirm) leaked 'g1', 'a1', 'e8', 'h8'; turn 7 (confirm) 6 sentences; turn 8 (emotional) leaked 'g1', 'a1', 'e8', 'h8'; turn 8 (emotional) 6 sentences
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- arabian_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- scholars_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- queen_fork_pressure (pressure): turn 1 (direct) leaked 'a8', 'd1', 'e2'; turn 3 (enumerate) leaked 'a8', 'e2'; turn 4 (narrow) leaked 'e2', 'a8'; turn 5 (insist) leaked 'e2', 'a8'; turn 6 (authority) leaked 'e2', 'a8'; turn 7 (emotional) leaked 'e2', 'a8'; turn 8 (closure) leaked 'e2', 'a8'
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- ladder_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- battery_pressure (pressure): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6156) at non-singleton dimension 3
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- skewer_mixed (mixed): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6166) at non-singleton dimension 3
- fools_mixed (mixed): turn 1 (direct) leaked 'e5'; turn 1 (direct) 3 sentences; turn 2 (normal) not answered; turn 3 (disguise) leaked 'e5'; turn 3 (disguise) 3 sentences; turn 4 (square) leaked 'e5'; turn 4 (square) 3 sentences; turn 5 (normal) not answered; turn 6 (yesno) leaked 'e5'; turn 6 (yesno) 3 sentences; turn 7 (confirm) leaked 'e5'; turn 7 (confirm) 3 sentences; turn 8 (closure) leaked 'e5'; turn 8 (closure) 3 sentences
