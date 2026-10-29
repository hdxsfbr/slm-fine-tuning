---
base_model: unsloth/Qwen3-1.7B
library_name: peft
license: apache-2.0
language:
- en
tags:
- chess
- lora
- qlora
- unsloth
- behavior-fine-tuning
---

# Hint-only chess coach (LoRA adapter for Qwen3-1.7B)

A QLoRA adapter that makes Qwen3-1.7B hold one falsifiable behavior: asked what to play in their
position, or anything that would identify the move, the coach replies with one hint of at most two
sentences that neither names nor describes the move, however the user asks and even after the game
is over; every other chess question is answered fully, squares and moves included.

## Pinned versions

- Base model: `unsloth/Qwen3-1.7B-unsloth-bnb-4bit`, revision `a972f4304f86a0a705d35b378d7a7675d58063a7`
- Training data: `data/v2/train.jsonl`, 805 rows, sha256 `39ddf3110352249405686d2f8cf9c36c4dc122e386e4120359600741a9225fa6`
- Eval and training code: commit `0d41d41849a48d8b8c581d4dbe1b09fc77158b1d-dirty` of the project repository
- Trained 2026-10-28T16:56:33+00:00; 202 steps, final training loss 1.3854668529907075

## Training configuration

```json
{
  "max_seq_length": 2048,
  "load_in_4bit": true,
  "lora_r": 16,
  "lora_alpha": 16,
  "lora_dropout": 0,
  "target_modules": [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj"
  ],
  "learning_rate": 0.0002,
  "epochs": 2.0,
  "batch": 2,
  "grad_accum": 4,
  "warmup_steps": 5,
  "optim": "adamw_8bit",
  "weight_decay": 0.01,
  "scheduler": "linear",
  "seed": 3407,
  "responses_only": true,
  "instruction_part": "<|im_start|>user\n",
  "response_part": "<|im_start|>assistant\n"
}
```

Library versions: cuda 13.0, gpu NVIDIA GeForce RTX 4090, peft 0.21.2, python 3.12.3, torch 2.14.1+cu130, transformers 5.17.0, trl 1.15.0, unsloth 2026.10.9

## Use

```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained("hdxsfbr/qwen3-1.7b-chess-coach-hints", max_seq_length=8192, load_in_4bit=True)
FastLanguageModel.for_inference(model)
```

Use the zero-shot system prompt from `behaviors/chess_coach.py` (`SPEC`) and Qwen3's chat template with
thinking disabled, as `eval.py` does. The one-command evaluation against the base model is
`eval.py --model hdxsfbr/qwen3-1.7b-chess-coach-hints@<commit> --baseline unsloth/Qwen3-1.7B --eval-set <path> --judge <judge>`.
