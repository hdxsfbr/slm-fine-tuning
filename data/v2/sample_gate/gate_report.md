# Data gate report

- Gated: 2026-10-28T15:46:41+00:00
- Input rows: 50

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 50 | 48 | 2 |
| dedupe | 48 | 48 | 0 |
| checks | 48 | 45 | 3 |
| judge | 45 | 44 | 1 |
| leakage | 44 | 44 | 0 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 324 verdicts, 362725 input and 127192 output tokens.

## Output

- `train.jsonl`: 44 rows, sha256 `ac6ee5329b0267e81e5097edc0e339c4719c780bf3b36766db8bca24fe3508dc`
- `synthetic_test.jsonl`: 0 rows, sha256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Coverage of the gated rows

Families: Q 3, QB 4, QB+shield 3, QN 4, QR 3, QR+shield 3, R 4, RB 3, RN 4, RN+shield 4, RR 5, RR+shield 4

User-turn kinds: normal 58, direct 55, format 28, yesno 27, confirm 26, insist 25, emotional 25, square 25, narrow 23, enumerate 17, disguise 16, roleplay 14, authority 14, elimination 12, closure 9

Personas: coach 7, titled 6, formal 5, blitz 4, composer 4, club_player 3, returning 2, flatterer 2, parent 2, streamer 2, arbiter 2, programmer 2, esl 1, beginner 1, skeptic 1

## Rejections by stage and reason (first 40)

- gen_0010 [structure] first user turn does not carry the FEN
- gen_0024 [structure] turn count 11, plan wants 10
- gen_0017 [checks] turn 3 (normal) no squares in the answer
- gen_0032 [checks] turn 3 (normal) no squares in the answer
- gen_0048 [checks] turn 4 (normal) no squares in the answer
- gen_0030 [judge] turn 9 (closure) The reply says the answer is a single queen check that leaves Black's king with zero squares, which describes a mating queen check and so nearly states the move, going beyond a search instruction like the allowed examples.
