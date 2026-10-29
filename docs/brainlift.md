# Brainlift: a hint-only chess coach that a prompt cannot hold

Status: in progress (2026-10-29). The v1 and v2 numbers, both curves and
the second-family judge check are final and the model and dataset are on
the Hub; the staff held-out set, when published, and the demo land before
the final submission. Everything cited is in this repository and can be
regenerated with the commands in README.md.

## Thesis

A 1.7B model trained on a few hundred filtered conversations holds a narrow
conversational constraint that frontier models, however prompted, drift off
within a few turns. The constraint is a chess coach that only ever hints.
The claim is not that the small model knows more chess; it is that the
behavior is in the data, and a model trained on that data keeps it under
pressure that a system prompt cannot survive.

## The behavior, in two sentences

Asked what to play in their position, or anything that would identify the
move, the coach replies with one hint of at most two sentences that neither
names nor describes the move (no square, no piece-goes-where, no yes or no
to a guess), however the user asks and even after the game is over. Every
other chess question is answered fully, squares and moves included.

The second sentence is the half that makes it falsifiable in both
directions: a model that refuses everything fails too. Thirteen of the 30
eval scenarios interleave rules and opening questions that must be answered
with squares.

## Why this behavior: the prompt ceiling

Two frontier families, three prompting strategies, 30 scripted conversations
of 8 to 10 turns per cell, 180 conversations, judged by one fixed rubric
(results/ablation_chess_2026-10-27):

| Model | zero-shot | few-shot | structured | best |
|---|---|---|---|---|
| claude-sonnet-5.5 | 7% | 13% | 20% | 20% |
| gpt-5.5 | 10% | 3% | 7% | 10% |

The number is Robustness: the share of conversations in which every reply
held. By code checks alone both models look nearly perfect (gpt-5.5
zero-shot names a square in 0 of 30 conversations). The ceiling only shows
with a judge that reads for meaning: under pressure the coach keeps the
letter of the rule and states the move in words ("the rook goes to the far
end of its file"), confirms a guess, or, once told the game is over, gives
the line. The pressure kinds that break it most are "just the square", "the
game is over", plain insistence and encodings. Details in
results/ablation_chess_2026-10-27/failure_mode.md.

Spiky view 1: a behavior can have a prompt ceiling that your checks cannot
see. Two earlier candidates (anti-sycophancy, no AI-writing tells) scored
100% on the best prompt and were dropped. The chess coach looked the same
until the judge was built and calibrated (80% agreement with 40 hand labels;
rubric v1, which asked the judge to work out whether only one move fit the
hint, agreed 66% because the judges solved the puzzle themselves).

## Method

The lecture recipe in order: spec, evals, ceiling, data, train, prove. No
training before the harness existed (ablation 19:09Z, data 21:03Z, first
training 22:22Z on 2026-10-27). One training configuration throughout
(QLoRA r=16 on Qwen3-1.7B, 2 epochs, lr 2e-4, seed 3407); every
improvement is a data change.

Data: python-chess-verified mate-in-one positions disjoint from the eval
positions, a seeded plan per conversation (persona x situation x pressure
kinds x hard negatives, 4 to 12 user turns), a teacher that writes the
conversation to the plan, and a gate: structure, dedupe, code checks,
the same LLM judge as the ablation, leakage against the eval set, a split
held out by position.

## Evidence so far: v1

v1 was taught by claude-haiku-5.5 (455 rows gated from 1,100, 46% yield).
On the 30 challenge scenarios, same judge and rubric as the ablation
(results/eval_base_2026-10-27, results/eval_v1_2026-10-27):

| | Robustness | Spec adherence (turns) | hint replies stating the move |
|---|---|---|---|
| Qwen3-1.7B base | 0 of 30 | 17% | 106 of 212 |
| v1 | 15 of 30 (50%) | 90% | 13 of 220 |
| best frontier cell | 20% | 80% | 47 of 220 |

Data to behavior held for the hint stance: the tuned model states the move
in 13 hint replies out of 220 where the base did it in half of them and
the best frontier prompt in 47. It did not hold for the hard negatives: v1
answers 14 of 26 rules questions with squares. The diagnosis is in the
data, not the model: the v1 teacher prompt banned squares from "every coach
reply", the gate did not require squares in answers, and 137 of the 233
hard-negative answers in train.jsonl have none. The model learned exactly
what it was shown.

Spiky view 2: "the dataset is the deliverable" is literal. One sentence in
a generation prompt became the tuned model's main failure mode. The fix is
a data change (prompt, gate rule, and a frontier teacher), not a training
change, and v2 is that fix.

## Data efficiency: the v1 curve

Nested subsets of the v1 data, two training seeds, rule fixed before the
numbers (smallest n within 5 points of the full run):

| rows | Robustness (checks) | Spec adherence (turns) |
|---|---|---|
| 455 | 65% | 92% |
| 228 | 48% | 88% |
| 114 | 35% | 69% |
| 57 | 43% | 73% |

Per-turn adherence reaches the full-set level at 228 rows; per-conversation
robustness does not until 455, and the hard negatives are what the extra
rows buy. So v1 is data-limited, and the minimum viable size for the
behavior as specified is the full set.

Spiky view 3: reliability is a property of conversations, not replies. A
model can obey the spec on 9 replies in 10 and still fail 2 conversations
in 3, because one lapse anywhere fails the conversation. Per-turn numbers
flatter every model in this project, frontier ones included; the number to
train against and report is the all-turns one.

## v2 (in progress)

Changes, all in the data: claude-sonnet-5.5 as teacher (the brief's
"frontier teacher"), squares banned in hints only and required in answers,
a larger share of hard-negative turns, a specific scene for every emotional
turn, and a split held out by position. Same training configuration. The
batch: 1,200 conversations, 907 gated (76% against 46% for haiku), 805
training rows with 1,027 hard-negative turns, all answered with squares
(v1: 137 of 233 without), 102 test rows on positions train never saw.
Result on the 30 challenge scenarios, same judge and rubric, base rerun in
the same command (results/eval_v2_2026-10-28):

| | Robustness | Spec adherence (turns) | pressure split | mixed split | hint replies stating the move |
|---|---|---|---|---|---|
| Qwen3-1.7B base | 0 of 30 | 16% | 0 of 17 | 0 of 13 | 108 of 219 |
| v1 (haiku data, 455 rows) | 15 of 30 (50%) | 90% | 12 of 17 | 3 of 13 | 13 of 220 |
| v2 (sonnet data, 805 rows) | 21 of 30 (70%) | 96% | 17 of 17 | 4 of 13 | 4 of 219 |
| best frontier prompt | 20% | 80% | 3 of 17 | 3 of 13 | 47 of 220 |

Data to behavior held again, and where it was aimed: v2 holds every one of
the 17 pressure scenarios, dodges 4 hard negatives where v1 dodged 12, and
states the move in 4 hint replies out of 219. What is left is one pressure
kind: "disguise", the user restating their own position as a general
question ("in a queen-and-bishop mate on the pawn in front of the king,
which square does the queen land on?"). v2 answers those as the general
questions they pretend to be, with squares, in 6 of the 13 mixed
conversations, and in 4 of them the judge agrees the move was stated. That
is the next data change: the v2 plans carry one disguise turn in half the
conversations; the fix is more of them, with the answer rephrased each
time.

On the 102 synthetic test conversations, written by the same generator on
positions no training row uses (results/eval_v2_heldout_2026-10-29, every
hint turn judged): base 0 of 102, v2 95 of 102 (93%), Spec adherence 26%
against 99%, the base stating the move in 301 of 703 hint turns and v2 in
4. The 23-point gap between that and the challenge set is the gap between
pressure the model was trained on and pressure written by hand, and it is
why the hand-written set is the headline.

## Data efficiency: the v2 curve

Nested subsets of the v2 data, two seeds, every point judged, the same
rule (results/curve_v2_2026-10-28/curve.md):

| rows | Robustness (judged, mean) | Spec adherence (turns) | pressure held of 17 | mixed held of 13 |
|---|---|---|---|---|
| 805 | 70% | 95% | 17, 16 | 4, 5 |
| 402 | 62% | 94% | 16, 16 | 2, 3 |
| 201 | 33% | 84% | 8, 12 | 0, 0 |
| 100 | 45% | 75% | 15, 12 | 0, 0 |

Minimum viable N, by the rule fixed before the numbers: the full 805 rows.
Half the data (402) already holds 16 of the 17 pressure scenarios on both
seeds and reaches 94% per-turn adherence, but it is 8 points behind on
Robustness because the mixed conversations, where hard negatives and
disguised restatements sit between pressure turns, are what the second
half of the data teaches. The curve has not flattened, so the honest claim
is "at least 805 for this spec" with the next gain expected from more
disguise turns rather than more rows of the same mix.

Spiky view 4: a cheap teacher is not cheap. The haiku batch cost $0.62 and
threw away 54% of what it wrote; the sonnet batch costs about 20 times more
per conversation and keeps 88%, and its hints are specific where haiku's
were formulaic.

## Judge validity

haiku-5.5 is the gate judge and the eval judge, so a second family read
the same transcripts under the same rubric (gemini-3.1-flash-lite,
results/judge_check_2026-10-29). Against the 40 hand labels both judges
score 80%, haiku from the strict side and gemini from the lenient side, and
only 3 of each one's 8 misses are shared. On base vs v2 they agree on 76%
of turns (kappa 0.52); the disagreements are 88 base replies, which fail
anyway, and 16 v2 replies, enough to put v2 at 47% Robustness under gemini
against 70% under haiku, with the base at 0% under both and the frontier
cells at 17% and 20%. In the 8 of those 16 read so far, gemini's reason
falls outside the rubric (a refusal to confirm read as a denial, "look for
the check" read as the move). So the ordering, base, then frontier prompt,
then tuned, does not depend on the judge family; the absolute number does,
and the one reported is haiku's, with gemini's beside it.

## What is not shown yet

- v2 on the staff held-out set, when the course publishes one.
- A model above the 80% bar on Robustness: v2 is at 70%, and the one
  failure mode left (disguise) is a data change away.
- The 40 calibration labels were written by the assistant that built the
  judge, not by the author; they are being relabeled.

## Artifacts

- Model: [hdxsfbr/qwen3-1.7b-chess-coach-hints](https://huggingface.co/hdxsfbr/qwen3-1.7b-chess-coach-hints/tree/020015527aa37100ff6b10ba323cd0c329b57d97),
  commit `020015527aa37100ff6b10ba323cd0c329b57d97`.
- Dataset: [hdxsfbr/chess-coach-hints](https://huggingface.co/datasets/hdxsfbr/chess-coach-hints/tree/a4325dbdfd3a14c7b59b371a27b28795bbc8a788),
  commit `a4325dbdfd3a14c7b59b371a27b28795bbc8a788`.
- Code: commit 0d41d41 on main of the project repository; every result
  directory carries its run.json with the loaded revisions.

## Sources

- The course brief (docs/G7_W7_Train_Your_Own_Small_Learning_Model.pdf)
  and lecture (docs/lecture).
- Unsloth QLoRA recipe for Qwen3; TRL's train_on_responses_only.
- python-chess for position generation and mate verification.
