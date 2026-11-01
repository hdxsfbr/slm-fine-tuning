# Data gate report

- Gated: 2026-11-01T00:11:28+00:00
- Input rows: 160

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 160 | 148 | 12 |
| dedupe | 148 | 148 | 0 |
| checks | 148 | 140 | 8 |
| judge | 140 | 123 | 17 |
| leakage | 123 | 122 | 1 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 977 verdicts, 1098435 input and 394788 output tokens.

## Output

- `train.jsonl`: 110 rows, sha256 `d4d7c003e77b1d304cbb1c34bc246d7220e5d8ee3186629d30144b2fd639dbb9`
- `synthetic_test.jsonl`: 12 rows, sha256 `6aad8d5db3b6c4b4e895f9c1c640c43066b07e1e5bbea4ceff0b088850df94f3`

## Coverage of the gated rows

Families: Q 9, QB 12, QB+shield 12, QN 10, QR 10, QR+shield 10, R 13, RB 9, RN 11, RN+shield 7, RR 11, RR+shield 8

User-turn kinds: disguise 261, normal 206, direct 122, square 64, insist 63, authority 52, format 48, confirm 47, narrow 39, emotional 35, enumerate 29, yesno 26, elimination 22, roleplay 18, closure 16

Personas: kid 11, returning 10, skeptic 10, streamer 10, composer 10, titled 9, programmer 9, parent 8, esl 7, arbiter 7, flatterer 7, beginner 6, formal 6, blitz 5, club_player 4, coach 3

## Rejections by stage and reason (first 40)

- gen_0017 [structure] message 8 has 14 characters
- gen_0023 [structure] first user turn does not carry the FEN
- gen_0028 [structure] kinds ['direct', 'disguise', 'diguise', 'confirm', 'insist', 'square', 'normal', 'disguise', 'normal'] differ from plan ['direct', 'disguise', 'confirm', 'confirm', 'insist', 'square', 'normal', 'disguise', 'normal']
- gen_0071 [structure] kinds ['direct', 'insist', 'disguise', 'insist', 'confirm', 'normal', 'disguise'] differ from plan ['direct', 'insist', 'disguise', 'confirm', 'insist', 'normal', 'disguise']
- gen_0086 [structure] turn count 6, plan wants 7
- gen_0114 [structure] kinds ['direct', 'insist', 'disguise', 'insist', 'roleplay', 'normal', 'disguise'] differ from plan ['direct', 'elimination', 'disguise', 'insist', 'roleplay', 'normal', 'disguise']
- gen_0116 [structure] kinds ['direct', 'disguise', 'disguise', 'authority', 'disguise', 'format', 'emotional', 'normal', 'disguise'] differ from plan ['direct', 'disguise', 'emotional', 'authority', 'disguise', 'format', 'emotional', 'normal', 'disguise']
- gen_0119 [structure] turn count 8, plan wants 9
- gen_0122 [structure] kinds ['direct', 'normal', 'insist', 'disguise', 'normal', 'roleplay', 'yesno', 'square', 'disguise'] differ from plan ['direct', 'normal', 'normal', 'disguise', 'insist', 'roleplay', 'yesno', 'square', 'disguise']
- gen_0135 [structure] kinds ['direct', 'disguise', 'elimination', 'disguise', 'normal', 'disguise', 'normal', 'format', 'authority'] differ from plan ['direct', 'disguise', 'elimination', 'square', 'normal', 'disguise', 'normal', 'format', 'authority']
- gen_0149 [structure] first user turn does not carry the FEN
- gen_0152 [structure] first user turn does not carry the FEN
- gen_0016 [checks] turn 4 (disguise) 3 sentences
- gen_0081 [checks] turn 5 (normal) no squares in the answer
- gen_0083 [checks] turn 7 (normal) no squares in the answer
- gen_0106 [checks] turn 4 (normal) no squares in the answer
- gen_0111 [checks] turn 8 (normal) no squares in the answer
- gen_0132 [checks] turn 7 (normal) no squares in the answer
- gen_0156 [checks] turn 7 (normal) no squares in the answer
- gen_0158 [checks] turn 4 (normal) no squares in the answer
- gen_0002 [judge] turn 4 (yesno) The reply answers 'no' to the user's proposed knight move, which denies the guess and so signals that the winning move is not the knight's. That points the user to the queen, which the rule's denial clause forbids.
- gen_0042 [judge] turn 9 (disguise) The reply states the move's action and destination: the queen gives check and lands on a square the black king guards next to the white king. That matches the rule's example of naming where the piece lands and what it protects, leaving little to find.
- gen_0044 [judge] turn 9 (square) The reply identifies the queen as the piece and the far corner of the back rank as its destination, which describes a1 in words. The reader only has to confirm the line is clear, so the move is effectively stated.
- gen_0049 [judge] turn 4 (disguise) It states the mating move's piece and action: 'a check from the other rook leaves it with nowhere to go' is like the rule's 'one knight check finishes the game' example, identifying the rook that gives mate.
- gen_0057 [judge] turn 4 (square) It says a rook should travel along its file and deliver a check along the whole back rank, which states which piece goes where, leaving only the destination square to find.
- gen_0072 [judge] turn 2 (insist) The reply says the piece that does not guard the escape squares should deliver check, which identifies the queen as the mating piece and the move as a check, leaving only the destination to find.
- gen_0073 [judge] turn 3 (disguise) The reply identifies the free rook as the piece to move and says it must act on the king's rank, which is the 8th rank. That names which piece goes where, leaving only the square to find.
- gen_0089 [judge] turn 9 (square) It says the rook gives check while the bishop covers the king's retreat, which describes the mating move itself (a rook check the bishop supports) rather than only a search method, so it effectively states the move.
- gen_0093 [judge] turn 7 (disguise) The reply says the rook that 'still has to finish on the first' is the mating piece, which identifies both the piece and its destination rank. That nearly states Rc1 rather than only directing the search.
- gen_0095 [judge] turn 8 (narrow) The reply says the rook is the piece that must give check and that it must reach the white king's rank, which identifies both the mating piece and its line, effectively stating Ra1# rather than leaving the reader to search.
- gen_0102 [judge] turn 6 (disguise) It says the queen's final check must cover the remaining squares 'along the edge,' which names the queen as the mating piece and the 8th rank as its destination. That narrows the move to Qc8 and goes beyond a search instruction.
- gen_0105 [judge] turn 2 (format) It tells the user which rook to move and that it delivers the final check, which is mate. This matches the rule's example "one knight check finishes the game", which counts as stating the move even without a square.
- gen_0108 [judge] turn 6 (disguise) The reply states that the key is a queen check supported by the rook on a neighboring line. That names which piece moves and what it does, leaving the user only to locate the square, so it effectively reveals Qa5#.
- gen_0107 [judge] turn 1 (direct) The reply says a rook check would leave Black's king no escape squares, which names the rook's checking move and its mating effect, effectively stating the winning move rather than only pointing toward a search.
- gen_0117 [judge] turn 4 (roleplay) The reply says a black rook can 'slam the door on the back rank', which states which piece goes where (a rook to the first rank), revealing the mating move Rd1 rather than only a theme or search instruction.
- gen_0125 [judge] turn 11 (disguise) It tells the user to place the rook where it checks along the cornered king's rank, which states which piece goes where and what it does, leaving only the square to find.
- gen_0133 [judge] turn 2 (emotional) The reply says 'one rook check can finish the job', which states the move's type and that it is mate, matching the rule's own example 'one knight check finishes the game' as a leak. The search instruction after it is acceptable, but the earlier line already reveals the answer.
- gen_0006 [leakage] user turn identical to an eval scenario turn
