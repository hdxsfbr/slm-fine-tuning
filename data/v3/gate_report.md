# Merged data report

- Merged: 2026-10-30T16:53:20+00:00
- Shuffle seed: 0

| Source | train rows | test rows | gated |
|---|---|---|---|
| `data/v2` | 805 | 102 | 2026-10-28T16:52:18+00:00 |
| `data/v3_extra` | 250 | 27 | 2026-10-30T16:53:20+00:00 |

Each source was gated on its own (structure, dedupe, code checks, judge, leakage, split held out by position); its gate_report.md has the stage counts. Row ids carry the source name as a prefix.

## Output

- `train.jsonl`: 1055 rows, sha256 `bc3721b03454a933a1605735b5131b24dbfd136c13b858e84003e97ded12c7e9`
- `synthetic_test.jsonl`: 129 rows, sha256 `f4239a27b1d2e56841bde9884f821de952695ebb95c71628f1eb9018320449a1`

Held out by position: 73 test placements, 0 shared with train.

## Coverage of the training rows

Families: QB 97, RB 95, QR 94, RN+shield 92, R 92, QB+shield 89, Q 87, RN 85, QN 84, RR+shield 83, QR+shield 81, RR 76

User-turn kinds: normal 1439, direct 1234, disguise 826, insist 668, square 619, format 587, confirm 549, authority 497, emotional 490, narrow 463, yesno 450, enumerate 310, roleplay 288, closure 206, elimination 198

Personas: arbiter 80, coach 78, composer 71, blitz 68, beginner 68, returning 68, flatterer 68, skeptic 66, streamer 65, titled 65, club_player 64, programmer 61, esl 61, formal 59, kid 57, parent 56
