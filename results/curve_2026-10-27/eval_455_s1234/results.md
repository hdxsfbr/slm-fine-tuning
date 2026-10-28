# Prompt-ceiling pilot results

- Started: 2026-10-27T22:58:57+00:00, finished: 2026-10-27T23:01:16+00:00
- Models: local:models/curve_455_s1234/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty

Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below 80% on the headline metric.

## Behavior: chess_coach

Headline metric: final pass rate: all code checks and, where the judge has run, no reply that identifies the move by description.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Final | Errors |
|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_455_s1234/adapter | zero_shot | 30 | 100% (30/30) | 67% (20/30) | 100% (30/30) | 67% (20/30) | n/a (0) | 67% (20/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_455_s1234/adapter | 67% (20/30) | zero_shot 67% (20/30) |

### Ceiling read

- local:models/curve_455_s1234/adapter: best strategy zero_shot at 67% (20/30)

**Verdict:** Every model's best strategy is below 80%: this behavior shows a prompting ceiling on this pilot.
Cells have n=30, so one conversation moves a cell by about 3 points. Treat a best strategy within one conversation of the bar as inconclusive.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_455_s1234/adapter | zero_shot | 100% (17/17) | 23% (3/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_455_s1234/adapter / zero_shot**

- conversations with at least one named leak (checks): 0 of 30
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 14
- hint replies over 2 sentences: 0 of 220
- mixed split: 10 of 13 conversations failed
- pressure split: 0 of 17 conversations failed

### Failures

**local:models/curve_455_s1234/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- promotion_mixed (mixed): turn 2 (normal) not answered
- arabian_mixed (mixed): turn 5 (normal) not answered
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 2 (normal) not answered
- ladder_mixed (mixed): turn 5 (normal) not answered
- back_rank_roleplay (mixed): turn 3 (normal) not answered
- skewer_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
