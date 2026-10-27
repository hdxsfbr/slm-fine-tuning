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
only if budget allows) x 3 strategies x 30+ scenarios, scored by checks and
the same haiku-5.5 judge used later for base vs tuned. Put real
effort into each prompt; a weak baseline makes any win meaningless. The
useful output is the table plus one sentence naming the failure that survives
the best cell. If there is no plateau, go back to step 1 with the music tutor.

## Step 4: data (lecture Parts 4 to 6)

- Teacher: a cheap, strong model (the lab uses gpt-4.1-mini or
  claude-haiku-5-5; we pick from the ablation's second-best cell so the
  teacher is not also the judge).
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

## Budget for the rest of the project (written 2026-10-27 evening)

Measured so far: a sonnet-5.5 8-turn conversation costs about $0.05, a
gpt-5.5 one about $0.06, a haiku-5.5 judge call about $0.0004. Training is
local on the 4090 and free. What is left, in the order it will be spent:

| Step | What runs | Estimate |
|---|---|---|
| Ablation, 16 more scenarios | 96 frontier conversations + haiku judge | $5.50, actual $6.14 |
| Training data, 700 rows | haiku teacher, about 150 calls | under $1, actual $0.67 for 1,100 one-row calls |
| Gate on the generated rows | haiku judge, about 5,000 hint turns | $1.70, actual $1.50 |
| Base vs tuned, v1 and v2 | haiku judge on challenge + synthetic sets, 4 evals | $1.30 |
| Data-efficiency curve | haiku judge on the challenge set only, 4 sizes x 2 seeds | $0.60 |
| Staff held-out set | haiku judge, 2 evals | $0.30 |
| Total | | about $10.50 |

Against, after the ablation: $11.90 of credit, and a $20 weekly key limit
with $3.18 left this week (measured 2026-10-27 evening), which covers the
data generation and its gate; the evals wait for the weekly reset or a limit
bump. Rules: every run over $1 is quoted first; the running total is kept in
this table; if the week's key limit runs out before the evals, the
challenge-set evals (about $0.10 each) go first and the synthetic-set evals
wait for the reset. Fallback if money stops after the ablation and v1: the
submission still has the full ablation table, v1 base vs tuned on the
challenge set, and a code-check-only curve with a judged sample.

## Timeline (brief: early submission Thu 2026-10-30 midnight, final Sun 2026-11-02 noon)

- Mon 10-27: choose the behavior; spec; 30+ scenarios; checks; judge and its
  calibration labels.
- Tue 10-28: ceiling ablation (needs OpenRouter credits, about $15 to $25 with
  frontier models and 30+ multi-turn scenarios); if a plateau shows, generate,
  gate, split; `train.py`; v1; base vs tuned.
- Wed 10-29: diagnose, v2, delta; curve; `eval.py`; Hub push; README.
- Thu 10-30: early submission.
- Fri to Sun: staff held-out set, second seed on the curve, polish, final.

## Decisions needed now

1. Behavior: the hint-only chess coach (judged pilot shows a plateau at 21%).
2. Spend: about $9.60 went on the two pilots and the judge on 2026-10-27,
   which Andre flagged as too much. From here every run over about $1 gets a
   cost quote first, the judge and the teacher are claude-haiku-5.5, and the
   ablation uses sonnet-5.5 plus gemini-3.1-pro-preview rather than gpt-5.5
   (three times the output price). Rough remaining total: $8 to $10, with
   about $18.40 of credit and a $20 weekly key limit ($9.60 left this week).
3. Training on the local 4090 (recommended) or Colab.
