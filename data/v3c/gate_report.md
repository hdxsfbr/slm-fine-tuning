# Merged data report

- Merged: 2026-10-30T17:56:31+00:00
- Shuffle seed: 0

| Source | train rows | test rows | gated |
|---|---|---|---|
| `data/v2` | 805 | 102 | 2026-10-28T16:52:18+00:00 |
| `data/v3_extra` | 250 | 27 | 2026-10-30T16:53:20+00:00 |
| `data/v3b_extra` | 243 | 26 | 2026-10-30T17:43:36+00:00 |

Each source was gated on its own (structure, dedupe, code checks, judge, leakage, split held out by position); its gate_report.md has the stage counts. Row ids carry the source name as a prefix.

## Output

- `train.jsonl`: 1298 rows, sha256 `0c91f2daa4421eea3a31319febbd9049d2c893c09ba88d02c836a5e302b0a489`
- `synthetic_test.jsonl`: 155 rows, sha256 `cd974a7e5beb07463ca2bc4f4e2ce29414dadcc8ba3b1d9efea45af049444a83`

Held out by position: 99 test placements, 0 shared with train.

## Coverage of the training rows

Families: QB 97, RB 95, QR 94, R 92, RN+shield 92, QB+shield 89, Q 87, RN 85, QN 84, RR+shield 83, QR+shield 81, RR 76, epaulette 21, box 20, fools 20, smothered 20, opera 19, boden 19, legals 19, promotion 19, anastasia 18, back_rank 16, arabian 15, ladder 13, damiano 12, scholars 12

User-turn kinds: normal 1847, direct 1477, disguise 1345, insist 804, square 732, format 681, confirm 649, emotional 580, authority 570, narrow 536, yesno 521, enumerate 353, roleplay 340, closure 262, elimination 235

Personas: arbiter 95, coach 94, skeptic 86, beginner 85, composer 84, titled 82, flatterer 82, returning 82, blitz 81, esl 81, formal 77, streamer 76, parent 76, kid 75, club_player 73, programmer 69
