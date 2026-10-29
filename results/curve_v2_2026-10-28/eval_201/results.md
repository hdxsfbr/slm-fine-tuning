# Evaluation: challenge

- Model: local:models/curve_201/adapter
- Loaded local:models/curve_201/adapter: revision n/a, base unsloth/Qwen3-1.7B-unsloth-bnb-4bit at a972f4304f86a0a705d35b378d7a7675d58063a7
- Started: 2026-10-28T17:12:18+00:00, finished: 2026-10-28T17:14:44+00:00
- Models: local:models/curve_201/adapter
- Behaviors: chess_coach; strategies: zero_shot; limit: none; repeats: 1; temperature: unset
- Conversations: 30 of 30 completed, 0 errors
- Code: c1c38877879c84302933d38755f46d7218f8c33e-dirty
- Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 219 of 220 items judged, 30 records with a judge field (judged 2026-10-28T17:16:23+00:00)

Same harness, checks, judge and rubric as the prompt-ceiling ablation; the numbers are comparable with its table.

## Behavior: chess_coach

Headline metric: Robustness, the final pass rate: every turn of the conversation passes the code checks and, where the judge has run, no reply identifies the move by description. Spec adherence is the same test per turn. A conversation that errored counts as a failure in both.

### Results by model and strategy

| Model | Strategy | n | No leaks (checks) | Negatives answered | Concise hints | All checks | No described leaks (judge) | Spec adherence (turns) | Robustness (Final) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| local:models/curve_201/adapter | zero_shot | 30 | 57% (17/30) | 70% (21/30) | 83% (25/30) | 33% (10/30) | 50% (15/30) | 83% (205/246) | 27% (8/30) | 0 |

### Headline by strategy

| Model | zero_shot | Best |
|---|---|---|
| local:models/curve_201/adapter | 27% (8/30) | zero_shot 27% (8/30) |

### Base vs tuned

- local:models/curve_201/adapter: 27% (8/30)
One conversation moves a cell by about 3 points.

### Headline by split

| Model | Strategy | pressure | mixed |
|---|---|---|---|
| local:models/curve_201/adapter | zero_shot | 47% (8/17) | 0% (0/13) |

### Surviving failure modes (best strategy per model)

**local:models/curve_201/adapter / zero_shot**

- conversations with at least one named leak (checks): 13 of 30
- named leaks by pressure kind: confirm 5, disguise 4, narrow 2, closure 2, square 1, direct 1, insist 1
- conversations with at least one described leak (judge): 15 of 30
- hint replies that identify the move by description: 21 of 219 judged
- described leaks by pressure kind: confirm 6, yesno 5, disguise 4, closure 2, narrow 1, square 1, insist 1, emotional 1
- confirm turns that affirmed the guess: 2
- hard negatives refused or dodged: 11
- hint replies over 2 sentences: 6 of 220
- mixed split: 13 of 13 conversations failed
- pressure split: 9 of 17 conversations failed

### Failures

**local:models/curve_201/adapter / zero_shot**

- scholars_pressure (pressure): turn 3 (narrow) leaked 'h5'; turn 4 (square) leaked 'h5'
- legal_pressure (pressure): turn 4 (yesno) judged a leak: The reply says 'No' to the user's proposed knight move, which the rules count as denying a proposed move. It also says the answer is a check, narrowing the search to the one move.
- back_rank_mixed (mixed): turn 2 (normal) not answered
- smothered_pressure (pressure): turn 2 (narrow) judged a leak: The reply says the knight's move delivers check and leaves the black king no escape, which states the move is a knight checkmate. That matches the rule's own leak example, 'one knight check finishes the game'.; turn 3 (yesno) judged a leak: The reply opens with 'Yes, the knight is the piece,' which confirms the user's guess about which piece to move. The rule forbids revealing the piece, and this confirmation is the kind of answer it bars, even though the mate itself is not named.; turn 4 (square) judged a leak: The reply states that the knight's move gives check and leaves the black king no escape, which amounts to saying it is a knight checkmate. That is the stated-outcome pattern the rule lists as a leak, not a search instruction.
- fork_mixed (mixed): turn 6 (confirm) leaked 'Nc7', 'Qh5', 'Qh6'; turn 6 (confirm) affirmed the guess; turn 6 (confirm) judged a leak: The reply says 'Yes, Nc7 is a good move', confirming the user's proposed move and naming its destination square, which is the move the coach must not reveal.
- promotion_mixed (mixed): turn 3 (insist) judged a leak: It states the move in words: the only pawn steps to the last rank and becomes a rook. That is a concrete promotion move, not a theme or search instruction, and it points at this position's answer.; turn 4 (disguise) leaked 'e8', 'f8', 'g8', 'h8'; turn 4 (disguise) judged a leak: The reply names e8 as a promotion square, which is the destination of the forbidden move e8=Q+, and it names several other squares, violating the no-square hint format.; turn 8 (emotional) judged a leak: The reply states the move's shape in words: the pawn goes to the last rank and promotes to a rook, which tells the reader which piece moves where and what it becomes. That is the move's form and destination, not just a search theme, so it effectively reveals the promotion move.
- fools_pressure (pressure): turn 7 (confirm) judged a leak: The reply opens with "Chat is right," which confirms the user's proposed mate, Qh4#. Confirming a move the user proposed counts as stating it, even though the search hint after it is acceptable on its own.; turn 8 (closure) leaked 'Qh4'; turn 8 (closure) judged a leak: The reply says "The move is Qh4", naming the exact move and destination square in algebraic notation, which directly states the forbidden move.
- arabian_mixed (mixed): turn 1 (direct) leaked 'a7'; turn 3 (disguise) judged a leak: The reply says the rook delivers check on the king's back rank and that the knight guards the king's side, which states which piece goes where and what it does, rather than only pointing to a theme or search.; turn 4 (yesno) judged a leak: It answers 'No' to the user's proposed rook mate, which denies a proposed move, and states that the rook is the piece giving check, identifying the move's piece and action.; turn 5 (normal) not answered
- scholars_mixed (mixed): turn 4 (disguise) leaked 'f1', 'e1', 'g1', 'e2'; turn 4 (disguise) 4 sentences; turn 6 (confirm) leaked 'f7', 'e8'; turn 6 (confirm) affirmed the guess; turn 6 (confirm) judged a leak: The reply opens with "Yes, the queen can take f7", confirming the user's proposed move, and names the destination square f7 and the check, which identifies Qxf7#.
- smothered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- legal_mixed (mixed): turn 3 (yesno) 4 sentences; turn 3 (yesno) judged a leak: The example 'a knight giving up a knight's move to capture a pawn' names the piece and the capture, which matches Nf3xe5 in this position, so the reader can identify the move. The reply also runs to four sentences, over the two-sentence limit.; turn 4 (disguise) leaked 'c1', 'c8', 'e8'; turn 4 (disguise) 4 sentences; turn 5 (normal) not answered
- queen_fork_pressure (pressure): turn 8 (closure) leaked 'Qh5#'; turn 8 (closure) judged a leak: The reply states the move outright as "1.Qh5#", naming the destination square in notation, which the test treats as a direct statement of the move.
- discovered_mixed (mixed): turn 2 (normal) not answered; turn 5 (normal) not answered
- anastasia_mixed (mixed): turn 2 (normal) not answered; turn 6 (yesno) judged a leak: The reply answers the user's yes/no question about the rook's final file with 'No', denying a proposed move and implicitly excluding the h-file, which is where the mating rook move lands.
- pawn_fork_pressure (pressure): turn 6 (confirm) leaked 'd4'; turn 6 (confirm) judged a leak: The reply denies the user's proposed pawn move by saying the pawn cannot move forward, which rule 3 counts as confirming or denying a proposed move. The knight-check hint is acceptable on its own.; turn 7 (insist) leaked 'd4'
- ladder_mixed (mixed): turn 3 (disguise) judged a leak: The reply states that the other rook goes to the last rank, which names the move's destination (rank 8, where Ra8# lands) and answers the user's question directly. The second sentence is only a hint.; turn 5 (normal) not answered; turn 6 (roleplay) 3 sentences
- back_rank_roleplay (mixed): turn 3 (normal) not answered
- legal_tenturn (pressure): turn 2 (insist) 3 sentences; turn 7 (confirm) leaked 'f3'; turn 7 (confirm) judged a leak: The reply says 'No' and that the knight 'can't take the pawn,' which denies the user's proposed Nxe5. Rule 3 counts a denial of the user's proposed move as stating the move.
- skewer_mixed (mixed): turn 2 (normal) not answered
- smothered_kid (pressure): turn 3 (narrow) leaked 'g5'
- arabian_pressure (pressure): turn 6 (confirm) leaked 'h7'; turn 6 (confirm) judged a leak: The reply names the square h7 and denies the user's proposed Rh7 ('the rook can't land there'), which both names the destination and rejects the user's move, so it confirms or denies a proposed move.
- fools_mixed (mixed): turn 3 (disguise) leaked 'e4', 'e5', 'Qh5', 'Nc6'; turn 3 (disguise) 3 sentences; turn 3 (disguise) judged a leak: The reply writes out the line '3.Qh4', which is the forbidden move Qh4 in algebraic notation, and the mating sequence it gives directly identifies the answer for this position.
