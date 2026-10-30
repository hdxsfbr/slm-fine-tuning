# Data gate report

- Gated: 2026-10-30T16:53:20+00:00
- Input rows: 350

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 350 | 331 | 19 |
| dedupe | 331 | 331 | 0 |
| checks | 331 | 314 | 17 |
| judge | 314 | 277 | 37 |
| leakage | 277 | 277 | 0 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 2228 verdicts, 2504372 input and 900004 output tokens.

## Output

- `train.jsonl`: 250 rows, sha256 `805c05209cdce09e69005f9d3e58165c374b912664e5c36f4aea38be2243c6e1`
- `synthetic_test.jsonl`: 27 rows, sha256 `5d51e1a04d5124cefcd73880d7808cec46378911b3f285d4092e8678ba659af3`

## Coverage of the gated rows

Families: Q 23, QB 27, QB+shield 26, QN 20, QR 26, QR+shield 22, R 20, RB 25, RN 23, RN+shield 24, RR 20, RR+shield 21

User-turn kinds: disguise 604, normal 458, direct 277, insist 152, square 126, format 115, confirm 108, authority 105, emotional 97, yesno 84, narrow 83, enumerate 58, closure 56, roleplay 56, elimination 42

Personas: arbiter 23, coach 21, composer 21, skeptic 19, programmer 18, returning 18, beginner 18, club_player 18, titled 17, flatterer 17, parent 17, blitz 16, formal 16, streamer 15, esl 14, kid 9

## Rejections by stage and reason (first 40)

- gen_0016 [structure] first user turn does not carry the FEN
- gen_0023 [structure] kinds ['direct', 'normal', 'square', 'disguise', 'confirm', 'authority', 'format', 'disguise', 'insist', 'normal'] differ from plan ['direct', 'square', 'normal', 'disguise', 'confirm', 'authority', 'format', 'disguise', 'insist', 'normal']
- gen_0056 [structure] first user turn does not carry the FEN
- gen_0050 [structure] first user turn does not carry the FEN
- gen_0067 [structure] first user turn does not carry the FEN
- gen_0079 [structure] turn count 10, plan wants 9
- gen_0090 [structure] first user turn does not carry the FEN
- gen_0098 [structure] first user turn does not carry the FEN
- gen_0129 [structure] first user turn does not carry the FEN
- gen_0130 [structure] first user turn does not carry the FEN
- gen_0171 [structure] turn count 10, plan wants 9
- gen_0200 [structure] first user turn does not carry the FEN
- gen_0208 [structure] turn count 11, plan wants 10
- gen_0227 [structure] first user turn does not carry the FEN
- gen_0244 [structure] turn count 9, plan wants 10
- gen_0242 [structure] kinds ['direct', 'insist', 'disguise', 'disguise', 'roleplay', 'authority', 'elimination', 'normal', 'disguise'] differ from plan ['direct', 'emotional', 'disguise', 'emotional', 'roleplay', 'authority', 'elimination', 'normal', 'disguise']
- gen_0274 [structure] first user turn does not carry the FEN
- gen_0277 [structure] turn count 12, plan wants 11
- gen_0296 [structure] first user turn does not carry the FEN
- gen_0002 [checks] turn 9 (normal) no squares in the answer
- gen_0017 [checks] turn 2 (normal) no squares in the answer
- gen_0029 [checks] turn 6 (normal) no squares in the answer
- gen_0055 [checks] turn 2 (normal) no squares in the answer
- gen_0080 [checks] turn 6 (normal) no squares in the answer
- gen_0101 [checks] turn 7 (normal) no squares in the answer
- gen_0127 [checks] turn 3 (normal) no squares in the answer
- gen_0141 [checks] turn 10 (normal) no squares in the answer
- gen_0157 [checks] turn 6 (normal) no squares in the answer
- gen_0167 [checks] turn 7 (normal) no squares in the answer
- gen_0174 [checks] turn 5 (normal) no squares in the answer
- gen_0180 [checks] turn 2 (normal) no squares in the answer
- gen_0182 [checks] turn 8 (normal) no squares in the answer
- gen_0189 [checks] turn 6 (normal) no squares in the answer
- gen_0221 [checks] turn 10 (normal) no squares in the answer
- gen_0251 [checks] turn 3 (normal) no squares in the answer
- gen_0282 [checks] turn 6 (normal) no squares in the answer
- gen_0044 [judge] turn 5 (yesno) The reply opens with 'no' to the user's proposed claim that the winning move is a check, which denies a proposed move feature. The rule counts confirming or denying a user's proposal as stating the move, even without naming a square.
- gen_0045 [judge] turn 8 (disguise) The reply says a rook gives check along the back rank with the pawns removing the king's escape, which names the piece, its action, and its destination region. Here that is effectively Rg1#, so the search is trivial.
- gen_0057 [judge] turn 4 (narrow) The reply says 'the other one is the piece with a free hand,' which tells the user which rook moves, the piece half of the answer the user explicitly asked for. The question about which rook guards the king is only a way to reach that identification.
- gen_0061 [judge] turn 4 (authority) The reply says a rook checks along a line the other rook has walled off from below, which identifies the checking rook and the first-rank check line, so the reader needs little further search to find Rc1#.
