# Data gate report

- Gated: 2026-10-27T21:56:07+00:00
- Input rows: 1100

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 1100 | 901 | 199 |
| dedupe | 901 | 901 | 0 |
| checks | 901 | 664 | 237 |
| judge | 664 | 505 | 159 |
| leakage | 505 | 505 | 0 |

Judge: openrouter:anthropic/claude-haiku-5.5, rubric chess_coach_leak_v2, 4533 verdicts, 5085048 input and 1970462 output tokens.

## Output

- `train.jsonl`: 455 rows, sha256 `109377ecb7b35e3c4c40c0e5ce992b075c777becbf441090520d5365e8a483ac`
- `synthetic_test.jsonl`: 50 rows, sha256 `d6660fb422cb379d024342810bcb23ac591c5de634674f1a92abaa8fe7e37c7d`

## Coverage of the gated rows

Families: Q 55, QB 53, QB+shield 29, QN 62, QR 60, QR+shield 29, R 51, RB 42, RN 47, RN+shield 14, RR 44, RR+shield 19

User-turn kinds: direct 594, insist 341, square 296, format 294, authority 260, confirm 258, normal 251, emotional 230, narrow 224, yesno 205, disguise 204, roleplay 150, enumerate 150, elimination 113, closure 96

Personas: returning 38, blitz 38, programmer 37, formal 36, arbiter 35, skeptic 34, coach 32, parent 32, composer 32, beginner 30, kid 29, esl 29, club_player 28, flatterer 28, titled 26, streamer 21

## Rejections by stage and reason (first 40)

- gen_0010 [structure] turn count 4, plan wants 6
- gen_0012 [structure] turn count 9, plan wants 10
- gen_0026 [structure] turn count 4, plan wants 5
- gen_0025 [structure] turn count 6, plan wants 7
- gen_0024 [structure] turn count 7, plan wants 8
- gen_0030 [structure] turn count 9, plan wants 10
- gen_0034 [structure] turn count 4, plan wants 8
- gen_0041 [structure] turn count 5, plan wants 6
- gen_0045 [structure] turn count 4, plan wants 5
- gen_0050 [structure] turn count 6, plan wants 7
- gen_0054 [structure] turn count 7, plan wants 8
- gen_0063 [structure] turn count 8, plan wants 9
- gen_0081 [structure] turn count 6, plan wants 7
- gen_0091 [structure] turn count 4, plan wants 5
- gen_0106 [structure] turn count 8, plan wants 9
- gen_0107 [structure] turn count 6, plan wants 8
- gen_0110 [structure] turn count 9, plan wants 10
- gen_0113 [structure] turn count 10, plan wants 9
- gen_0120 [structure] turn count 7, plan wants 8
- gen_0119 [structure] turn count 9, plan wants 10
- gen_0122 [structure] turn count 5, plan wants 8
- gen_0123 [structure] turn count 6, plan wants 8
- gen_0134 [structure] turn count 8, plan wants 9
- gen_0135 [structure] turn count 8, plan wants 9
- gen_0143 [structure] turn count 4, plan wants 5
- gen_0146 [structure] turn count 6, plan wants 7
- gen_0151 [structure] turn count 5, plan wants 6
- gen_0154 [structure] turn count 9, plan wants 10
- gen_0161 [structure] turn count 5, plan wants 4
- gen_0159 [structure] turn count 9, plan wants 10
- gen_0174 [structure] turn count 5, plan wants 6
- gen_0178 [structure] turn count 7, plan wants 8
- gen_0184 [structure] turn count 7, plan wants 8
- gen_0190 [structure] turn count 7, plan wants 8
- gen_0189 [structure] turn count 7, plan wants 8
- gen_0193 [structure] turn count 5, plan wants 10
- gen_0198 [structure] turn count 5, plan wants 6
- gen_0197 [structure] turn count 7, plan wants 10
- gen_0201 [structure] turn count 7, plan wants 8
- gen_0210 [structure] turn count 5, plan wants 6
