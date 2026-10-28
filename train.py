#!/usr/bin/env python3
"""QLoRA fine-tune of Qwen3-1.7B on the gated chess-coach conversations.

    .venv-train/bin/python train.py --data data/train.jsonl --out models/v1

The configuration is the lecture slide's, unchanged unless a flag says so:
unsloth/Qwen3-1.7B in 4-bit, LoRA r=16, alpha=16, dropout 0 on the
attention and MLP projections, learning rate 2e-4, 2 epochs, batch 2 with
gradient accumulation 4, seed 3407, max sequence length 2048, the model's
own chat template, and loss on the assistant turns only. The system prompt
is the eval harness's zero-shot prompt, so train and eval see the same one.

--n takes a nested subset for the data-efficiency curve: the first n rows
of one fixed permutation (numpy default_rng(0)), so N/2 is a subset of N.

Writes <out>/adapter (LoRA weights and tokenizer) and <out>/manifest.json
with the base revision, data hash, row count, config, library versions,
seeds and the loss log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Dict, List, Optional

from behaviors.chess_coach import STRATEGIES

BASE_MODEL = "unsloth/Qwen3-1.7B"
MAX_SEQ_LENGTH = 2048
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
INSTRUCTION_PART = "<|im_start|>user\n"
RESPONSE_PART = "<|im_start|>assistant\n"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def load_rows(path: str, n: Optional[int], perm_seed: int = 0) -> List[Dict]:
    import numpy as np

    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    if n is None or n >= len(rows):
        return rows
    perm = np.random.default_rng(perm_seed).permutation(len(rows))
    return [rows[i] for i in perm[:n]]


def render(tokenizer, system: str, messages: List[Dict[str, str]]) -> str:
    chat = [{"role": "system", "content": system}] + messages
    return tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=False)


def cached_revision(repo: str) -> Optional[str]:
    """The commit hash of the Hub snapshot in the local cache: refs/main of
    the repo's cache folder, else the single snapshot directory name."""
    if os.path.isdir(repo):
        return None
    try:
        from huggingface_hub import snapshot_download

        return os.path.basename(snapshot_download(repo, local_files_only=True))
    except Exception:
        pass
    cache = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface")), "hub")
    folder = os.path.join(cache, "models--" + repo.replace("/", "--"))
    ref = os.path.join(folder, "refs", "main")
    if os.path.isfile(ref):
        with open(ref, encoding="utf-8") as fh:
            return fh.read().strip() or None
    snaps = os.path.join(folder, "snapshots")
    if os.path.isdir(snaps):
        names = sorted(os.listdir(snaps))
        return names[-1] if names else None
    return None


def git_sha() -> Optional[str]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="QLoRA fine-tune of Qwen3-1.7B on the chess-coach data.")
    p.add_argument("--data", default="data/train.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=None, help="nested subset size for the data-efficiency curve")
    p.add_argument("--perm-seed", type=int, default=0, help="seed of the one permutation the subsets are taken from")
    p.add_argument("--base", default=BASE_MODEL)
    p.add_argument("--system", default="zero_shot", choices=list(STRATEGIES), help="system prompt used at train and eval")
    p.add_argument("--epochs", type=float, default=2.0)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--seed", type=int, default=3407)
    p.add_argument("--r", type=int, default=16)
    p.add_argument("--alpha", type=int, default=16)
    p.add_argument("--dry-run", action="store_true", help="render the rows and report lengths and masking, no training")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    t_start = time.time()
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only

    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    rows = load_rows(args.data, args.n, args.perm_seed)
    system = STRATEGIES[args.system]
    print("rows: %d of %s (sha256 %s)" % (len(rows), args.data, sha256_of(args.data)[:16]), file=sys.stderr)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base, max_seq_length=MAX_SEQ_LENGTH, load_in_4bit=True, dtype=None
    )
    texts = [render(tokenizer, system, r["messages"]) for r in rows]
    lengths = [len(tokenizer(t)["input_ids"]) for t in texts]
    over = sum(1 for n in lengths if n > MAX_SEQ_LENGTH)
    print("tokens per row: min %d, median %d, max %d; over %d: %d" % (
        min(lengths), sorted(lengths)[len(lengths) // 2], max(lengths), MAX_SEQ_LENGTH, over), file=sys.stderr)

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.r,
        target_modules=TARGET_MODULES,
        lora_alpha=args.alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )
    dataset = Dataset.from_list([{"text": t} for t in texts])
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_length=MAX_SEQ_LENGTH,
            per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=args.grad_accum,
            warmup_steps=5,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            logging_steps=5,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=args.seed,
            output_dir=os.path.join(args.out, "checkpoints"),
            report_to="none",
            save_strategy="no",
        ),
    )
    trainer = train_on_responses_only(trainer, instruction_part=INSTRUCTION_PART, response_part=RESPONSE_PART)

    # Masking check on the first row: how many tokens carry loss, and the
    # text they cover, so a template mismatch is caught before training.
    sample = trainer.train_dataset[0]
    labels = sample["labels"]
    kept = [i for i, l in enumerate(labels) if l != -100]
    kept_text = tokenizer.decode([sample["input_ids"][i] for i in kept])
    print("masking: %d of %d tokens carry loss on row 0; first trained text: %r" % (
        len(kept), len(labels), kept_text[:160]), file=sys.stderr)
    if not kept:
        print("no tokens carry loss: the chat template does not match the instruction/response markers", file=sys.stderr)
        return 1
    if args.dry_run:
        print("dry run, not training", file=sys.stderr)
        return 0

    stats = trainer.train()
    os.makedirs(args.out, exist_ok=True)
    adapter_dir = os.path.join(args.out, "adapter")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    import peft
    import transformers
    import trl
    import unsloth

    # Unsloth swaps a 4-bit request for its pre-quantized repo when one
    # exists (unsloth/Qwen3-1.7B becomes unsloth/Qwen3-1.7B-unsloth-bnb-4bit),
    # so the manifest records what was actually loaded and its revision.
    base_loaded = getattr(getattr(model, "config", None), "_name_or_path", None) or args.base
    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "base_model": args.base,
        "base_loaded": base_loaded,
        "base_revision": cached_revision(base_loaded) or cached_revision(args.base),
        "data": {"path": args.data, "sha256": sha256_of(args.data), "rows_total": len(load_rows(args.data, None)), "rows_used": len(rows), "n": args.n, "perm_seed": args.perm_seed},
        "system_prompt": args.system,
        "config": {
            "max_seq_length": MAX_SEQ_LENGTH, "load_in_4bit": True, "lora_r": args.r, "lora_alpha": args.alpha, "lora_dropout": 0,
            "target_modules": TARGET_MODULES, "learning_rate": args.lr, "epochs": args.epochs, "batch": args.batch,
            "grad_accum": args.grad_accum, "warmup_steps": 5, "optim": "adamw_8bit", "weight_decay": 0.01,
            "scheduler": "linear", "seed": args.seed, "responses_only": True,
            "instruction_part": INSTRUCTION_PART, "response_part": RESPONSE_PART,
        },
        "tokens_per_row": {"min": min(lengths), "median": sorted(lengths)[len(lengths) // 2], "max": max(lengths), "over_max": over},
        "train": {
            "steps": trainer.state.global_step, "train_loss": stats.metrics.get("train_loss"),
            "runtime_s": round(stats.metrics.get("train_runtime", 0), 1), "log": trainer.state.log_history,
        },
        "versions": {
            "python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
            "transformers": transformers.__version__, "trl": trl.__version__, "peft": peft.__version__,
            "unsloth": unsloth.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "code_git_sha": git_sha(),
        "wall_s": round(time.time() - t_start, 1),
    }
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("trained %d steps, loss %.4f, %.0fs -> %s" % (
        manifest["train"]["steps"], manifest["train"]["train_loss"] or 0.0, manifest["train"]["runtime_s"], adapter_dir), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
