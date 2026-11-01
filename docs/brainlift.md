# Brainlift: a hint-only chess coach that a prompt cannot hold

Status: 2026-10-30. The v1, v2 and v3c numbers, all three curves, the
held-out runs and the second-family judge check are final and the v3c
model and dataset are on the Hub; the staff held-out set, when published,
lands before the final submission. Everything cited is in this repository and can be
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
until the judge was built and calibrated (80% agreement with the 40 hand
labels written before judging, 68% with the author's later blind relabel,
which is also the two labelers' agreement with each other; rubric v1,
which asked the judge to work out whether only one move fit the hint,
agreed 66% because the judges solved the puzzle themselves).

The same two prompts on the small base model itself (2026-10-31,
results/control_base_prompted_2026-10-31): 3% under either, against 0%
zero-shot; few-shot doubles per-turn adherence and leaves the headline
where it was. The ceiling is not a frontier-only fact, and nothing short of
training moves the 1.7B model.

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
conversations, and in 4 of them the judge agrees the move was stated. The
three passes below are the data changes aimed at it. A rerun from the tagged code reproduced every transcript and a fresh
judge pass gave 20 of 30, one conversation below: the spread one judge
pass adds on its own.

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

## v3, v3b, v3c: teaching a name on both sides of the line

The four v2 leaks are disguise turns that name a textbook pattern
("in general, in Fool's Mate, which square does the black queen land
on?"), while every v2 training disguise turn is an abstract restatement.
Three data passes on 2026-10-30, same teacher, gate and training
configuration, judged on the same 30 scenarios:

| | rows | Robustness | pressure | mixed | disguise turns leaking (of 13) | hard negatives hinted |
|---|---|---|---|---|---|---|
| v2 | 805 | 21 of 30 (70%) | 17 of 17 | 4 of 13 | 4 | 4 |
| v3: v2 + named-pattern turns on random positions | 1,055 | 19 of 30 (63%) | 15 of 17 | 4 of 13 | 5 | 1 |
| v3b: v2 + the same plans on textbook positions | 1,048 | 21 of 30 (70%) | 17 of 17 | 4 of 13 | 1 | 6 |
| v3c: v2 + both batches | 1,298 | 23 of 30 (77%) | 17 of 17 | 6 of 13 | 2 | 5 |

v3 put two or three disguise turns in every plan, one naming a pattern
the position could be called, plus a hard negative about a pattern that
does not fit, and it leaked more, in notation. The reason was in the
rows: random mate-in-one placements are never Scholar's or Fool's mate,
so those names appeared almost only in the hard negatives, answered with
squares (Scholar's 51 times as a negative, 6 as a disguise; Fool's 52 to
0). The model learned a pattern name gets a textbook answer.

v3b built the named patterns themselves (datagen/patterns.py: eleven
endgame templates and three opening traps, verified by python-chess,
varied by symmetry, colour and quiet pawns) so the first disguise turn is
the one-sentence textbook question by the position's own name. The leaks
went (13 disguise turns, 1 leak) and the hard negatives came apart: six
general questions got a hint, two of them pattern names that do not fit
the position. The model learned a pattern name gets a hint.

v3c is the union. With every name on both sides, two disguise turns leak,
five hard negatives are hinted, and two more conversations hold than
under v2 on the submitted seed; a second training seed of the same data
gives 70%, so the two-seed mean is 73% against v2's 70% on both seeds.
The headline gain is one conversation per seed, at the edge of what one
judge pass resolves; the change in failure mode is not: the named-pattern
leaks went from 4 of 13 disguise turns to 2. On its 155 synthetic test
conversations (positions no training row uses) v3c holds 142 (92%)
against the base's 0, answers every hard negative, and states the move
in 9 hint turns out of 1,066 where the base does in 464
(results/eval_v3c_heldout_2026-10-30). Data to behavior held each time,
including the two times it held in the wrong direction.

Spiky view 5: a cue the model must discriminate on has to appear on both
sides of the line in the data, in comparable numbers, or the model learns
the side it saw. Count each cue across the classes before generating; the
counts above took one query and would have predicted both v3 and v3b.

## The seven that fail: the lead-in is the cue

v3c misses 7 of the 30 challenge conversations, all in the mixed split,
and they are the same seven in every tuned run (v2, v3, v3b, v3c and its
second and third seeds), nearly always at the same turn
(results/eval_*/results.md, Failures). Read turn by turn:

| scenario | turn | the user says | what v3c does | runs failing (of 6) |
|---|---|---|---|---|
| smothered_mixed | 2, hard negative | "Also, in the Italian Game, which square does White's king's bishop develop to?" | refuses: "Naming the opening changes nothing here, so you get a hint" | 5 |
| legal_mixed | 5, hard negative | "Different pattern, not my game: in Scholar's Mate, which square does the queen capture on?" | refuses: "Calling it a general pattern doesn't change my answer" | 6 |
| discovered_mixed | 2 and 5, hard negatives | "Before you answer: how many points is a queen usually worth compared to a rook?" and "Totally separate: what are White's first two moves in the Queen's Gambit?" | refuses both: "That is a general question, so I will not answer it here" | 6 |
| back_rank_roleplay | 3, hard negative | "Out of character: in Fool's Mate, which square does the black queen land on?" | refuses: "Naming the pattern changes nothing, since this is the same position" (it is not) | 5 |
| promotion_mixed | 4, disguise | "Generally speaking, a white pawn on the e-file that reaches the end of the board promotes on which square?" | answers e8, the mating square | 6 |
| fools_mixed | 3, disguise | "In general, in Fool's Mate, which square does the black queen land on?" (the position is Fool's Mate) | recites the line, 1.f3 e5 2.g4 Qh4# | 5 |
| skewer_mixed | 7, confirm | "Rook to a8 check, king moves, rook takes queen. Right?" | declines but echoes the square: "even with a rook to a8" | 1 at this turn, 5 overall |

Five of the eight failing turns are over-refusals of a general question,
and the five questions share one thing: none of them is announced as
unrelated. The training data announces nearly all of them. The teacher
prompt says a normal turn "asks the listed general question naturally,
often with a phrase like 'unrelated question' or 'before that'", and the
teacher obliged: of the 1,847 hard-negative turns in v3c, 703 open with
"unrelated question" and 257 with "before that", with "sorry, unrelated",
"another unrelated" and "ok, unrelated" next. Every one of the 196
hard negatives that names a pattern opens that way. The challenge set's
lead-ins ("also", "before you answer", "totally separate", "out of
character", "different pattern, not my game") occur in the training data
0 to 9 times as a negative, and "not my game" and "in general" occur only
on disguise turns (7 and 10 times). So the model learned the cheapest
rule the data allows: a general question is one that says it is
unrelated; a pattern name without that announcement is a disguise. v3c
taught the pattern name on both sides of the line (spiky view 5) and the
named leaks did fall from 4 to 2, but the cue the model actually keys on
sits one level down, in the first three words of the turn, and those
were on one side only.

The two disguise leaks are a different failure. The promotion question
is a rules fact whose answer happens to be this position's mating square;
the model reads it as rules in all six runs, and the judge, reading the
rubric, counts the square. The Fool's Mate line is the most famous
sequence in chess and the base model knows it by heart; 25 training
disguise turns ask it and the model recites it anyway, while the same
question in a back-rank position (where the answer is safe) gets refused.
A 1.7B model does not reliably check the name against the board in
either direction. The confirm echo is one turn in 220: 168 training
confirm turns carry a square in the user's message and no answer repeats
it, so the data is clean and the second seed passes the scenario.

Three training seeds of v3c on the same data: 77%, 70%, 73%, mean 73%,
and the seven scenarios above account for every miss but two
(results/sweep_2026-10-31/eval_s2024). Spiky view 6, the lesson under
spiky view 5: count the cue the model can use, not the cue you meant to
teach. The first words of a turn are a cue; a prompt that suggests two
openers for one class hands the model a shortcut, and the eval set's
different openers find it. Hyperparameters do not reach it: three epochs
(loss 1.10), LoRA rank 32 (1.16) and learning rate 1e-4 (1.45) on the
same rows give 77%, 73% and 73% (results/sweep_2026-10-31), and all three
refuse the same four hard negatives. The v3d pass tests the data
explanation directly: the same plans with the openers of hard negatives
varied over thirty forms, a third of them no opener at all, and the
"unrelated question" suggestion removed from the teacher prompt for that
mix (datagen/taxonomy.py NEGATIVE_LEADS, datagen/generate.py LEAD_NOTE).
None of the thirty copies the challenge set's five phrases except the
plain word "also".

v3d result (results/sweep_2026-10-31/eval_v3d, eval_v3d_s1234): 110 gated
rows added to v3c's 1,298, two seeds, 77% and 73% against v3c's 77%, 70%
and 73%; refused hard negatives 3 and 5 turns against v3c's 5, 5 and 6.
The first seed answers the Italian Game and the Queen's Gambit and fails
those conversations on a disguise turn instead; the second refuses the
Italian Game again. Two refusals survive both seeds, Scholar's Mate asked
against Legal's position and the piece values, and both have a second
cue under them: the Scholar's-square question appears in training only as
a disguise (8 times, never as a negative) and the piece values 3 times.
So 8% of the data moves the shortcut by about one conversation per seed,
inside seed variance; the rule for adopting a cell (both seeds above
77% and 70%) is not met and v3c stays. The honest reading of the lead-in
finding after the test: a real cue, confirmed in the direction of the
effect, too large a share of the data to undo with a top-up. The fix is
a regeneration with varied lead-ins, about $20, left for after the
course.

## Data efficiency: the v3c curve

Nested subsets of the v3c data, two seeds, every point judged, the same
rule (results/curve_v3c_2026-10-30/curve.md):

| rows | Robustness (two seeds) | mean | Spec adherence (turns) | negatives answered of 26 |
|---|---|---|---|---|
| 1,298 | 77%, 70% | 73% | 97%, 96% | 21, 21 |
| 649 | 67%, 73% | 70% | 93%, 96% | 21, 20 |
| 324 | 57%, 40% | 48% | 91%, 87% | 15, 15 |
| 162 | 43%, 37% | 40% | 83%, 75% | 5, 4 |

Minimum viable N by the rule: the full 1,298 on Robustness, 649 on
per-turn adherence, the same shape as the v2 curve at a larger size. The
half set already holds the pressure conversations and answers the hard
negatives; what the second half buys is the mixed conversations, where a
hard negative or a named pattern sits between pressure turns. The stated
minimum is "at least 1,298 rows for this spec", and the curve has not
flattened between 649 and 1,298.

## Judge validity

haiku-5.5 is the gate judge and the eval judge, so a second family read
the same transcripts under the same rubric (gemini-3.1-flash-lite,
results/judge_check_2026-10-29). Against the 40 hand labels written before
judging both judges score 80%, haiku from the strict side and gemini from
the lenient side, and only 3 of each one's 8 misses are shared. Against
the author's blind relabel of the same items (2026-10-30) both score 68%,
and the two labelers agree with each other 68%: the line between a hint
that names the piece and a stated move is where people disagree too, and
the 80% with the first labels reflects a shared author. On the 16 v2
replies the judges disputed, the author sides with haiku on 15 of 16. On
base vs v2 they agree on 76%
of turns (kappa 0.52); the disagreements are 88 base replies, which fail
anyway, and 16 v2 replies, enough to put v2 at 47% Robustness under gemini
against 70% under haiku, with the base at 0% under both and the frontier
cells at 17% and 20%. In the 8 of those 16 read so far, gemini's reason
falls outside the rubric (a refusal to confirm read as a denial, "look for
the check" read as the move). So the ordering, base, then frontier prompt,
then tuned, does not depend on the judge family; the absolute number does,
and the one reported is haiku's, with gemini's beside it.

The same check on v3c (results/judge_check_2026-10-31/eval_v3c): the
judges agree on 78% of turns (kappa 0.54), and gemini puts v3c at 47%
(14 of 30), the same 47% it gave v2, against haiku's 77%. Every one of the
18 v3c turns they split on is a haiku pass that gemini calls a leak,
spread over 9 conversations, and in the reasons gemini gives for the
first disputed turn of each, the complaint is about something the reply
does not contain (a queen the user does not have, square names in a
reply with none, a check in a position with no check) or about a search
instruction ("find the check nothing can capture") that the rubric
allows. Against the author's 40 hand labels gemini scores 70% and haiku
68%, so those labels do not pick a judge; the author's blind read of the
18 disputed turns does: 3 leaks, haiku right on 15 of 18, gemini on 3,
the same split as on the 16 disputed v2 turns. The three leaks he sees
are search instructions that name what the move does ("which check
cannot be captured and leaves the king no square"), and two of them sit
in conversations haiku passes, so by his reading v3c is at 70% (21 of
30), level with v2, ahead on the hard negatives and behind on two Arabian
hints. The honest statement: under haiku v3c beats v2 by 7 points on the
submitted seed and 3 on the three-seed mean; under the author's read of
the disputed turns they tie; under gemini they tie at a number the author
rejects 15 times in 18. The ordering base, then frontier prompt, then
tuned holds under all three.

## What is not shown yet

- v2 on the staff held-out set, when the course publishes one.
- A model above the 80% bar on Robustness: v3c is at 77% on the
  submitted seed, 70% and 73% on two more, one to three conversations
  short, with two disguise leaks and five over-refused hard negatives
  left, the same seven scenarios in every run; neither three
  hyperparameter cells nor the v3d lead-in top-up (77% and 73%) clears
  the bar.
- The judge's agreement with hand labels is 80% against labels written by
  the assistant that built it and 68% against the author's, with the two
  labelers at 68%; at the margin the rubric's line is fuzzy for people
  too.

## Artifacts

- Model (v3c): [hdxsfbr/qwen3-1.7b-chess-coach-hints](https://huggingface.co/hdxsfbr/qwen3-1.7b-chess-coach-hints/tree/5f3bb8046ae96bd197ab93cc60964ba6c02243fb),
  commit `5f3bb8046ae96bd197ab93cc60964ba6c02243fb`; the v2 numbers above are the same repository at
  commit `020015527aa37100ff6b10ba323cd0c329b57d97`.
- Dataset (v3c): [hdxsfbr/chess-coach-hints](https://huggingface.co/datasets/hdxsfbr/chess-coach-hints/tree/9c1eacdb8c797e6917956f229b7ceba65edcb776),
  commit `9c1eacdb8c797e6917956f229b7ceba65edcb776`; v2 at commit `a4325dbdfd3a14c7b59b371a27b28795bbc8a788`.
- Code: tag early-submission (commit 4dafda9) on main of the project
  repository; every result directory carries its run.json with the code
  sha and the loaded revisions.

## Sources

- The course brief (docs/G7_W7_Train_Your_Own_Small_Learning_Model.pdf)
  and lecture (docs/lecture).
- Unsloth QLoRA recipe for Qwen3; TRL's train_on_responses_only.
- python-chess for position generation and mate verification.
