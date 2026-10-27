#!/usr/bin/env python3
"""Evaluate a model on a chess-coach eval set with the same harness, checks
and (later) judge as the ablation.

    .venv-train/bin/python eval.py --model local:unsloth/Qwen3-1.7B --eval-set challenge --out results/eval_base
    .venv-train/bin/python eval.py --model local:models/v1/adapter --eval-set challenge --out results/eval_v1
    .venv-train/bin/python eval.py --model local:models/v1/adapter --eval-set data/synthetic_test.jsonl --out results/eval_v1_synth
    python eval.py --model openrouter:anthropic/claude-sonnet-5.5 --eval-set challenge --out results/eval_sonnet

--eval-set is "challenge" (the 30 hand-written scenarios) or a JSONL file of
gated rows (data/synthetic_test.jsonl, or a staff held-out set in the same
shape); a file is turned into scenarios whose user turns are replayed and
whose normal turns pass when the reply is substantive and not a refusal.
The system prompt is the zero-shot one that train.py trained with. The run
directory is a normal pilot run: run_judge.py and rescore.py work on it,
and eval_set.jsonl in it lets them find the loaded scenarios.

--revision pins a Hub model's commit for the record (the local client also
records the cached snapshot's hash in run.json).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

from behaviors import chess_coach
from pilot import report
from pilot.runner import RunConfig, run_pilot

EVAL_SET_FILE = "eval_set.jsonl"


def load_eval_set(path: str, generated_path: str = "data/generated.jsonl") -> List[Dict]:
    """Gated rows as scenarios. The position (needed by the judge) is taken
    from the row when present, else looked up by id in the generated file."""
    positions: Dict[str, Dict] = {}
    if os.path.exists(generated_path):
        with open(generated_path, encoding="utf-8") as fh:
            for line in fh:
                g = json.loads(line)
                positions[g["id"]] = g["position"]
    scenarios = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            users = [m["content"] for m in row["messages"] if m["role"] == "user"]
            kinds = row.get("kinds") or ["direct"] + ["insist"] * (len(users) - 1)
            position = row.get("position") or positions.get(row["id"])
            if position is None:
                raise ValueError("row %s has no position and %s does not list it" % (row["id"], generated_path))
            scenarios.append({
                "id": row["id"],
                "split": row.get("family", "loaded"),
                "position": {"fen": position["fen"], "prose": position["prose"], "answer": position["answer"]},
                "turns": [{"kind": k, "user": u} for k, u in zip(kinds, users)],
            })
    return scenarios


def install_eval_set(path_or_name: str) -> List[Dict]:
    """Make the harness run the chosen scenarios and register them for the
    judge. Returns the scenarios."""
    if path_or_name == "challenge":
        return chess_coach.SCENARIOS
    scenarios = load_eval_set(path_or_name)
    chess_coach.register_scenarios(scenarios)
    chess_coach.SCENARIOS = scenarios
    return scenarios


def register_from_dir(out_dir: str) -> None:
    """Used by run_judge.py and rescore.py: if the directory holds a saved
    eval set, make its scenarios findable."""
    path = os.path.join(out_dir, EVAL_SET_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            chess_coach.register_scenarios([json.loads(line) for line in fh])


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a model on a chess-coach eval set.")
    p.add_argument("--model", required=True, metavar="PROVIDER:MODEL", help="local:<model-or-adapter> or a provider spec")
    p.add_argument("--eval-set", default="challenge", help="'challenge' or a JSONL file of gated rows")
    p.add_argument("--out", required=True)
    p.add_argument("--revision", default=None, help="Hub commit of the model, recorded in run.json")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600.0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    scenarios = install_eval_set(args.eval_set)
    cfg = RunConfig(
        models=[args.model], behaviors=["chess_coach"], strategies=["zero_shot"], limit=args.limit,
        workers=args.workers, out_dir=args.out, temperature=args.temperature, timeout=args.timeout,
    )
    result = run_pilot(cfg)
    os.makedirs(args.out, exist_ok=True)
    if args.eval_set != "challenge":
        with open(os.path.join(args.out, EVAL_SET_FILE), "w", encoding="utf-8") as fh:
            for s in scenarios:
                fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    meta_path = os.path.join(args.out, "run.json")
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["eval"] = {"eval_set": args.eval_set, "model": args.model, "revision": args.revision, "scenarios": len(scenarios)}
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(report.headline_summary(result["records"]))
    print("\nresults: %s" % result["results"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
