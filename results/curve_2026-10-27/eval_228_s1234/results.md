# Prompt-ceiling pilot results

- Started: 2026-10-27T23:02:41+00:00, finished: 2026-10-27T23:04:51+00:00
- Models: local:models/curve_228_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_228_s1234/adapter | zero_shot | 30 | 90% (27/30) | 67% (20/30) | 83% (25/30) | 50% (15/30) | n/a (0) | 50% (15/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_228_s1234/adapter | 50% (15/30) | zero_shot 50% (15/30) |

### Ceiling read

- local:models/curve_228_s1234/adapter: best strategy zero_shot at 50% (15/30)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_228_s1234/adapter | zero_shot | 82% (14/17) | 8% (1/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_228_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 3 of 30
- named leaks by pressure kind: confirm 2, disguise 1
- confirm turns that affirmed the guess: 1
- hard negatives refused or dodged: 16
- hint replies over 2 sentences: 11 of 220
- mixed split: 12 of 13 conversations failed
- pressure split: 3 of 17 conversations failed

### Failures

**local:models/curve_228_s1234/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fork_mixed (mixed): turn 5 (normal) not answered; turn 6 (confirm) leaked 'Nc7'; turn 6 (confirm) affirmed the guess
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) leaked 'e7'; turn 5 (normal) not answered
- fools_pressure (pressure): turn 2 (insist) 3 sentences; turn 3 (narrow) 3 sentences; turn 4 (format) 3 sentences; turn 5 (authority) 3 sentences; turn 6 (square) 3 sentences; turn 7 (confirm) 3 sentences; turn 8 (closure) 3 sentences
- arabian_mixed (mixed): turn 5 (normal) not answered
- scholars_mixed (mixed): turn 6 (confirm) 4 sentences
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 3 (yesno) 4 sentences; turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- ladder_mixed (mixed): turn 6 (roleplay) 3 sentences
- scholars_tenturn (pressure): turn 2 (insist) 3 sentences
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- legal_tenturn (pressure): turn 7 (confirm) leaked 'e5'
- skewer_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fools_mixed (mixed): turn 2 (normal) not answered
