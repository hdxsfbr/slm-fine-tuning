# Merged data report

- Merged: 2026-10-30T17:43:36+00:00
- Shuffle seed: 0

| Source | train rows | test rows | gated |
|---|---|---|---|
| `data/v2` | 805 | 102 | 2026-10-28T16:52:18+00:00 |
| `data/v3b_extra` | 243 | 26 | 2026-10-30T17:43:36+00:00 |

Each source was gated on its own (structure, dedupe, code checks, judge, leakage, split held out by position); its gate_report.md has the stage counts. Row ids carry the source name as a prefix.

## Output

- `train.jsonl`: 1048 rows, sha256 `16a290ed75f9a5c517c17619c385969930772a4d69203f6d2c19be760d9ac611`
- `synthetic_test.jsonl`: 128 rows, sha256 `690f4cabdedda55f776eb1412c2209a931e712596e8a96d4f7d16d7b8e7b08cd`

Held out by position: 72 test placements, 0 shared with train.

## Coverage of the training rows

Families: R 74, QB 73, RB 72, QR 71, RN+shield 70, Q 66, QN 66, QB+shield 66, RR+shield 64, RN 64, QR+shield 61, RR 58, epaulette 21, smothered 20, box 20, fools 20, boden 19, legals 19, opera 19, promotion 19, anastasia 18, back_rank 16, arabian 15, ladder 13, damiano 12, scholars 12

User-turn kinds: normal 1435, direct 1227, disguise 797, insist 667, square 616, format 577, confirm 555, emotional 495, authority 470, narrow 462, yesno 450, enumerate 299, roleplay 290, closure 210, elimination 198

Personas: coach 77, arbiter 73, esl 68, flatterer 68, skeptic 67, beginner 67, kid 67, titled 67, blitz 66, composer 66, returning 66, formal 62, parent 62, streamer 61, club_player 57, programmer 54
