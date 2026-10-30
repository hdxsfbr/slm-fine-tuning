#!/usr/bin/env python3
"""Publish the adapter and the dataset to the Hugging Face Hub, and write
the resulting commit hashes back into the local manifests so the
submission can cite them.

    export HF_TOKEN=$(tr -d '\\n\\r ' < ~/.config/agentforge/hf_token)
    python push_to_hub.py model models/v2 --repo <user>/qwen3-1.7b-chess-coach-hints
    python push_to_hub.py dataset data/v2 --repo <user>/chess-coach-hints
    python push_to_hub.py model models/v2 --repo ... --dry-run   # list what would be uploaded

The model repo gets <model>/adapter/* plus a model card built from the
manifest (base model and its revision, data sha256 and row count, the
training config, library versions, the eval-code commit). The dataset repo
gets train.jsonl, synthetic_test.jsonl, manifest.json and gate_report.md
plus a dataset card. Both are created public unless --private is given.
After the upload, <model>/manifest.json (or <data>/manifest.json) gains a
"hub" field with the repo id, the commit hash and the time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Dict, List

MODEL_FILES = ("adapter",)
DATASET_FILES = ("train.jsonl", "synthetic_test.jsonl", "manifest.json", "gate_report.md")


def git_sha() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def load_json(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def model_card(repo: str, manifest: Dict, code_sha: str) -> str:
    cfg = manifest.get("config", {})
    data = manifest.get("data", {})
    train = manifest.get("train", {})
    versions = manifest.get("versions", {})
    base = manifest.get("base_loaded") or manifest.get("base_model")
    lines = [
        "---",
        "base_model: %s" % manifest.get("base_model", base),
        "library_name: peft",
        "license: apache-2.0",
        "language:",
        "- en",
        "tags:",
        "- chess",
        "- lora",
        "- qlora",
        "- unsloth",
        "- behavior-fine-tuning",
        "---",
        "",
        "# Hint-only chess coach (LoRA adapter for Qwen3-1.7B)",
        "",
        "A QLoRA adapter that makes Qwen3-1.7B hold one falsifiable behavior: asked what to play in their",
        "position, or anything that would identify the move, the coach replies with one hint of at most two",
        "sentences that neither names nor describes the move, however the user asks and even after the game",
        "is over; every other chess question is answered fully, squares and moves included.",
        "",
        "## Pinned versions",
        "",
        "- Base model: `%s`, revision `%s`" % (base, manifest.get("base_revision")),
        "- Training data: `%s`, %s rows, sha256 `%s`" % (data.get("path"), data.get("rows_used"), data.get("sha256")),
        "- Eval and training code: commit `%s` of the project repository" % code_sha,
        "- Trained %s; %s steps, final training loss %s" % (manifest.get("created_at"), train.get("steps"), train.get("train_loss")),
        "",
        "## Training configuration",
        "",
        "```json",
        json.dumps(cfg, indent=2),
        "```",
        "",
        "Library versions: " + ", ".join("%s %s" % kv for kv in sorted(versions.items())),
        "",
        "## Use",
        "",
        "```python",
        "from unsloth import FastLanguageModel",
        'model, tokenizer = FastLanguageModel.from_pretrained("%s", max_seq_length=8192, load_in_4bit=True)' % repo,
        "FastLanguageModel.for_inference(model)",
        "```",
        "",
        "Use the zero-shot system prompt from `behaviors/chess_coach.py` (`SPEC`) and Qwen3's chat template with",
        "thinking disabled, as `eval.py` does. The one-command evaluation against the base model is",
        "`eval.py --model %s@<commit> --baseline unsloth/Qwen3-1.7B --eval-set <path> --judge <judge>`." % repo,
        "",
    ]
    return "\n".join(lines)


def dataset_card(repo: str, manifest: Dict) -> str:
    out = manifest.get("output", {})
    judge = manifest.get("judge", {})
    stages = manifest.get("stages", [])
    lines = [
        "---",
        "license: apache-2.0",
        "language:",
        "- en",
        "task_categories:",
        "- text-generation",
        "tags:",
        "- chess",
        "- behavior-fine-tuning",
        "- synthetic",
        "size_categories:",
        "- n<1K" if (out.get("train", {}).get("rows", 0) < 1000) else "- 1K<n<10K",
        "---",
        "",
        "# Hint-only chess coach conversations",
        "",
        "Multi-turn conversations in which a chess coach is pressed, in many ways, to name the winning move in",
        "the user's position and only ever hints, while answering unrelated chess questions fully with squares",
        "and moves. Written by a frontier teacher model to seeded plans (persona x situation x pressure kinds x",
        "hard negatives) over python-chess-verified mate-in-one positions, then filtered by a gate: structure,",
        "dedupe, code checks (no square or move in any hint, squares required in answers), an LLM judge for hints",
        "that state the move in words, and leakage against the evaluation set. The split is held out by position.",
        "",
        "## Files",
        "",
        "- `train.jsonl`: %s rows, sha256 `%s`" % (out.get("train", {}).get("rows"), out.get("train", {}).get("sha256")),
        "- `synthetic_test.jsonl`: %s rows, sha256 `%s`, positions disjoint from train" % (out.get("synthetic_test", {}).get("rows"), out.get("synthetic_test", {}).get("sha256")),
        "- `manifest.json`, `gate_report.md`: the gate's stages and counts",
        "",
        "Row shape: `{\"id\", \"family\", \"persona\", \"kinds\", \"messages\": [{\"role\", \"content\"}, ...]}`; `kinds`",
        "names the pressure kind of each user turn (`normal` marks a hard negative).",
        "",
        "## Gate",
        "",
    ]
    if manifest.get("merged_from"):
        # A merged version (run_datagen.py merge): every source was gated on
        # its own, so the card shows each gate; the merge only checks that
        # no test row shares a position with a train row.
        lines += [
            "This version merges %d gated batches; row ids carry the batch name as a prefix. Each batch went through"
            % len(manifest["merged_from"]),
            "the same gate on its own, and the merge checked that the test rows share no position with the train rows",
            "(%s held-out positions, %s shared)." % (manifest.get("holdout", {}).get("test_placements"), manifest.get("holdout", {}).get("placements_shared_with_train")),
            "",
        ]
        for entry in manifest["merged_from"]:
            gate = entry.get("gate", {})
            lines += [
                "### `%s`: %s train rows, %s test rows" % (entry.get("name"), entry.get("train.jsonl", {}).get("rows"), entry.get("synthetic_test.jsonl", {}).get("rows")),
                "",
            ]
            lines += _gate_table(gate.get("stages", []), gate.get("judge", {}))
    else:
        lines += _gate_table(stages, judge)
    return "\n".join(lines)


def _gate_table(stages, judge) -> list:
    lines = ["| Stage | In | Out | Dropped |", "|---|---|---|---|"]
    for s in stages:
        lines.append("| %s | %s | %s | %s |" % (s.get("stage"), s.get("in"), s.get("out"), s.get("dropped")))
    lines += [
        "",
        "Judge: `%s`, rubric `%s`, %s verdicts." % (judge.get("model"), judge.get("rubric"), judge.get("verdicts")),
        "",
    ]
    return lines


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Push the adapter or the dataset to the Hugging Face Hub.")
    p.add_argument("what", choices=["model", "dataset"])
    p.add_argument("path", help="models/<run> for a model, data/<version> for a dataset")
    p.add_argument("--repo", required=True, help="<user>/<name> on the Hub")
    p.add_argument("--private", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print the files and the card, upload nothing")
    args = p.parse_args(argv)

    manifest_path = os.path.join(args.path, "manifest.json")
    manifest = load_json(manifest_path)
    code_sha = git_sha()
    if args.what == "model":
        files: List[str] = [os.path.join(args.path, "adapter")]
        card = model_card(args.repo, manifest, code_sha)
        repo_type = "model"
    else:
        files = [os.path.join(args.path, f) for f in DATASET_FILES]
        card = dataset_card(args.repo, manifest)
        repo_type = "dataset"
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        sys.exit("missing: %s" % ", ".join(missing))
    if args.dry_run:
        print("would upload to %s (%s, %s):" % (args.repo, repo_type, "private" if args.private else "public"))
        for f in files:
            print("  " + f)
        print("\n--- card ---\n" + card)
        return 0

    from huggingface_hub import HfApi  # noqa: WPS433

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN is not set")
    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type=repo_type, private=args.private, exist_ok=True)
    card_path = os.path.join(args.path, "README.hub.md")
    with open(card_path, "w", encoding="utf-8") as fh:
        fh.write(card)
    message = "Upload %s from %s (code %s)" % (args.what, args.path, code_sha)
    if args.what == "model":
        info = api.upload_folder(repo_id=args.repo, repo_type=repo_type, folder_path=files[0], path_in_repo=".", commit_message=message)
        info = api.upload_file(repo_id=args.repo, repo_type=repo_type, path_or_fileobj=card_path, path_in_repo="README.md", commit_message=message + " (card)")
    else:
        from huggingface_hub import CommitOperationAdd

        ops = [CommitOperationAdd(path_in_repo=os.path.basename(f), path_or_fileobj=f) for f in files]
        ops.append(CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=card_path))
        info = api.create_commit(repo_id=args.repo, repo_type=repo_type, operations=ops, commit_message=message)
    commit = getattr(info, "oid", None) or getattr(info, "commit_url", "").rsplit("/", 1)[-1]
    manifest["hub"] = {
        "repo_id": args.repo,
        "repo_type": repo_type,
        "commit": commit,
        "url": "https://huggingface.co/%s%s/tree/%s" % ("datasets/" if repo_type == "dataset" else "", args.repo, commit),
        "pushed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "code_git_sha": code_sha,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("pushed %s to %s at commit %s" % (args.what, args.repo, commit))
    print(manifest["hub"]["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
