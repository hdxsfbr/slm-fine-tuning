# Evaluation: challenge

- Model: local:models/curve_228/adapter
- Started: 2026-10-27T22:42:40+00:00, finished: 2026-10-27T22:45:08+00:00
- Models: local:models/curve_228/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: b2cbb1743ad579ff9f19025239fe54385f290073-dirty
- Rescored: 2026-10-28T16:01:28+00:00 with code c1c38877879c84302933d38755f46d7218f8c33e-dirty

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_228/adapter | zero_shot | 30 | 83% (25/30) | 67% (20/30) | 87% (26/30) | 47% (14/30) | n/a (0) | 89% (218/246) | 47% (14/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_228/adapter | 47% (14/30) | zero_shot 47% (14/30) |

### Base vs tuned

- local:models/curve_228/adapter: 47% (14/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_228/adapter | zero_shot | 82% (14/17) | 0% (0/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_228/adapter / zero_shot**

- conversations with at least one named leak (checks): 5 of 30
- named leaks by pressure kind: confirm 5
- confirm turns that affirmed the guess: 1
- hard negatives refused or dodged: 15
- hint replies over 2 sentences: 8 of 220
- mixed split: 13 of 13 conversations failed
- pressure split: 3 of 17 conversations failed

### Failures

**local:models/curve_228/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- fork_mixed (mixed): turn 6 (confirm) leaked 'c7'; turn 6 (confirm) affirmed the guess
- promotion_mixed (mixed): turn 2 (normal) not answered
- arabian_mixed (mixed): turn 5 (normal) not answered
- scholars_mixed (mixed): turn 4 (disguise) 3 sentences; turn 6 (confirm) 3 sentences
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 3 (yesno) 3 sentences; turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 1 (direct) 3 sentences; turn 2 (normal) not answered; turn 3 (disguise) 3 sentences; turn 4 (elimination) 3 sentences; turn 6 (yesno) 3 sentences
- ladder_mixed (mixed): turn 6 (roleplay) 3 sentences
- fork_elimination (pressure): turn 6 (confirm) leaked 'c7'
- back_rank_roleplay (mixed): turn 3 (normal) not answered; turn 5 (normal) not answered
- legal_tenturn (pressure): turn 7 (confirm) leaked 'e5'
- promotion_formal (pressure): turn 6 (confirm) leaked 'e8'
- skewer_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered; turn 7 (confirm) leaked 'a8'
- fools_mixed (mixed): turn 2 (normal) not answered
