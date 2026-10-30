---
license: apache-2.0
language:
- en
task_categories:
- text-generation
tags:
- chess
- behavior-fine-tuning
- synthetic
size_categories:
- 1K<n<10K
---

# Hint-only chess coach conversations

Multi-turn conversations in which a chess coach is pressed, in many ways, to name the winning move in
the user's position and only ever hints, while answering unrelated chess questions fully with squares
and moves. Written by a frontier teacher model to seeded plans (persona x situation x pressure kinds x
hard negatives) over python-chess-verified mate-in-one positions, then filtered by a gate: structure,
dedupe, code checks (no square or move in any hint, squares required in answers), an LLM judge for hints
that state the move in words, and leakage against the evaluation set. The split is held out by position.

## Files

- `train.jsonl`: 1298 rows, sha256 `0c91f2daa4421eea3a31319febbd9049d2c893c09ba88d02c836a5e302b0a489`
- `synthetic_test.jsonl`: 155 rows, sha256 `cd974a7e5beb07463ca2bc4f4e2ce29414dadcc8ba3b1d9efea45af049444a83`, positions disjoint from train
- `manifest.json`, `gate_report.md`: the gate's stages and counts

Row shape: `{"id", "family", "persona", "kinds", "messages": [{"role", "content"}, ...]}`; `kinds`
names the pressure kind of each user turn (`normal` marks a hard negative).

## Gate

This version merges 3 gated batches; row ids carry the batch name as a prefix. Each batch went through
the same gate on its own, and the merge checked that the test rows share no position with the train rows
(99 held-out positions, 0 shared).

### `v2`: 805 train rows, 102 test rows

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 1200 | 1118 | 82 |
| dedupe | 1118 | 1118 | 0 |
| checks | 1118 | 1018 | 100 |
| judge | 1018 | 908 | 110 |
| leakage | 908 | 907 | 1 |

Judge: `openrouter:anthropic/claude-haiku-5.5`, rubric `chess_coach_leak_v2`, 7122 verdicts.

### `v3_extra`: 250 train rows, 27 test rows

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 350 | 331 | 19 |
| dedupe | 331 | 331 | 0 |
| checks | 331 | 314 | 17 |
| judge | 314 | 277 | 37 |
| leakage | 277 | 277 | 0 |

Judge: `openrouter:anthropic/claude-haiku-5.5`, rubric `chess_coach_leak_v2`, 2228 verdicts.

### `v3b_extra`: 243 train rows, 26 test rows

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 350 | 341 | 9 |
| dedupe | 341 | 341 | 0 |
| checks | 341 | 327 | 14 |
| judge | 327 | 269 | 58 |
| leakage | 269 | 269 | 0 |

Judge: `openrouter:anthropic/claude-haiku-5.5`, rubric `chess_coach_leak_v2`, 2278 verdicts.
