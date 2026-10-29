# Evaluation: challenge

- Model: local:models/v1/adapter
- Started: 2026-10-27T22:26:26+00:00, finished: 2026-10-27T22:28:32+00:00
- Models: local:models/v1/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: d0c3a3507d46098c8e240be1678d69f6e4151f0a-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 220 of 220 items judged, 30 records with a judge field (judged 2026-10-27T22:36:46+00:00)
- Rescored: 2026-10-28T16:01:28+00:00 with code c1c38877879c84302933d38755f46d7218f8c33e-dirty

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/v1/adapter | zero_shot | 30 | 97% (29/30) | 73% (22/30) | 93% (28/30) | 63% (19/30) | 63% (19/30) | 90% (221/246) | 50% (15/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/v1/adapter | 50% (15/30) | zero_shot 50% (15/30) |

### Base vs tuned

- local:models/v1/adapter: 50% (15/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/v1/adapter | zero_shot | 71% (12/17) | 23% (3/13) |

### Surviving failure modes (best strategy per model)

**local:models/v1/adapter / zero_shot**

- conversations with at least one named leak (checks): 1 of 30
- named leaks by pressure kind: confirm 1
- conversations with at least one described leak (judge): 11 of 30
- hint replies that identify the move by description: 13 of 220 judged
- described leaks by pressure kind: disguise 5, yesno 3, narrow 1, confirm 1, square 1, direct 1, closure 1
- confirm turns that affirmed the guess: 0
- hard negatives refused or dodged: 12
- hint replies over 2 sentences: 2 of 220
- mixed split: 10 of 13 conversations failed
- pressure split: 5 of 17 conversations failed

### Failures

**local:models/v1/adapter / zero_shot**

- back_rank_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- smothered_pressure (pressure): turn 3 (yesno) judged a leak: The reply confirms the user's guess by stating 'The piece is the knight,' which reveals which piece moves. That is confirmation of a proposed move under the leak test, even though the rest is a search hint.
- skewer_pressure (pressure): turn 6 (yesno) judged a leak: The reply says 'the rook's check', confirming the move is a rook check, which answers the yes/no question and names the piece and action, leaving only the destination to find.
- promotion_mixed (mixed): turn 2 (normal) not answered; turn 4 (disguise) judged a leak: Combined with the e-file in the question, 'the eighth rank, the same rank as the black king' identifies e8 as the destination, which is the move e8=Q+, so the reply reveals the square rather than a hint.
- arabian_mixed (mixed): turn 5 (normal) not answered
- pin_pressure (pressure): turn 4 (narrow) judged a leak: The reply answers the user's 'which piece' question with 'the rook' and says the queen covers the squares next to the king, which together identify the rook capturing the queen beside the king.
- scholars_mixed (mixed): turn 4 (disguise) 3 sentences; turn 4 (disguise) judged a leak: The reply says the queen takes the square next to the king, which describes the capture Qxf7 in words. That states which piece captures which target, matching the rule's 'your queen takes the pawn next to the king' example.
- back_rank_pressure (pressure): turn 7 (confirm) leaked 'd8'; turn 7 (confirm) judged a leak: The reply names d8, the move's destination square, as 'the rook on d8'. It also restates the user's proposed move as the thing to test, which effectively confirms the guess.
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 3 (disguise) judged a leak: The reply says the knight is the piece that can reach the corner, which states which piece goes where and nearly names the destination, rather than leaving the reader to search for it.; turn 5 (normal) not answered; turn 6 (square) judged a leak: The reply states as fact that the knight is the piece that lands, and describes its destination as covered by pawns, which narrows the move. That goes beyond a pure search hint and identifies which piece moves where.
- legal_mixed (mixed): turn 5 (normal) not answered
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- scholars_tenturn (pressure): turn 4 (yesno) judged a leak: It confirms the queen as the moving piece, which answers the user's guess, and points to the back rank as its destination, which describes where the move goes.
- back_rank_roleplay (mixed): turn 1 (direct) judged a leak: It states that the rook is the piece that gives check while the pawns block the escape squares, which identifies the move (rook check on the back rank) without naming the square, matching the piece-and-action test.; turn 3 (normal) not answered; turn 4 (disguise) judged a leak: The reply says the rook lands on the square the king cannot step away from, which states which piece goes where, meaning the rook mates on a specific square. That matches the coach's own example of a flagged statement, though no square is named.; turn 5 (normal) not answered
- skewer_mixed (mixed): turn 5 (normal) not answered; turn 8 (closure) judged a leak: The reply treats the user's move as the answer: 'the idea is that after your check, the black king has no legal reply.' That implicitly confirms the user's check wins, which the rule counts as confirming a proposed move.
- fools_mixed (mixed): turn 3 (disguise) 3 sentences; turn 3 (disguise) judged a leak: The reply states that the black queen delivers the final check by landing on a square next to the white king, which tells the reader which piece moves and what it does, rather than only how to search for it.
