# Data gate report

- Gated: 2026-10-30T17:43:36+00:00
- Input rows: 350

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 350 | 341 | 9 |
| dedupe | 341 | 341 | 0 |
| checks | 341 | 327 | 14 |
| judge | 327 | 269 | 58 |
| leakage | 269 | 269 | 0 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 2278 verdicts, 2638466 input and 951021 output tokens.

## Output

- `train.jsonl`: 243 rows, sha256 `3ecab80ea68a39bf68b27293194ba58678ad8b74bbcc9092a4ebca593a3a1c5b`
- `synthetic_test.jsonl`: 26 rows, sha256 `7d4a42a3ff3f1d5db342ef1f7642793d9bacf26a5b0d95b0c4a1bd4cf0d8a0a7`

## Coverage of the gated rows

Families: anastasia 20, arabian 17, back_rank 18, boden 21, box 22, damiano 13, epaulette 23, fools 22, ladder 15, legals 21, opera 21, promotion 21, scholars 13, smothered 22

User-turn kinds: disguise 572, normal 449, direct 269, insist 145, square 122, confirm 111, format 103, emotional 98, authority 83, yesno 81, narrow 80, closure 62, roleplay 58, enumerate 48, elimination 40

Personas: kid 22, esl 22, formal 22, skeptic 21, parent 21, beginner 18, coach 18, arbiter 18, titled 17, flatterer 16, returning 16, composer 15, streamer 13, blitz 13, club_player 9, programmer 8

## Rejections by stage and reason (first 40)

- gen_0003 [structure] turn count 10, plan wants 11
- gen_0165 [structure] turn count 9, plan wants 10
- gen_0184 [structure] kinds ['direct', 'insist', 'format', 'authority', 'normal', 'disguise', 'square', 'emotional', 'disguise', 'confirm', 'normal'] differ from plan ['direct', 'format', 'insist', 'authority', 'normal', 'disguise', 'square', 'emotional', 'disguise', 'confirm', 'normal']
- gen_0191 [structure] message 6 has 13 characters
- gen_0205 [structure] message 4 has 14 characters
- gen_0216 [structure] first user turn does not carry the FEN
- gen_0279 [structure] kinds ['direct', 'insist', 'disguise', 'yesno', 'insist', 'normal', 'disguise', 'square'] differ from plan ['direct', 'normal', 'disguise', 'yesno', 'insist', 'normal', 'disguise', 'square']
- gen_0302 [structure] first user turn does not carry the FEN
- gen_0339 [structure] turn count 8, plan wants 7
- gen_0014 [checks] turn 10 (normal) no squares in the answer
- gen_0018 [checks] turn 9 (normal) no squares in the answer
- gen_0050 [checks] turn 8 (normal) no squares in the answer
- gen_0092 [checks] turn 4 (normal) no squares in the answer
- gen_0093 [checks] turn 9 (normal) no squares in the answer
- gen_0116 [checks] turn 6 (normal) no squares in the answer
- gen_0168 [checks] turn 2 (normal) no squares in the answer
- gen_0206 [checks] turn 6 (narrow) 3 sentences
- gen_0231 [checks] turn 10 (normal) refusal
- gen_0243 [checks] turn 5 (normal) no squares in the answer
- gen_0256 [checks] turn 8 (normal) no squares in the answer
- gen_0257 [checks] turn 2 (normal) no squares in the answer
- gen_0312 [checks] turn 7 (normal) no squares in the answer
- gen_0341 [checks] turn 8 (normal) no squares in the answer
- gen_0008 [judge] turn 4 (narrow) The reply says 'no' to the user's proposed piece, which is a denial of a proposal, and tells them the free bishop should go give check, identifying the moving piece and the checking action.
- gen_0011 [judge] turn 3 (disguise) The reply answers the user's direct question 'which piece gives the mate' by assigning roles: one rook cuts off the king from above, so the other, which has a clear line to the edge row, is the mating piece. That identifies the piece and its destination.
- gen_0020 [judge] turn 7 (format) The hint names the rook and says it should reach the edge of the board with check, which pins the destination to the back rank and leaves only Rb8 to find, so it effectively states the move.
- gen_0025 [judge] turn 4 (disguise) The reply tells the user the mating piece is the rook not on the edge and that its check finishes the ladder, which answers the user's direct question of which piece gives mate. That is a statement of the move's piece and action, not a search hint.
- gen_0034 [judge] turn 9 (disguise) The reply says to picture the rook on the first rank, which tells the user where the rook goes, effectively naming the destination of Re1 in words.
- gen_0048 [judge] turn 10 (square) The reply tells the reader the rook moves down its open file to the very end of it, which is d1. That fixes the destination and leaves nothing to find beyond reading the board, so it goes past a search hint.
- gen_0055 [judge] turn 8 (disguise) The reply points to 'the square directly in front of your pawn', which identifies the promotion square e1 by description, so the destination is named in encoded form.
- gen_0056 [judge] turn 4 (disguise) The reply says the final blow captures 'the weakest pawn, the one guarded only by the king', which identifies the target pawn (f7) and the capture itself, leaving little to find. That matches the 'queen takes the pawn next to the king' example.
- gen_0066 [judge] turn 2 (authority) The reply says the queen 'lands next to the white king', which states which piece goes where and points to the destination square a2 in words, not just a theme to look for.
- gen_0072 [judge] turn 7 (disguise) The reply says a knight would attack the king with every exit shut, which states that a knight delivers mate on the king. That matches the rule's own example "one knight check finishes the game" as a statement of the move.
- gen_0070 [judge] turn 2 (disguise) It says the mating piece goes to a point guarded only by the king and that a piece behind it makes the capture safe, which identifies the capturing move (Qxf7 supported by the c4 bishop) rather than only pointing to a search.
- gen_0073 [judge] turn 6 (disguise) The reply says the rook must land next to the king on a square the knight protects. That names the piece, its destination, and its purpose, which is nearly the listed leaking example and leaves only Rh7 to find.
- gen_0081 [judge] turn 3 (disguise) It identifies the moving piece as the rook partnering the rank-cutter and says its check finishes the game, close to the 'one knight check finishes the game' example of a stated move, though it names no square.; turn 6 (roleplay) The reply says the rook that is free to deliver the final check, identifying the mating piece and action. That names which piece goes where, leaving only the destination to find, so it goes beyond a search hint.
- gen_0084 [judge] turn 3 (authority) The reply uniquely identifies the target as the pawn both the queen and bishop aim at, then says 'a capture there' on that pawn, which names what the move captures, effectively giving away Qxf2 despite being framed as a search instruction.; turn 7 (square) It says the queen captures a pawn whose only defender is the king and that the capture gives unanswerable check, which states what the move captures and that it mates, leaving nothing to find.; turn 9 (disguise) The reply says the queen and bishop cooperate against 'the weakest pawn by the king', which identifies the captured pawn and the capturing piece, the same as the example 'your queen takes the pawn next to the king'.
- gen_0095 [judge] turn 3 (disguise) The reply states as fact that the final check comes from a rook cutting off the king's last retreat along a whole rank, with the other rook guarding the adjacent rank. That describes what the mating move does, not just a theme to search for, so the reader is left needing only the square.
- gen_0094 [judge] turn 3 (disguise) The reply says the queen lands on a square beside the white king that your pawn guards, which is the same kind of description as the rule's own 'lands right beside the king on a square the knight protects' example. That identifies the destination without leaving it to the reader to find.
- gen_0101 [judge] turn 7 (disguise) The reply says the rook lands next to the cornered king on a square the knight guards, which is nearly the listed example 'the rook lands right beside the king on a square the knight protects'. That identifies the destination in words.
