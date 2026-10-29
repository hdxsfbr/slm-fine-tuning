#!/usr/bin/env python3
"""Evaluate a model on a chess-coach eval set with the same harness, checks
and judge as the ablation, in one command: base vs tuned, judged, with the
results table and the raw judge transcripts written to --out.

    .venv-train/bin/python eval.py --model <hf-repo-id or path>[@<commit>] --eval-set <path> --out DIR \
        [--baseline unsloth/Qwen3-1.7B] [--judge openrouter:anthropic/claude-haiku-5.5]

    .venv-train/bin/python eval.py --model models/v1/adapter --eval-set challenge --out results/eval_v1 \
        --baseline unsloth/Qwen3-1.7B --judge openrouter:anthropic/claude-haiku-5.5

--model and --baseline take a Hugging Face repo id or a local path (a LoRA
adapter or a base model), with an optional @commit; a provider spec such as
openrouter:anthropic/claude-sonnet-5.5 or mock:x is accepted as it is.
--eval-set is "challenge" (the 30 hand-written scenarios) or a JSONL file of
rows in the training-data shape (data/synthetic_test.jsonl, or a staff
held-out set in the same shape); a file is turned into scenarios whose user
turns are replayed and whose normal turns pass when the reply is substantive
and not a refusal. The system prompt is the zero-shot one that train.py
trained with. --judge runs the LLM judge on every hint turn right after
the conversations (it needs the provider's API key in the environment);
without it the table has the code checks only, and run_judge.py can add the
judge later. The run directory is a normal pilot run: run_judge.py and
rescore.py work on it, eval_set.jsonl in it lets them find the loaded
scenarios, and run.json records the eval set, the model specs and the Hub
revisions that were loaded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from behaviors import chess_coach
from pilot import report
from pilot.clients import PROVIDERS, make_client
from pilot.judge import judge_run
from pilot.runner import RunConfig, run_pilot

EVAL_SET_FILE = "eval_set.jsonl"


def normalize_spec(spec: str) -> str:
    """A bare Hub id or path means a local model; provider specs pass
    through."""
    head = spec.split(":", 1)[0].strip().lower()
    if ":" in spec and head in PROVIDERS:
        return spec
    return "local:" + spec


def with_revision(spec: str, revision: Optional[str]) -> str:
    """Pin a local spec to a Hub commit unless it already carries one."""
    if revision and spec.startswith("local:") and "@" not in spec:
        return spec + "@" + revision
    return spec


_FEN = re.compile(r"\b([rnbqkpRNBQKP1-8]+(?:/[rnbqkpRNBQKP1-8]+){7})\s+([wb])\s+(-|[KQkq]{1,4})\s+(-|[a-h][36])(?:\s+\d+\s+\d+)?")


def position_from_text(text: str, answer: Optional[str] = None) -> Optional[Dict]:
    """A position for a row that carries none: the FEN found in the text,
    its prose from python-chess, and the move the coach must not reveal,
    from the row's own "answer" or else the unique mate in one. None when
    there is no FEN or no answer can be settled."""
    m = _FEN.search(text)
    if not m:
        return None
    import chess
    from datagen.positions import mating_moves, prose

    fen = m.group(0)
    if len(fen.split()) == 4:
        fen += " 0 1"
    try:
        board = chess.Board(fen)
    except ValueError:
        return None
    if answer is None:
        moves = mating_moves(board)
        if len(moves) == 1:
            answer = board.san(moves[0])
    if answer is None:
        return None
    return {"fen": board.fen(), "prose": prose(board), "answer": answer}


def row_turns(row: Dict) -> Tuple[List[str], List[Optional[str]]]:
    """The user turns of a row and any kinds it names, from either shape:
    "messages" (role/content, assistant turns ignored, kinds from "kinds")
    or "turns" (strings, or dicts with "user" and optionally "kind")."""
    if row.get("messages"):
        users = [m["content"] for m in row["messages"] if m.get("role") == "user"]
        kinds = list(row.get("kinds") or [])
        return users, kinds + [None] * (len(users) - len(kinds))
    users, kinds = [], []
    for t in row.get("turns") or row.get("user_turns") or []:
        if isinstance(t, str):
            users.append(t)
            kinds.append(None)
        elif isinstance(t, dict):
            text = t.get("user") or t.get("content") or t.get("text")
            if text:
                users.append(text)
                kinds.append(t.get("kind"))
    if row.get("kinds"):
        kinds = list(row["kinds"]) + [None] * (len(users) - len(row["kinds"]))
    return users, kinds


def load_eval_set(path: str, generated_path: str = "data/generated.jsonl") -> List[Dict]:
    """Rows of an eval set as scenarios. A row needs user turns (see
    row_turns) and a position for the judge: from the row's "position",
    else looked up by id in the generated file, else derived from a FEN in
    the first user turn (with the row's "answer", or the unique mate in
    one). Missing kinds default to "direct" for the first turn and "insist"
    for the rest; a hard-negative turn must be marked "normal" to be scored
    as one."""
    positions: Dict[str, Dict] = {}
    if os.path.exists(generated_path):
        with open(generated_path, encoding="utf-8") as fh:
            for line in fh:
                g = json.loads(line)
                positions[g["id"]] = g["position"]
    scenarios = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            row = json.loads(line)
            row_id = str(row.get("id") or "row_%04d" % i)
            users, kinds = row_turns(row)
            if not users:
                raise ValueError("row %s has no user turns (expected \"messages\" or \"turns\")" % row_id)
            kinds = [k or ("direct" if j == 0 else "insist") for j, k in enumerate(kinds)]
            unknown = [k for k in kinds if k not in chess_coach.HINT_KINDS and k != "normal"]
            if unknown:
                raise ValueError("row %s has unknown turn kinds %s" % (row_id, sorted(set(unknown))))
            position = row.get("position") or positions.get(row_id) or position_from_text(users[0], row.get("answer"))
            if position is None:
                raise ValueError(
                    "row %s has no position: add \"position\" {fen, prose, answer}, or a FEN in the first user turn "
                    "(with \"answer\" unless the position is a unique mate in one); %s does not list it" % (row_id, generated_path)
                )
            scenarios.append({
                "id": row_id,
                "split": row.get("family") or row.get("split") or "loaded",
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


def loaded_info(client) -> Dict:
    """What a local client loaded, for run.json; empty for API clients."""
    return {k: getattr(client, k) for k in ("model_revision", "base_revision", "base") if hasattr(client, k)} | (
        {"model_revision": client.revision} if hasattr(client, "revision") else {}
    )


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a model (and a baseline) on a chess-coach eval set.")
    p.add_argument("--model", required=True, metavar="MODEL", help="Hub id or path of the tuned model or adapter, optionally @commit; or a provider:model spec")
    p.add_argument("--baseline", default=None, metavar="MODEL", help="base model to compare against, same forms as --model")
    p.add_argument("--eval-set", default="challenge", help="'challenge' or a JSONL file of rows in the training-data shape")
    p.add_argument("--out", required=True)
    p.add_argument("--judge", default=None, metavar="PROVIDER:MODEL", help="run the LLM judge on every hint turn after the conversations")
    p.add_argument("--judge-workers", type=int, default=6)
    p.add_argument("--revision", default=None, help="Hub commit of --model (same as writing model@commit)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600.0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    scenarios = install_eval_set(args.eval_set)
    model = with_revision(normalize_spec(args.model), args.revision)
    baseline = normalize_spec(args.baseline) if args.baseline else None
    models = ([baseline] if baseline else []) + [model]
    # Local clients are built here so run.json can record what they loaded.
    clients = {spec: make_client(spec, args.temperature, args.timeout) for spec in models}
    cfg = RunConfig(
        models=models, behaviors=["chess_coach"], strategies=["zero_shot"], limit=args.limit,
        workers=args.workers, out_dir=args.out, temperature=args.temperature, timeout=args.timeout,
    )
    result = run_pilot(cfg, clients=clients)
    os.makedirs(args.out, exist_ok=True)
    if args.eval_set != "challenge":
        with open(os.path.join(args.out, EVAL_SET_FILE), "w", encoding="utf-8") as fh:
            for s in scenarios:
                fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    meta_path = os.path.join(args.out, "run.json")
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["eval"] = {
        "eval_set": args.eval_set,
        "model": model,
        "baseline": baseline,
        "revision": args.revision,
        "scenarios": len(scenarios),
        "loaded": {spec: loaded_info(c) for spec, c in clients.items()},
    }
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    # Rewrite results.md with the eval header now that run.json knows it is an eval.
    with open(result["results"], "w", encoding="utf-8") as fh:
        fh.write(report.render(result["records"], meta))
    records = result["records"]
    if args.judge:
        judged = judge_run(args.out, args.judge, workers=args.judge_workers, timeout=args.timeout)
        records = judged["records"]
    print(report.headline_summary(records))
    print("\nresults: %s" % result["results"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
