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
- n<1K
---

# Hint-only chess coach conversations

Multi-turn conversations in which a chess coach is pressed, in many ways, to name the winning move in
the user's position and only ever hints, while answering unrelated chess questions fully with squares
and moves. Written by a frontier teacher model to seeded plans (persona x situation x pressure kinds x
hard negatives) over python-chess-verified mate-in-one positions, then filtered by a gate: structure,
dedupe, code checks (no square or move in any hint, squares required in answers), an LLM judge for hints
that state the move in words, and leakage against the evaluation set. The split is held out by position.

## Files

- `train.jsonl`: 805 rows, sha256 `39ddf3110352249405686d2f8cf9c36c4dc122e386e4120359600741a9225fa6`
- `synthetic_test.jsonl`: 102 rows, sha256 `9ccdb3f15f7a20843df77beb330980c544ce2bb026266f617018ab4debcb3e79`, positions disjoint from train
- `manifest.json`, `gate_report.md`: the gate's stages and counts

Row shape: `{"id", "family", "persona", "kinds", "messages": [{"role", "content"}, ...]}`; `kinds`
names the pressure kind of each user turn (`normal` marks a hard negative).

## Gate

| Stage | In | Out | Dropped |
|---|---|---|---|
| structure | 1200 | 1118 | 82 |
| dedupe | 1118 | 1118 | 0 |
| checks | 1118 | 1018 | 100 |
| judge | 1018 | 908 | 110 |
| leakage | 908 | 907 | 1 |

Judge: `openrouter:anthropic/claude-haiku-5.5`, rubric `chess_coach_leak_v2`, 7122 verdicts.
