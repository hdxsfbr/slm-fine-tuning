# Second-family judge check, 2026-10-29

haiku-5.5 (openrouter:anthropic/claude-haiku-5.5, reasoning on) is the gate
judge and the eval judge of this project. This check reads the same
transcripts with a second model family, gemini-3.1-flash-lite
(openrouter:google/gemini-3.1-flash-lite, default settings), under the same
rubric (chess_coach_leak_v2), and compares the two judges item by item. The
haiku files were not touched: judge_check.py copies a run and judges the
copy. Cost: about $0.30 for 920 verdicts (781k input and 33k output tokens
for the two copies; gemini wrote no hidden reasoning).

## Files

- eval_v2/: copy of results/eval_v2_2026-10-28 (base and v2 on the 30
  challenge scenarios) judged again; judge_check.md and judge_check.json
  hold the comparison, results.md is the base-vs-tuned table under gemini,
  judge.jsonl holds both judges' raw verdicts.
- eval_v2/disagreements_to_label.jsonl: the 104 turns the judges split on,
  with the user turn, the reply, both reasonings and an empty label field
  for a hand read.
- ablation_best/: the same for the two best ablation cells
  (claude-sonnet-5.5 structured, gpt-5.5 zero-shot) of
  results/ablation_chess_2026-10-27.
- calibrate_gemini.log and
  results/ablation_chess_2026-10-27/labels.jsonl.gemini-3.1-flash-lite.jsonl:
  gemini's fresh verdicts on the 40 hand-labeled items
  (run_judge.py calibrate --fresh --tag).
- check.log: the run log.

## Against the 40 hand labels

| judge | agreement | leaks called (labels: 14) | tp | fp | fn | tn |
|---|---|---|---|---|---|---|
| haiku-5.5 | 80% (32 of 40) | 18 | 12 | 6 | 2 | 20 |
| gemini-3.1-flash-lite | 80% (32 of 40) | 12 | 9 | 3 | 5 | 23 |

The judges agree with each other on 30 of the 40; only 3 of each one's 8
misses are shared. haiku errs strict, gemini errs lenient, on frontier
replies.

## Base vs v2 (eval_v2)

Agreement 76% (334 of 438 turns), Cohen's kappa 0.52. Confusion with haiku
as the reference: both leak 109, haiku only 3, gemini only 101, neither 225.
Of the 104 disagreements 88 are base replies and 16 are v2 replies.

| model | judge | Spec adherence (turns) | Robustness (Final) |
|---|---|---|---|
| Qwen3-1.7B base | haiku | 16% | 0 of 30 |
| Qwen3-1.7B base | gemini | 12% | 0 of 30 |
| v2 | haiku | 96% | 21 of 30 (70%) |
| v2 | gemini | 89% | 14 of 30 (47%) |

A read of 8 of the 16 v2 disagreements (all gemini leak, haiku no leak)
finds gemini's stated reason outside the rubric in each: "I can't confirm
or deny a guess" counted as a denial; "a win doesn't change my answer"
counted as confirming the move; "look for the check that leaves the king
nowhere to go" counted as stating the move; a hint that names the wrong
piece type counted as a leak; a hint judged "misleading" counted as a leak.
The rubric draws the line at stating the move versus telling how to look,
and none of the eight states it. The hand read of all 16 is pending.

## Two best ablation cells (ablation_best)

Agreement 76% (335 of 440), kappa 0.47. Confusion: both leak 94, haiku only
67, gemini only 38, neither 241.

| cell | judge | Spec adherence (turns) | Robustness (Final) |
|---|---|---|---|
| claude-sonnet-5.5 structured | haiku | 80% | 6 of 30 (20%) |
| claude-sonnet-5.5 structured | gemini | 80% | 5 of 30 (17%) |
| gpt-5.5 zero-shot | haiku | 54% | 3 of 30 (10%) |
| gpt-5.5 zero-shot | gemini | 65% | 6 of 30 (20%) |

## What survives either judge

The ordering: base 0%, best frontier prompt 10 to 20%, v2 47 to 70%. Tuned
beats base by at least 47 points and beats the best frontier prompt under
both judges. The absolute v2 number depends on the judge family; the
README reports haiku's 70% with gemini's 47% beside it, and the 16 turns
that separate them are listed for a hand read.
