# Data gate report

- Gated: 2026-10-28T16:52:18+00:00
- Input rows: 1200

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 1200 | 1118 | 82 |
| dedupe | 1118 | 1118 | 0 |
| checks | 1118 | 1018 | 100 |
| judge | 1018 | 908 | 110 |
| leakage | 908 | 907 | 1 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 7122 verdicts, 7973241 input and 2833915 output tokens.

## Output

- `train.jsonl`: 805 rows, sha256 `39ddf3110352249405686d2f8cf9c36c4dc122e386e4120359600741a9225fa6`
- `synthetic_test.jsonl`: 102 rows, sha256 `9ccdb3f15f7a20843df77beb330980c544ce2bb026266f617018ab4debcb3e79`

## Coverage of the gated rows

Families: Q 75, QB 83, QB+shield 75, QN 76, QR 79, QR+shield 69, R 82, RB 82, RN 72, RN+shield 78, RR 65, RR+shield 71

User-turn kinds: normal 1168, direct 1109, insist 614, square 566, format 541, confirm 518, emotional 456, authority 440, narrow 438, yesno 423, disguise 318, enumerate 284, roleplay 260, elimination 179, closure 170

Personas: coach 66, arbiter 64, beginner 60, flatterer 59, returning 58, titled 57, streamer 57, composer 56, skeptic 56, programmer 55, kid 55, formal 54, blitz 54, club_player 53, esl 53, parent 50

## Rejections by stage and reason (first 40)

- gen_0010 [structure] first user turn does not carry the FEN
- gen_0024 [structure] turn count 11, plan wants 10
- gen_0051 [structure] turn count 3, plan wants 11
- gen_0058 [structure] first user turn does not carry the FEN
- gen_0067 [structure] message 6 has 13 characters
- gen_0074 [structure] turn count 5, plan wants 4
- gen_0076 [structure] first user turn does not carry the FEN
- gen_0077 [structure] first user turn does not carry the FEN
- gen_0109 [structure] message 10 has 13 characters
- gen_0132 [structure] kinds ['direct', 'disguise', 'disguise', 'roleplay', 'yesno', 'narrow', 'normal', 'insist', 'narrow'] differ from plan ['direct', 'disguise', 'enumerate', 'roleplay', 'yesno', 'narrow', 'normal', 'insist', 'narrow']
- gen_0148 [structure] turn count 10, plan wants 9
- gen_0164 [structure] kinds ['direct', 'insist', 'insist', 'direct', 'confirm', 'yesno', 'elimination', 'disguise', 'authority', 'format'] differ from plan ['direct', 'insist', 'narrow', 'direct', 'confirm', 'yesno', 'elimination', 'disguise', 'authority', 'format']
- gen_0206 [structure] kinds ['direct', 'insist', 'insist', 'insist', 'insist', 'insist', 'insist', 'insist'] differ from plan ['direct', 'insist', 'insist', 'confirm', 'square', 'narrow', 'enumerate', 'narrow']
- gen_0244 [structure] kinds ['direct', 'insist', 'insist', 'insist', 'authority', 'confirm', 'emotional'] differ from plan ['direct', 'insist', 'insist', 'yesno', 'authority', 'confirm', 'emotional']
- gen_0282 [structure] first user turn does not carry the FEN
- gen_0297 [structure] first user turn does not carry the FEN
- gen_0316 [structure] turn count 7, plan wants 6
- gen_0320 [structure] first user turn does not carry the FEN
- gen_0323 [structure] first user turn does not carry the FEN
- gen_0328 [structure] first user turn does not carry the FEN
- gen_0352 [structure] turn count 7, plan wants 6
- gen_0353 [structure] turn count 11, plan wants 10
- gen_0360 [structure] first user turn does not carry the FEN
- gen_0384 [structure] first user turn does not carry the FEN
- gen_0390 [structure] turn count 9, plan wants 8
- gen_0404 [structure] first user turn does not carry the FEN
- gen_0406 [structure] first user turn does not carry the FEN
- gen_0448 [structure] first user turn does not carry the FEN
- gen_0472 [structure] first user turn does not carry the FEN
- gen_0516 [structure] turn count 5, plan wants 6
- gen_0514 [structure] turn count 8, plan wants 9
- gen_0532 [structure] kinds ['direct', 'insist', 'insist', 'enumerate', 'normal', 'authority', 'direct', 'format', 'narrow'] differ from plan ['direct', 'insist', 'enumerate', 'insist', 'normal', 'authority', 'direct', 'format', 'narrow']
- gen_0551 [structure] first user turn does not carry the FEN
- gen_0566 [structure] first user turn does not carry the FEN
- gen_0613 [structure] first user turn does not carry the FEN
- gen_0625 [structure] kinds ['direct', 'insist', 'infinite', 'yesno'] differ from plan ['direct', 'insist', 'roleplay', 'yesno']
- gen_0633 [structure] kinds ['direct', 'normal', 'normal', 'narrow', 'enumerate', 'narrow', 'closure', 'authority'] differ from plan ['direct', 'normal', 'normal', 'narrow', 'enumerate', 'square', 'closure', 'authority']
- gen_0661 [structure] turn count 4, plan wants 7
- gen_0673 [structure] turn count 10, plan wants 9
- gen_0692 [structure] first user turn does not carry the FEN
