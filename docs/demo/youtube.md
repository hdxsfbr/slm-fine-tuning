# YouTube listing for the demo video

Published 2026-10-31 at <https://youtu.be/BvwQkEsGI0o>.

Video: `out/chess-coach-demo.mp4` (3:59, 1440x900, H.264). Thumbnail: `thumbnail.png` (1280x720,
76 KB, under the 2 MB limit). Chapter times come from `out/plan.tsv` and are exact for this cut; a
re-render changes them.

Upload notes: category Science & Technology; tick "altered or synthetic content" because the
narration is a cloned voice; the chapter list must keep its `0:00` first line to be recognised.

## Title (84 characters)

Hint-Only Chess Coach: Fine-Tuning Qwen3-1.7B to Hold a Rule Frontier Prompts Can't

Alternate: A 1.7B Model Beats Frontier Prompts at One Rule: the Hint-Only Chess Coach (QLoRA)

## Description

A 1.7B-parameter Qwen3 model, fine-tuned with QLoRA on 1,298 synthetic conversations, holds one rule that Claude Sonnet and GPT could not hold under any prompt I tried: as a chess coach it only ever hints. It never names the move or a square for your position, however you ask, and it answers every other chess question in full.

The video shows the prompt ceiling (the best frontier cell holds the rule in 20% of 30 scripted conversations), the tuned model next to its base on a live position, two kinds of pressure, a rules question, a prompt written for the recording, and the numbers: on the hand-written challenge set the base passes 0%, the best frontier prompt 20%, the first two tuned models 50% and 70%, and the submitted one 77% (every pressure conversation, 6 of 13 mixed); on 155 held-out conversations it passes 92%.

Nothing on screen is simulated. Every reply is a live call to the two models with greedy decoding and the same system prompt as the evaluation; the only edits are the removal of waiting time while a model generates. The narration is a clone of my own voice (Chatterbox), used with my permission.

Chapters
0:00 The rule
0:27 The prompt ceiling
1:01 Live: a position, base vs tuned
1:38 Live: pressure
2:06 Live: a rules question
2:35 Live: a grader prompt
2:56 Results
3:42 Artifacts

Try it: https://hdx-lab.tailf4eaa9.ts.net/
Model: https://huggingface.co/hdxsfbr/qwen3-1.7b-chess-coach-hints
Dataset: https://huggingface.co/datasets/hdxsfbr/chess-coach-hints
Code: https://labs.gauntletai.com/andrebatista/slm-fine-tuning

Stack: Qwen3-1.7B through Unsloth in 4-bit, QLoRA r=16, python-chess for verified mate-in-one positions, claude-sonnet-5.5 as the data teacher, claude-haiku-5.5 as the LLM judge, gemini-3.1-flash-lite as a second judge family, one judge rubric for the ablation, the data gate and the evaluation.

Tags: fine-tuning, QLoRA, LoRA, Qwen3, small language models, LLM evaluation, LLM as judge, synthetic data, chess, Unsloth, prompt engineering, behavior fine-tuning
