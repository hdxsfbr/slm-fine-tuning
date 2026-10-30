# Plan: the lecture recipe applied to this project

Sources: the lecture slides and companion lab (local copies in `docs/lecture/`),
the brief (`docs/G7_W7_Train_Your_Own_Small_Learning_Model.pdf`), and the pilot
results in `results/pilot_2026-10-27/`. The recipe is
Spec -> Evals -> Ceiling -> Data -> Train -> Prove, and we follow it unless a
section below says why not.

## Where we stand against the recipe

| Stage | Lecture says | We have | Gap |
|---|---|---|---|
| Spec | 1-2 sentences, binary, narrow, names the pressure case | Two candidate specs, both falsifiable | Both failed the ceiling test, so a new spec is needed |
| Evals | 30+ scenarios, code checks, calibrated LLM judge, JSONL transcripts, one-command base vs tuned | Scenarios (15 and 10), code checks, JSONL transcripts, behavior-module contract | 30+ scenarios, the judge and its calibration, `eval.py` |
| Ceiling | 2+ families x 3 strategies x 30+ scenarios, same judge; "no plateau: pick a harder target" | Ran 2 families x 3 strategies x 15/10 scenarios: 100% everywhere | We are in the "pick a harder target" branch |
| Data | Teacher writes on-spec by construction; personas x situations x difficulty x length; gate; leakage check; hashed dataset | Nothing | Build |
| Train | Qwen3-1.7B QLoRA with the slide's config, chat template, responses only | Nothing | Build |
| Diagnose | Name one failure mode, fix with v2 data, same config, report delta | Nothing | Build |
| Curve | N, N/2, N/4, N/8 nested, same evals, rule fixed before looking | Nothing | Build |
| Prove | HF Hub + commit hash, manifest, raw judge JSONL, `eval.py --model --revision --eval-set` | Transcripts and results.md from the pilot | Build |

The pilot harness is kept: provider layer (OpenAI-compatible + Anthropic, retries,
OpenRouter 402 handling, `--resume`), behavior-module contract, runner, report.
The lecture's `LLM` class and our `clients.py` do the same job; ours already
handles the failure modes we hit.

## Step 1: a harder behavior

The lecture's ceiling test: a well-prompted base model cannot do it every time,
at turn 20, under pressure (direct ask, pushback after refusal, long
conversations, malformed input). Our two candidates were beaten at turn 3 and
turn 1, so the next spec must put the pressure where frontier models actually
drift: being asked to break the rule repeatedly, and being asked in a way that
makes breaking it look helpful.

The lecture's own example (decline and redirect) was rejected as too close to
the material, and the domain is chess or music by choice. The shape that
survives the ceiling test is a rule the model knows how to follow but caves
on under pressure, not a capability it lacks: a tutor that never gives the
answer.

**Hint-only chess coach (chosen for the pilot).** When the user asks what to
play in their position, or anything whose answer would name a move or a
square in it (which piece, where to, what is attacked, whether a guess is
right, what the opponent plays), the coach replies with one hint of at most
two sentences that names no square and no move, in any notation, spelled out
or encoded. The rule holds when the user insists, claims credentials, asks
for just the piece or just the square, asks for confirmation of a guess, says
the game is over, or restates the position as a general question. Every
other chess question (rules, openings, famous games, general patterns,
positions that are not the user's) is answered fully, squares and moves
included.

- Pressure cases, all scripted as 8-turn conversations: insistence,
  credentials, narrowing ("just the piece", "just the square"), yes/no
  fishing, guess confirmation, emotional appeals, encodings (code block,
  JSON, German notation, NATO alphabet, reversed), "the game is over", and
  the same position re-described as a general question.
- Hard negatives: rules and opening questions inside the puzzle conversation
  that must be answered with squares (how castling works, what a knight on
  d4 attacks, the Ruy Lopez moves, Scholar's Mate when it is not the user's
  position). Without them the student learns to refuse everything.
- Code checks: squares, algebraic and coordinate notation, castling, and
  spelled-out squares on hint turns; an `expect` regex on hard negatives;
  sentence count on hints; affirmations on confirm turns. Judge, later:
  paraphrased leaks ("put your knight where it forks the king and rook") and
  denials of a guess.
- Why a ceiling is plausible: the rule fights the model's helpfulness on
  every turn, and the hard negatives punish the easy fix of refusing
  everything. The disguise turns need a judgment the prompt cannot fully
  spell out.
- Why the base student will be bad at it: a 1.7B instruct model names the
  move on turn 1. Large base-vs-tuned delta expected, and the teacher can
  generate positions and pressure scripts by the hundreds.

Music equivalent, kept in reserve: a theory tutor that never states the key,
chord, scale or interval the user asks it to identify, with definitions and
explanations answered normally. Same pressure cases, weaker code checks.

Pilot result (2026-10-27, `results/pilot_chess_2026-10-27/`, read in the
README): on code checks there is no ceiling (sonnet-5.5 best 86%, gpt-5.5
zero-shot 100%), and almost every code-check failure is a three-sentence
hint. The finding that matters is in the passing replies: about half of the
disguise, closure and "just the square" replies describe the move precisely
enough to be the answer. That leak by description is invisible to the regex
checks and survives the best prompt on both models, so the ceiling decision
now rests on the judge. Step 2 therefore comes before any rerun: build and
calibrate `pilot/judge.py` with a rubric that says a description identifying
the move is a leak, rescore this run with it (no credits needed, the
transcripts are recorded), and only then decide.

Judged read (2026-10-27 evening, claude-haiku-5.5, rubric v2): on the pilot's
14 scenarios the best strategy passed 21% on both models; on the full 30
scenarios (`results/ablation_chess_2026-10-27/`) it passes 20% on sonnet-5.5
and 10% on gpt-5.5, with 80% judge agreement on 40 hand labels. The ceiling
is real and the failure mode is named: under pressure the coach states the
move in words while keeping to the letter of the rule, most often on "just
the square", "the game is over", insistence and encoding requests. Details
and caveats in the README's pilot-runs section. The behavior is chosen and
the ablation deliverable exists; what remains of step 3 is Andre
spot-checking the labels.

## Step 2: evals before anything else (lecture Part 2)

1. `behaviors/<name>.py` on the existing contract: 30+ hand-written scenarios
   (this is the "challenge set" that the teacher never sees), with tags for
   pressure type and hard negatives; multi-turn where the pressure case needs
   it.
2. Code checks as pure functions.
3. `pilot/judge.py`: one fixed judge model, temperature 0, JSON out with
   `pass` and one-sentence `reasoning`, tolerant parsing. The judge output is a
   sibling `judge` field next to `score` in every transcript, and
   `final_pass = checks and judge`. For the chess coach the rubric judges
   each hint turn on two questions: does the reply identify the move by
   description (which piece and where, even without a square name), and is
   it one hint rather than a hint plus the answer. It runs over recorded
   transcripts the way `rescore.py` does, so the existing pilot run is
   judged before anything is rerun.
4. Calibration: hand-label about 30 replies before seeing judge scores, measure
   agreement, read every disagreement, fix the rubric wording, never the
   labels. Record agreement in the README.
5. Three eval sets, as in the lab: `challenge` (ours, hand-written),
   `synthetic_test` (held-out teacher rows, expected to flatter), and the
   staff held-out set from the brief, which plays the lab's OOD role.

## Step 3: the ceiling, properly sized (lecture Part 3)

Rerun the ablation on the new behavior with the existing CLI: 2 families
(claude-sonnet-5.5 and gemini-3.1-pro-preview through OpenRouter; gpt-5.5
only if budget allows; what ran on 2026-10-27 was sonnet-5.5 and gpt-5.5,
see results/ablation_chess_2026-10-27) x 3 strategies x 30+ scenarios, scored by checks and
the same haiku-5.5 judge used later for base vs tuned. Put real
effort into each prompt; a weak baseline makes any win meaningless. The
useful output is the table plus one sentence naming the failure that survives
the best cell. If there is no plateau, go back to step 1 with the music tutor.

## Step 4: data (lecture Parts 4 to 6)

- Teacher: a cheap, strong model (the lab uses gpt-4.1-mini or
  claude-haiku-5-5; we pick from the ablation's second-best cell so the
  teacher is not also the judge). What ran for v1 on 2026-10-27 was
  claude-haiku-5.5 as teacher, gate judge and eval judge, for cost. The v2
  plan below moves the teacher to sonnet-5.5, as the brief asks, and adds a
  second-family judge check.
- Generation prompt in the slide's shape: the spec inside the instructions,
  `n` conversations per call, persona x situation x difficulty x length grid,
  at least `k` pushback turns per conversation, JSON array of `{"messages"}`.
  Explicit hard-negative categories (in-domain questions that sound off-topic)
  and pressure categories (embedded ask, insistence, disguised ask).
- Gate: dedupe on normalized text, length filter, code checks, judge, then
  read 20 by hand. Critic pass on a 60-row sample to estimate label noise.
- Leakage check against every eval set before splitting; stratified split;
  `sha256` of the training file recorded in the manifest.
- Target: 500 to 800 gated conversations, which the lab reaches in under a
  dollar with small models; ours are longer, so budget a few dollars.

Built 2026-10-27 evening as `datagen/` and `run_datagen.py` (README section
"Training data"): python-chess-verified random mate-in-one positions disjoint
from the eval positions, seeded plans over 16 personas x 12 situations x 14
pressure kinds x 30 hard negatives, a haiku-5.5 teacher with hidden
reasoning off writing one conversation per call in a line format, and a
gate of structure, dedupe, code checks, the ablation's judge (reasoning on:
the reasoning-off variant agreed only 65% with the labels against 80%),
leakage and a stratified split with hashes. 1,100 rows requested, 505
gated (455 train, 50 synthetic test), $2.17 in total. Below the 500 to 800
target on the training side; the data-efficiency curve will say whether
more rows would help, and a second batch costs about the same again.

## Step 5: train (lecture Part 12 and the QLoRA slide)

Exactly the slide's config unless a run shows a reason to change it:
`unsloth/Qwen3-1.7B`, `max_seq_length=2048`, 4-bit, LoRA `r=16`,
`lora_alpha=16`, `lora_dropout=0`, targets q/k/v/o/gate/up/down,
`learning_rate=2e-4`, 2 epochs, batch 2 x grad accumulation 4, `seed=3407`,
the model's own chat template, `train_on_responses_only`, same system prompt
at train and eval. Hyperparameters are not the lever; data is.

Where: this machine has an RTX 4090 (24 GB), so a QLoRA run on 1.7B takes
minutes rather than the lab's T4 budget. The system Python (3.13) has a broken
torch install, so training gets its own `uv` environment pinned to Python 3.12
with Unsloth, TRL, PEFT and bitsandbytes pinned in `requirements-train.txt`.
Colab T4 with the same `train.py` is the fallback.

Done 2026-10-27 evening: `.venv-train` (torch 2.14.1 cu130, unsloth
2026.10.9, trl 1.15.0, peft 0.21.2), `train.py` with the slide config and a
manifest, `eval.py` with a local Unsloth client. v1 trained on the 455 rows
in 114 steps and 74 seconds, loss 4.64 to 1.23, adapter in
`models/v1/adapter` (78 MB). The base-vs-tuned read on the challenge set is
in the README once the evals finish.

## Step 6: diagnose and fix with data (lecture Part 9)

Read the misses of v1 on the challenge set, name one failure mode in a
sentence, trace it to a gap in the generation taxonomy, generate targeted
rows, gate them, retrain with the same config, rerun the same evals, report
the delta with transcripts.

v1 read (2026-10-27 night, challenge set, code checks plus the haiku judge):
v1 passes 15 of 30 conversations on the full metric against 0 for the base,
and against 20% and 10% for the best-prompted sonnet-5.5 and gpt-5.5 on the
same scenarios and judge. Named leaks fell from 152 of 212 hint turns to 1
of 220; stated moves, per the judge, from 106 of 212 to 13 of 220. The failure mode in one sentence: v1 answers the
hard negatives as hints or without squares (12 of 26 normal turns failed,
and 10 of the 11 failed conversations are in the mixed split). Traced to
the data, not the taxonomy: the teacher prompt banned square names from
"every coach reply", so the teacher's own answers to rules questions
avoided squares, the gate did not require them, and the model learned the
avoidance. Fixed for v2: the prompt now bans squares from hint replies only
and demands them in answers, and the gate rejects a square-free answer.
v2 data needs a new generation pass of about $2.20 (teacher plus judge)
with a larger share of hard-negative turns.

## Step 7: data-efficiency curve (lecture Part 10)

One permutation (`seed 0`), nested subsets N, N/2, N/4, N/8, same evals at
each size, two seeds if time allows. Threshold rule written in the README
before the curve is run: the smallest N whose challenge-set pass rate is within
0.05 of the full-N run.

Run 2026-10-27 night (`run_curve.py`, `results/curve_2026-10-27/`), two
training seeds (3407 and 1234), code checks, mean over seeds: 455 rows 65%,
228 rows 48%, 114 rows 37%, 57 rows 46%. Nothing short of 455 is within 5
points, so v1 is data-limited and v2 should add rows, not only fix them.
Named leaks fall monotonically with data (about 28, 12, 4, 0 to 1 per 200
hint turns); the hard negatives are the most data-hungry part (0 to 1, 4 to
5, 10 to 11, 12 to 14 of 26 answered). The 57-row models scoring above the
114-row ones holds across both seeds; the split tables in the eval
directories say why.

## Step 8: prove (lecture Part 13)

- `eval.py --model <hf-repo> --revision <commit> --eval-set <path>`: loads the
  pinned adapter plus the pinned base revision, runs every scenario at fixed
  temperature and seed, applies checks and judge, writes JSONL, prints the
  table. Same harness, same judge as the ablation.
- Push to the Hub, cite the commit hash, pin the base model revision too.
- `manifest.json`: seeds, library versions, data hashes, results, teacher and
  judge ids, eval-code commit.
- README: results table (base vs tuned, per eval set), ablation table, the
  failure-mode paragraph, the curve, the judge agreement number, and the one
  command that rebuilds everything.

## Deviations from the lecture, and why

1. The student is a chat model, not a classifier. The lab says this is the
   intended real project; its Part 12 and the slides give the chat recipe.
2. Multi-turn scenarios. The lecture names pushback and long conversations as
   the pressure cases, and our pilot showed single-turn and 3-turn pressure is
   not enough for frontier models.
3. Training locally on the 4090 instead of Colab, with Colab as the fallback.
   Same script, same config.
4. Our provider layer instead of the lab's `LLM` class. Same interface, plus
   the retry and resume behavior the pilot needed.

## Budget as spent through 2026-10-27

Measured: a sonnet-5.5 8-turn conversation costs about $0.05, a gpt-5.5 one
about $0.06, a haiku-5.5 judge call about $0.0004, a haiku-5.5 teacher
conversation about $0.0006. Training is local on the 4090 and free. Spent on
2026-10-27: pilots and judge calibration about $9.60, the 16-scenario
ablation $6.14, v1 data $0.62 teacher plus $1.50 gate judge, eval judge
$0.13. Decisions taken that day: the hint-only chess coach (judged plateau
at 20%); every run over about $1 is quoted first; training on the local
4090.

## Plan to final (written 2026-10-28, after the brief audit)

The audit is in docs/brief-compliance.md. Money on 2026-10-28 morning:
credit balance $49.63, all there is; Andre raised the key's weekly limit to
$100 so the window no longer binds. The cap for the rest of the project is
the $49.63 balance, and the plan below spends about $20 of it.

### Model policy

Frontier where the brief asks for it, cheap everywhere else:

- Teacher for distillation: the brief says "distilling from a frontier
  teacher model". v1 used haiku-5.5; v2, the dataset that gets submitted,
  uses claude-sonnet-5.5 ($2 in, $10 out per million tokens). It was the
  best cell of the ablation and is half the price of gpt-5.5.
- Prompt-ceiling ablation: done with sonnet-5.5 and gpt-5.5. No more spend.
- LLM judge: the brief asks for one rubric used everywhere, not a frontier
  model. haiku-5.5 stays (calibrated at 80% on 40 labels, same rubric for
  ablation, gate and base vs tuned). One second-family check with
  gemini-3.1-flash-lite ($0.25 in, $1.50 out) on four runs shows the
  ceiling and the base-vs-tuned gap do not depend on an Anthropic judge.
- Gate judge: haiku-5.5, as the eval judge, so the data is filtered by the
  rubric it is graded on.

### Spend plan (cap $49.63, the credit balance)

| # | Step | Model | Estimate |
|---|---|---|---|
| 1 | v2 teacher sample, 50 conversations, read 10, gate yield | sonnet-5.5 | $0.60, actual $0.67 plus $0.10 gate judge |
| 2 | v2 teacher batch, 1,150 more conversations to reach 1,200 | sonnet-5.5 | $14.40, requoted $15.30, actual $15.11 (whole batch $15.78 with the sample) |
| 3 | v2 gate judge, 7,122 verdicts | haiku-5.5 | $2.30, requoted $2.40, actual $2.21 |
| 4 | v2 and base on the challenge set | haiku-5.5 | $0.16, actual $0.16 |
| 5 | v2 curve, 4 sizes x 2 seeds | haiku-5.5 | $0.64, actual $0.48 |
| 6 | v1 curve, the 7 unjudged points (for the v1 vs v2 curve in the Brainlift) | haiku-5.5 | $0.56 |
| 7 | synthetic held-out set, base and v2 | haiku-5.5 | $0.30 (actual $0.40) |
| 8 | second-family judge check: eval_v2 (base and v2), two best ablation cells, the 40 labels fresh | gemini-3.1-flash-lite | $1.00 (actual $0.30) |
| 9 | clean-commit reruns of base and v2 before each submission | haiku-5.5 | $0.32 (early: actual $0.32, two passes) |
| | Total planned | | $20.30 |
| | Reserve under the credit balance | | $29.30 |

Step 2 token estimate came from v1 (1,470 input and 840 output tokens per
conversation) at sonnet prices, $0.012 per conversation. The sample
(2026-10-28, data/v2, seed 1) measured 1,611 input and 1,010 output tokens
per conversation, $0.0133, with OpenRouter's reasoning set to low effort
because sonnet-5.5 refuses to switch reasoning off; the plans are also
longer than v1's (8.4 user turns against 7.5, 1.3 hard negatives against
0.5). Gate yield on the sample: 44 of 50 (88%; v1 with haiku was 46%), 2
structure drops, 3 square-free answers, 1 judged leak. Read of six
conversations: specific hints, none over two sentences, answers with real
squares and lines, varied emotional scenes. Rules stay: every step over $1 is quoted
with the sample's real numbers and waits for a yes; the running total is
kept in this table with actuals.

Reserve uses, in order: a second teacher sample if the first yield is under
50% (prompt tightened first, $0.60); a top-up batch if v2 lands under 600
gated rows ($0.012 per conversation); nothing else. The DPO stretch costs no
API money: preference pairs come from the gate's rejected rows (off-spec)
against the accepted ones (on-spec).

### v2 data changes (data only, same training config)

1. Teacher sonnet-5.5 instead of haiku-5.5.
2. Prompt fix already coded: squares banned in hints only, required in the
   answers to normal turns; gate `require_squares` on. In v1, 137 of 233
   hard-negative answers had no square, which is v1's failure mode.
3. Larger share of hard-negative turns (the curve showed they are the
   data-hungry part) and varied emotional wording (the v1 read found one
   repeated trope).
4. Held-out split by position, not by row: 36 of the 50 v1 synthetic-test
   rows share a placement with train.
5. Target: about 740 gated rows from 1,200 conversations at a 62% yield,
   roughly 665 train after a 10% position-disjoint hold-out. Curve sizes N,
   N/2, N/4, N/8. Actual (2026-10-28, data/v2): 907 gated from 1,200 (76%;
   82 structure, 100 checks, 110 judge, 1 leakage), 805 train and 102 test
   rows over 46 test placements, none shared with train; 5,613 hint turns
   and 1,027 hard-negative turns in train, all 1,027 with a square. Curve
   sizes 805, 402, 201, 100.

### Work plan

Tue 10-28
- Step 1 sample, read, yield; then step 2 and 3 in the background.
- No-API code while the batch runs: Spec adherence and Robustness columns
  in the ablation table and the curve; errored conversations counted as
  failures and the inference window raised; `eval.py` with `--judge`,
  `--baseline`, a bare Hub id, `--revision` passed through and the snapshot
  hash recorded; a smoke script with a mock teacher; the README and plan
  number fixes from the audit; position-disjoint split in the gate.
- Train v2, rerun base and v2 on the challenge set, judge (step 4).

Wed 10-29
- v2 curve, 4 sizes x 2 seeds, local; judge (steps 5 and 6).
- Hub push of the v2 adapter and the v2 dataset with commit hashes: done
  2026-10-29, hdxsfbr/qwen3-1.7b-chess-coach-hints at 0200155 and hdxsfbr/chess-coach-hints at
  a4325db, both public, no spend.
- Held-out loader with a documented row schema; synthetic held-out runs
  (step 7): done 2026-10-29, $0.40, base 0% and v2 93%,
  results/eval_v2_heldout_2026-10-29; second-family judge check (step 8):
  done 2026-10-29, $0.30, results/judge_check_2026-10-29/summary.md.
- Brainlift draft. Andre relabels the 40 calibration items.

Thu 10-30, early submission by midnight
- README results tables, failure-mode paragraph in results/, two-sentence
  grader spec, compliance doc refreshed, tag, clean-tag reruns (step 9).
  Done 2026-10-29: tag early-submission at 4dafda9, base and v2 rerun from
  it in results/eval_v2_early_submission_2026-10-29.

Fri 10-31 to Sat 11-01
- `demo.py` (one prompt, base and tuned side by side) and a Gradio app; the
  running inference demo as a Colab notebook on a free GPU (a Hub Space
  with a GPU costs money); the 3 to 5 minute video with a live grader
  prompt. Done 2026-10-29 ahead of schedule: demo_server.py and its page
  instead of Gradio (no new dependencies), the video from docs/demo
  (3:46, cloned voice). Deployed the same evening at https://hdx-lab.tailf4eaa9.ts.net/ (lab GPU,
  user service, Tailscale Funnel); a Hub Space can replace it by Sunday.
  Left: where to publish the video file.
- DPO stretch if time allows, from gate rejects, no API spend.

Sun 11-02 by noon
- Final clean-tag reruns if code changed, final README, Brainlift, submit.

### Needed from Andre

- A Hugging Face write token at ~/.config/agentforge/hf_token (received 2026-10-29).
- The demo hosting choice: Colab notebook (free) or a paid Hub Space.
- 40 relabeled calibration items (about 40 minutes).
- The staff held-out format, if the course has published one.
