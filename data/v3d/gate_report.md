# Merged data report

- Merged: 2026-11-01T00:11:29+00:00
- Shuffle seed: 0

| Source | train rows | test rows | gated |
|---|---|---|---|
| `data/v2` | 805 | 102 | 2026-10-28T16:52:18+00:00 |
| `data/v3_extra` | 250 | 27 | 2026-10-30T16:53:20+00:00 |
| `data/v3b_extra` | 243 | 26 | 2026-10-30T17:43:36+00:00 |
| `data/v3d_extra` | 110 | 12 | 2026-11-01T00:11:28+00:00 |

Each source was gated on its own (structure, dedupe, code checks, judge, leakage, split held out by position); its gate_report.md has the stage counts. Row ids carry the source name as a prefix.

## Output

- `train.jsonl`: 1408 rows, sha256 `b0cae531dcd2f73820f79eb9216dd1c414a69fee357fceca99d0f2ee2d387166`
- `synthetic_test.jsonl`: 167 rows, sha256 `a5a36d2d9bbcd232468c27b4bd98cd71c9fbb6e428047fab29904866d7205bfb`

Held out by position: 111 test placements, 0 shared with train.

## Coverage of the training rows

Families: QB 108, R 104, QR 103, RB 103, QB+shield 100, RN+shield 98, RN 95, Q 95, QN 93, RR+shield 90, QR+shield 90, RR 86, epaulette 21, smothered 20, box 20, fools 20, promotion 19, opera 19, legals 19, boden 19, anastasia 18, back_rank 16, arabian 15, ladder 13, damiano 12, scholars 12

User-turn kinds: normal 2034, direct 1587, disguise 1582, insist 862, square 789, format 724, confirm 693, authority 617, emotional 613, narrow 570, yesno 542, enumerate 378, roleplay 358, closure 278, elimination 255

Personas: arbiter 101, coach 97, skeptic 94, composer 92, titled 91, beginner 90, returning 89, flatterer 89, esl 88, blitz 86, streamer 85, kid 84, parent 84, formal 83, programmer 78, club_player 77
