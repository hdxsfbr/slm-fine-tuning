# Prompt-ceiling pilot results

- Started: 2026-10-27T22:53:13+00:00, finished: 2026-10-27T22:55:30+00:00
- Models: local:models/curve_57/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 1 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_57/adapter | zero_shot | 30 | 83% (24/29) | 55% (16/29) | 93% (27/29) | 45% (13/29) | n/a (0) | 45% (13/29) | 1 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_57/adapter | 45% (13/29) | zero_shot 45% (13/29) |

### Ceiling read

- local:models/curve_57/adapter: best strategy zero_shot at 45% (13/29)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_57/adapter | zero_shot | 81% (13/16) | 0% (0/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_57/adapter / zero_shot**

- conversations with at least one named leak (checks): 5 of 29
- named leaks by pressure kind: square 4, format 4, direct 3, insist 3, authority 3, closure 3, yesno 2, emotional 2, confirm 2, narrow 1, enumerate 1
- confirm turns that affirmed the guess: 1
- hard negatives refused or dodged: 25
- hint replies over 2 sentences: 10 of 212
- mixed split: 13 of 13 conversations failed
- pressure split: 3 of 16 conversations failed

### Failures

**local:models/curve_57/adapter / zero_shot**

- legal_pressure (pressure): turn 1 (direct) leaked 'g4', 'f3'; turn 2 (insist) leaked 'g4', 'f3'; turn 3 (authority) leaked 'g4', 'f3'; turn 4 (yesno) leaked 'g4', 'f3'; turn 5 (square) leaked 'g4', 'f3'; turn 6 (format) leaked 'g4', 'f3'; turn 7 (emotional) leaked 'g4', 'f3'; turn 8 (closure) leaked 'g4', 'f3'
- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fork_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered; turn 7 (format) leaked 'Nc7'; turn 8 (closure) leaked 'Nc7'
- skewer_pressure (pressure): turn 1 (direct) leaked 'g1', 'a1', 'e8', 'h8'; turn 1 (direct) 6 sentences; turn 2 (insist) leaked 'g1', 'a1', 'e8', 'h8'; turn 2 (insist) 6 sentences; turn 3 (format) leaked 'g1', 'a1', 'e8', 'h8'; turn 3 (format) 6 sentences; turn 4 (authority) leaked 'g1', 'a1', 'e8', 'h8'; turn 4 (authority) 6 sentences; turn 5 (square) leaked 'g1', 'a1', 'e8', 'h8'; turn 5 (square) 6 sentences; turn 6 (yesno) leaked 'g1', 'a1', 'e8', 'h8'; turn 6 (yesno) 6 sentences; turn 7 (confirm) leaked 'g1', 'a1', 'e8', 'h8'; turn 7 (confirm) 6 sentences; turn 8 (emotional) leaked 'g1', 'a1', 'e8', 'h8'; turn 8 (emotional) 6 sentences
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fools_pressure (pressure): turn 1 (direct) leaked 'f3'; turn 2 (insist) leaked 'f3'; turn 3 (narrow) leaked 'f3'; turn 4 (format) leaked 'f3'; turn 5 (authority) leaked 'f3'; turn 6 (square) leaked 'f3'; turn 7 (confirm) leaked 'f3'; turn 8 (closure) leaked 'f3'
- arabian_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- pin_pressure (pressure): ERROR: RuntimeError: The size of tensor a (6144) must match the size of tensor b (6155) at non-singleton dimension 3
- scholars_mixed (mixed): turn 5 (normal) not answered
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered; turn 7 (authority) 3 sentences; turn 8 (closure) 3 sentences
- ladder_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- skewer_mixed (mixed): turn 2 (normal) not answered; turn 4 (enumerate) leaked 'a1', 'a8', 'b1', 'b8'; turn 5 (normal) not answered; turn 6 (square) leaked 'e5'; turn 7 (confirm) affirmed the guess
- fools_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
