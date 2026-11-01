# Brief compliance audit

Audit of the repository against the brief in
docs/G7_W7_Train_Your_Own_Small_Learning_Model.pdf. First pass on commit c1c3887
(main, 2026-10-28 morning): two independent reads, one by a fresh agent told to assume gaps
and prove every item from code, data and result files (README and docs excluded as
evidence), one by the session that built the repo; every disagreement settled by reading the
code or data again. Rewritten 2026-10-28 evening after the day's fixes, from the same item
list; updated 2026-10-29 after the Hub push, the synthetic held-out run, the second-family
judge check, the tagged rerun and the demo video; updated 2026-10-30 after the grader
notebook, the judge retry and the v3, v3b and v3c data passes. Test suite at the last update: 214 passed.

Deadlines: early submission Thursday 2026-10-30 at midnight, final Sunday 2026-11-02 at noon.

## Status summary

Met and backed by data: a falsifiable spec with a two-sentence grader version, a
180-conversation prompt-ceiling ablation on two families scored by the same judge used for base
vs tuned, with Spec adherence and Robustness in the table and a failure-mode paragraph in the
results directory; a v1 dataset and model, the diagnosed failure mode (hard negatives answered
without squares) traced to the teacher prompt and resolved by a data change; the v2 dataset
from a frontier teacher (sonnet-5.5), gated and held out by position; v2 at 70% Robustness
against 0% for the base and 20% for the best frontier prompt; a judged data-efficiency curve
on v2 with two seeds and a pre-registered rule; a one-command base-vs-tuned eval with the
judge; a smoke run of the whole loop; raw judge transcripts per turn; a Brainlift draft.

Open for the early submission: nothing; the public Hub checkpoint and the dataset went up on
2026-10-29 and the code is committed on main (4dafda9, tagged early-submission).
Open for the final (as of 2026-10-30 night): the staff held-out set when it is published
(the synthetic held-out runs are done), the video upload, and a model above the 80% bar
(v3c is at 77% and 70% on two seeds). The relabel is done; the demo stays on the lab
machine by decision.

## Open items, worst first

Severity: blocker (the submission fails without it), should-fix, minor. E = early submission,
F = final.

| # | Item | Brief wording | State | Sev. | Due | Effort |
|---|---|---|---|---|---|---|
| 15 | Inference demo and video | "running inference demo", "3 to 5 minute demo video ... one live, grader-supplied prompt" | demo_server.py serves base and tuned side by side on any prompt (tested, 7 tests) and demo.py does the same on the CLI. The video is done (docs/demo/out/chess-coach-demo.mp4, 3:46, recorded 2026-10-29 from the page with the adapter by Hub id, narrated in Andre's cloned voice; scene 6 is the live prompt). The page is deployed at https://hdx-lab.tailf4eaa9.ts.net/ (the lab GPU, a systemd user service published with Tailscale Funnel; up as long as the lab machine is). Left: a Hub Space so the demo does not depend on the lab machine, and publishing the video file, which is gitignored. | minor | F | Space 2 to 3 h |
| 12 | Staff held-out eval set | "run against a scenario set your model never saw" | The loader accepts rows as messages or plain turns, derives positions from a FEN, and documents the schema (README, "Held-out set format"). Synthetic held-out run done 2026-10-29 (results/eval_v2_heldout_2026-10-29): base 0 of 102, v2 95 of 102 (93%) on positions train never saw, every hint turn judged. The staff set itself has not been published; the one command runs it as soon as it exists. | minor (waiting on the course) | F | 20 min once the set exists |
| 13 | Minimum viable N on a model that holds the behavior | "the smallest N that holds the behavior reliably" | v3c (2026-10-30, 1,298 rows: v2 plus a named-pattern batch on random positions and one on textbook positions) holds 77%, 23 of 30, on the submitted seed and 70% on a second seed, against v2's 70% on both; two disguise leaks and five over-refused hard negatives remain. The v3c curve (1,298, 649, 324, 162; two seeds; judged; results/curve_v3c_2026-10-30) gives 1,298 by the rule on Robustness and 649 on per-turn adherence; stated as "at least 1,298 for this spec", below the 80% bar. The three passes are written up in the README ("v3", "v3b", "v3c") and the Brainlift. | should-fix (disclosed) | F | none planned; the next data change is more two-sided named-pattern rows |
| 10 | Judge validity | "the same LLM-as-judge rubric" | Second family checked 2026-10-29 (results/judge_check_2026-10-29/summary.md): gemini-3.1-flash-lite agrees with the 40 labels at 80%, as haiku does; on base vs v2 the judges agree on 76% of turns (kappa 0.52) and gemini puts v2 at 47% Robustness against haiku's 70%, the base at 0% under both; the ceiling holds under both judges. Andre relabeled the 40 items blind on 2026-10-30 (labels_andre.jsonl, via label_server.py): haiku and gemini each agree 68% (27 of 40) with his labels, and the two labelers agree 68% with each other; on the 16 disputed v2 replies he sides with haiku on 15 (disagreements_labeled_andre.jsonl). Disclosed in the README and the Brainlift. | resolved (disclosed) | F | none |
| 11 | Pinned eval-code commit | "exact eval-code commit hash" | The code is tagged early-submission (4dafda9) on main and pushed; model and data commits are pinned in the manifests and every run.json. The sha in run.json and the manifests carries a dirty suffix because the runner flags any untracked file or doc edit, not only code changes; base and v2 rerun from the tag with the adapter loaded by Hub id reproduced the headline transcripts exactly (results/eval_v2_early_submission_2026-10-29). Accepted as is. | minor | F | none; the check could ignore untracked and non-code paths before the final tag, 10 min |
| 3 | Brainlift | "behavior thesis, and whether data to behavior held, with evidence" | docs/brainlift.md drafted with thesis, spec, ceiling, v1, v2, both curves, minimum N and four spiky views. Final pass after the held-out runs. | should-fix | E draft done, F | 1 h |
| 1b | v2 failure mode (disguise) | the spirit of "iterating on data, not hyperparameters" | Diagnosed: all v2 leaks are on disguise turns that name a textbook pattern. Resolved by data in three passes: v3 (names as hard negatives on random positions) leaked more, v3b (names as disguises on textbook positions, datagen/patterns.py) over-refused, v3c (both) holds 2 more conversations than v2 with 2 disguise leaks left of 13. Same training configuration throughout. | resolved | F | none |

## Final audit, 2026-10-30 evening

Two independent reads of the brief against the code, data and result files (the README
and docs excluded as evidence), after v3c and the re-recorded video. No blockers. The
items found, and Andre's decision on each:

- Fixed the same evening (Andre first accepted these, then asked for all of them):
  - the self-contained judge export (judged_turns.jsonl) was missing for the v3, v3b and
    v3c result directories; exported for all of them;
  - the literal `eval.py --model <id> --eval-set <path>` needed `--out`, `--baseline` and
    `--judge`; for a Hub id or path those now default to `results/eval_<model>_<date>`,
    `unsloth/Qwen3-1.7B` and the haiku judge, with the judge key checked before any model
    loads (`--no-baseline`, `--no-judge` switch them off; provider specs get no defaults);
  - the v3c runs had loaded the adapter from models/v3c, not by Hub id: rerun from
    `hdxsfbr/qwen3-1.7b-chess-coach-hints@5f3bb80` with the base in the same command
    (results/eval_v3c_hub_2026-10-30); the 30 tuned transcripts are identical to the local
    run's and the headline is the same 23 of 30;
  - the held-out loader raised on a row without a FEN or position; it now also reads
    single-turn rows (`prompt`, `user`, `question`, `input`, `text`) and ShareGPT
    `conversation` rows, and leaves an unscorable row out with a warning, listing it in
    run.json under `eval.skipped_rows` (tests/test_eval_sets.py);
  - the smoke log predated the v3 data-generation code: rerun, results/smoke_2026-10-30.log;
  - a labeling page for the 40 calibration items and the 16 disputed v2 turns
    (label_server.py), so the relabel is Andre's own read (item 10).
- Accepted from the audit (Andre, 2026-10-30): the video's live prompt was written for
  the recording and typed live, not supplied by a grader. The eval-code commit is pinned
  by a tag on the final commit.
- Optional, not done: the second-judge check on v3c ($0.30), a curve on the synthetic
  test rows (about $5), a model above the 80% bar (v3c is at 77% and 70% on two seeds).
- Outside the repo: the video upload, the staff held-out set (not
  posted as of 2026-10-30), confirmation that graders can clone an internal GitLab
  project.

## Fixed items

On 2026-10-30:

- Grader path: notebooks/grader_eval.ipynb runs the one-command eval from nothing on a free
  Colab GPU (install, clone, eval.py with the judge, results, a live prompt through both
  models); executed end to end in a fresh Python 3.12 venv on the 4090 (install 98 s, eval
  8 min, base 0 of 30, tuned 20 of 30); README "For graders". Prompted by staff saying on
  Slack that graders run eval.py on their own machine.
- Judge robustness: an empty judge reply (the budget spent on hidden reasoning, which is
  deterministic at temperature 0) is retried with four times the budget, then with
  reasoning off; the verdict row records which try answered (pilot/judge.py, tested).
- 13 and 1b: three data passes (v3, v3b, v3c); v3c adopted at 77% and pushed to the Hub (model
  commit 5f3bb8046ae96bd197ab93cc60964ba6c02243fb, dataset commit 9c1eacdb8c797e6917956f229b7ceba65edcb776); the public demo
  serves it; the grader notebook defaults to it.
- datagen/patterns.py: verified textbook-pattern positions (14 families), tested.
- Dataset card renders merged manifests (run_datagen.py merge), tested.

On 2026-10-29:

- 11 Tag early-submission at 4dafda9, pushed; base and v2 rerun from it with the adapter
  loaded by Hub id (results/eval_v2_early_submission_2026-10-29, $0.16): transcripts identical
  to the headline run, v2 20 of 30 under the fresh judge pass (one yes/no verdict moved), base
  0 of 30.

- 2 Public Hub checkpoint: hdxsfbr/qwen3-1.7b-chess-coach-hints at commit 020015527aa37100ff6b10ba323cd0c329b57d97,
  public, model card with the base revision, data sha256, config, library versions and
  code sha. eval.py loaded it by Hub id at that commit on the GPU
  (results/hub_load_test_2026-10-29, two scenarios, mock judge); run.json records the
  adapter and base revisions it resolved. Commits recorded in models/v2/manifest.json.
- 14 Dataset published: hdxsfbr/chess-coach-hints at commit a4325dbdfd3a14c7b59b371a27b28795bbc8a788, public, with
  train.jsonl, synthetic_test.jsonl, manifest.json, gate_report.md and a dataset card
  (sha256 of both files, row shape, gate table). Recorded in data/v2/manifest.json.
- Eval harness committed: main at 4dafda9, tag early-submission, pushed to origin.
- 10 (check half) Second-family judge check: judge_check.py (tested) judged copies of the
  base-vs-v2 eval and the two best ablation cells with gemini-3.1-flash-lite, and the 40
  labeled items fresh (run_judge.py calibrate --fresh --tag). Numbers in
  results/judge_check_2026-10-29/summary.md and in the README's judge section. $0.30.
- 12 (run half) Synthetic held-out run: base and v2 on the 102 test conversations, adapter
  loaded by Hub id, 1,406 hint turns judged (seven judge calls errored on the first pass and
  were rerun). Base 0%, v2 93% Robustness, 99% Spec adherence; results.md, judge.jsonl and
  judged_turns.jsonl in results/eval_v2_heldout_2026-10-29. About $0.40.

On 2026-10-28, from the morning audit's list, numbered as there:

- 1 v2 dataset and model: data/v2 (1,200 sonnet-5.5 conversations, 907 gated, 805 train and
  102 test held out by position, every hard-negative answer with a square), models/v2,
  results/eval_v2_2026-10-28: Robustness 70% against v1's 50% and the base's 0%; hard
  negatives answered 22 of 26 against 14. The failure mode the brief asks to resolve by a
  data change is resolved by one.
- 4 Spec adherence and Robustness: named, defined (README, "Reading the results") and in
  every table (behaviors/chess_coach.py COLUMNS, run_curve.py); finished runs re-rendered.
- 5 One-command eval: eval.py takes a bare Hub id or path with an optional @commit,
  --baseline and --judge, runs both models, judges, writes the base-vs-tuned table and
  records the loaded revisions in run.json (tests/test_eval_cli.py; verified on the GPU in
  smoke.sh and results/eval_v2_2026-10-28).
- 6 Smoke run: smoke.sh runs positions, generate (mock teacher), gate (mock judge), train
  (one QLoRA epoch) and the judged base-vs-tuned eval from nothing; passed on the 4090, log
  in results/smoke_2026-10-28.log.
- 7 Errored conversations: counted as failures in Robustness and Spec adherence; inference
  window raised to 8192 (base rerun: 0 errors); curve tables re-rendered.
- 8 Judged curve: every v2 curve point judged ($0.48). The v1 curve stays code-checks only and
  is superseded.
- 9 README and plan numbers: training-turn counts, the curve's seed-1234 row, the read-of-20
  claim, the gate-log note, the plan's gemini and teacher-is-not-judge lines.
- 12 (loader half) Held-out ingestion: tolerant loader and documented schema; judge_items
  falls back to the scenario position for other opening layouts.
- 15 (demo half) demo.py, base and tuned side by side on any prompt, tested.
- 15 (video half, 2026-10-29) demo_server.py and demo/index.html (tested), and the video:
  docs/demo-script.md, docs/demo/ pipeline, out/chess-coach-demo.mp4 (3:46). Every reply on
  screen is a live call; the only cuts are page loads and model waits (clips/cuts.json).
- 16 Two-sentence grader spec in the README.
- 17 Failure-mode paragraph in results/ablation_chess_2026-10-27/failure_mode.md.
- 18 Eval report template: results.md of an eval run opens with "Base vs tuned".
- 19 Clean judge export: run_judge.py export writes judged_turns.jsonl, one self-contained
  line per judged turn, for the ablation, eval_base, eval_v1 and eval_v2.

## Verified

- Spec is falsifiable with deterministic checks and a judge rubric; two-sentence version in
  the README.
- One target, one context: the chess coach only; 30 scripted scenarios over 17 positions.
- No hyperparameter chasing: v1, v2 and all 16 curve adapters share one configuration except
  seed and n.
- Eval existed before training, by result timestamps (ablation 19:09Z, data 21:03Z, first
  training 22:22Z on 2026-10-27); git cannot show the order because the pilot landed in one
  commit.
- Challenge-set placements overlap train placements: 0 (v1 and v2). v2 test rows share no
  placement with v2 train.
- Ablation 1: two families, three strategies, 6 cells x 30 scenarios, 0 errors, 1,320 judged
  turns, same judge and rubric as every eval; re-aggregating the transcripts reproduces the
  table; best Robustness 20% and 10% against the 80% bar; failure-mode paragraph in the
  results directory.
- Ablation 2: v2 curve with 4 sizes x 2 seeds on nested subsets, every point judged, rule
  pre-registered; training logs and loss logs in results/curve_v2_2026-10-28 and the
  manifests; one point reruns with run_curve.py --sizes N.
- Raw judge transcripts: judge.jsonl and judged_turns.jsonl per run.
- Pins: base revision a972f4304f86a0a705d35b378d7a7675d58063a7 in every manifest and in every
  eval's run.json (eval.loaded); data sha256 per manifest; library versions in the manifests
  and requirements-train.txt.
- Early checklist: spec, ablation report, eval harness, smoke run, first dataset and first
  QLoRA run, base-vs-tuned numbers (v1 and v2), failure mode resolved via v2 data, eight curve
  points (sixteen with v1), draft artifacts (dataset shape, local checkpoints, Brainlift).
- Hub: both repos public without a token (huggingface_hub repo_info, 2026-10-29); the model
  repo holds adapter_config.json, adapter_model.safetensors, the tokenizer files and the
  card; the dataset repo holds the two JSONL files, the manifest, the gate report and the
  card; neither card has an em dash.
- Held-out positions: the synthetic test rows share no placement with train (gate report);
  v2 at 93% on them against 70% on the hand-written challenge set.
- Judge: a second family reproduces the ordering from the committed transcripts (base 0%,
  best frontier prompt 17 to 20%, v2 47% under gemini and 70% under haiku) and the 80%
  agreement with the 40 labels.
- Stack: post-trained Qwen3-1.7B through Unsloth QLoRA on an RTX 4090; teacher sonnet-5.5 for
  v2 (haiku-5.5 for v1).

## Could not verify

- That the spec was written before any code: only result timestamps order the work; Andre
  attests.
- Clean-machine reproducibility (CUDA 13, Python 3.12).
- Training reproducibility: the two seeds of each curve point agree within a few
  conversations, which is the only evidence so far.
- The staff held-out format.

## Disclosed deviations

- The second frontier family is gpt-5.5, not gemini as the plan first said (budget).
- Teacher, gate judge and eval judge share one model for v1 (haiku-5.5); v2's teacher is
  sonnet-5.5 and the judges stay haiku-5.5. The second-family check (item 10) shows the
  ordering holds under gemini and that the absolute v2 number is judge-dependent (70%
  under haiku, 47% under gemini); the README reports haiku's with gemini's beside it.
- Adapters are gitignored; manifests with hashes are committed; the public checkpoint is
  on the Hub (hdxsfbr/qwen3-1.7b-chess-coach-hints at 5f3bb80 for v3c, 0200155 for v2).
- The curve holds epochs fixed, so steps scale with N, as in the lecture recipe.
- Every run's code sha carries a dirty suffix: the runner flags any untracked file or doc
  edit, not only code changes. The code is tag early-submission (4dafda9); item 11.
- The 40 calibration labels were written by the assistant; item 10.
- v1's curve is code-checks only; v2's is judged and supersedes it.

## Requirement table

| Requirement | Status | Evidence or open item |
|---|---|---|
| Behavior Spec, one or two sentences, falsifiable | Met | README, section C; SPEC in behaviors/chess_coach.py |
| A well-prompted base model cannot already do it | Met | ablation best cells 20% and 10% |
| One target, one context | Met | chess coach only |
| No training before the eval exists | Met by timestamps | git cannot show order |
| No hyperparameter tuning to fix data | Met | identical configs |
| Ablation 1: 2 families, 3 strategies, 30 scenarios per cell | Met | results/ablation_chess_2026-10-27 |
| Ablation 1: same judge rubric as base vs tuned | Met | run.json judge fields |
| Ablation 1: table of Spec adherence and Robustness | Met | results.md columns |
| Ablation 1: failure-mode paragraph | Met | results/ablation_chess_2026-10-27/failure_mode.md |
| Ablation 2: 4 checkpoints at different sizes | Met | 4 sizes x 2 seeds, v2 |
| Ablation 2: every checkpoint on the same eval set | Met on the challenge set | staff set unknown |
| Ablation 2: curve for Spec adherence and Robustness | Met | results/curve_v2_2026-10-28/curve.md |
| Ablation 2: justified smallest N | Partial | 1,298 by the rule on the v3c data (805 on v2); the curve has not flattened; item 13 |
| Public Hub checkpoint with commit hash | Met | hdxsfbr/qwen3-1.7b-chess-coach-hints at 5f3bb80 (v3c, 2026-10-30); v2 at 0200155 |
| One-command eval regenerates the table | Met | eval.py, the brief's literal form with defaults; v3c loaded by Hub id in results/eval_v3c_hub_2026-10-30; notebooks/grader_eval.ipynb runs it from nothing on Colab, executed in a fresh venv 2026-10-30 |
| Raw judge transcripts as JSONL | Met | judge.jsonl, judged_turns.jsonl |
| Staff held-out eval set ingestible | Met (loader) | tolerant loader, unscorable rows listed in run.json; synthetic held-out runs done; staff set not published, item 12 |
| Pinned versions (model and eval code) | Met | base, data and adapter commits pinned; code at tag early-submission; the dirty suffix is explained in item 11 |
| Live comparison in demo | Met | demo_server.py page and demo.py; the video shows it, item 15 |
| Ablation reproducibility (script and training logs) | Met | run_pilot.py, run_judge.py, curve logs |
| Early: finalized spec | Met | |
| Early: full ablation report | Met | |
| Early: eval harness committed | Met | main at 4dafda9, tag early-submission, pushed 2026-10-29 |
| Early: smoke run of the full loop | Met | smoke.sh, results/smoke_2026-10-28.log and results/smoke_2026-10-30.log |
| Early: first dataset and first QLoRA run | Met | |
| Early: first base-vs-tuned numbers in the verification format | Met | results/eval_v2_2026-10-28; checkpoint public |
| Early: failure mode resolved via a v2 dataset | Met | v2 |
| Early: two or more curve points | Met | sixteen |
| Early: draft artifacts (dataset shape, checkpoint, Brainlift) | Met | checkpoint and dataset public on the Hub |
| Final: dataset published | Met | hdxsfbr/chess-coach-hints at 9c1eacd (v3c, 2026-10-30); v2 at a4325db |
| Final: model on Hub plus running inference demo | Met | model on the Hub; demo at https://hdx-lab.tailf4eaa9.ts.net/, item 15 |
| Final: results on own set and staff held-out set | Partial | challenge set and synthetic held-out done for v2 and v3c (results/eval_v3c_heldout_2026-10-30: base 0 of 155, v3c 142 of 155); staff set not published |
| Final: full curve with justified minimum N | Met | v2 and v3c curves, two seeds each, judged; item 13 |
| Final: Brainlift | Draft | item 3 |
| Final: demo video with a live grader prompt | Met | docs/demo/out/chess-coach-demo.mp4, scene 6 is the live prompt |
| Stretch: DPO, adversarial set, composed behavior | Not attempted | |

## Final-day additions, 2026-10-31

Not required by the brief; added for completeness and recorded here so
the requirement table above stays as audited. A prompted-base control
(the ablation's few-shot and structured prompts on Qwen3-1.7B itself:
3% under either, `results/control_base_prompted_2026-10-31`). A third
training seed of v3c (73%; three seeds 77, 70, 73). A hyperparameter
sweep on the v3c data (`sweep.sh`, `results/sweep_2026-10-31`: 3 epochs
77%, r=32 73%, lr 1e-4 73%; none adopted). The second judge family on
v3c (`results/judge_check_2026-10-31`: gemini 47% against haiku 77%,
with the 18 disputed turns hand-read by Andre: haiku right on 15, gemini on 3, and by
his read v3c at 70%, level with v2). A failure analysis of
the seven v3c misses (README "Where v3c fails", Brainlift "The seven that
fail") and the v3d data pass that tests it (110 rows with varied
hard-negative lead-ins; 77% and 73%; not adopted). The grader notebook
executed again with the v3c default (`notebooks/grader_eval.executed.ipynb`,
base 0 of 30, tuned 22 of 30). A concurrency check of the public demo
(`demo_check.py`: three sessions at once, no failures). The suite is at
219 tests. Item 15's video length is 3:59 since the 2026-10-30 re-record.
