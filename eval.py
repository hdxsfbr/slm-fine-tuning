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
import datetime as dt
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


DEFAULT_BASELINE = "unsloth/Qwen3-1.7B"
DEFAULT_JUDGE = "openrouter:anthropic/claude-haiku-5.5"
# Environment variable each judge provider needs, checked before any model loads.
JUDGE_KEYS = {"openrouter": "OPENROUTER_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def default_out(model_spec: str) -> str:
    """results/eval_<model>_<date>: the model's last path or repo component."""
    name = model_spec.split("@")[0].rstrip("/").split("/")[-1]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "model"
    return os.path.join("results", "eval_%s_%s" % (slug, dt.date.today().isoformat()))


def resolve_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """The brief's literal command, `eval.py --model <hf-repo-id> --eval-set
    <path>`, regenerates the base-vs-tuned table: for a Hub id or path the
    baseline and the judge default to the project's, and the output
    directory is named after the model and the date. Provider specs (the
    mock, an API model) get no defaults, so tests and ablation runs are
    unchanged. --no-baseline and --no-judge switch the defaults off."""
    local = normalize_spec(args.model).startswith("local:")
    if args.no_baseline:
        args.baseline = None
    elif args.baseline is None and local:
        args.baseline = DEFAULT_BASELINE
    if args.no_judge:
        args.judge = None
    elif args.judge is None and local:
        args.judge = DEFAULT_JUDGE
    if args.out is None:
        args.out = default_out(args.model)
    return args


def missing_judge_key(judge: Optional[str]) -> Optional[str]:
    """The environment variable the judge needs and does not have, or None."""
    if not judge:
        return None
    env = JUDGE_KEYS.get(judge.split(":", 1)[0].strip().lower())
    if env and not os.environ.get(env):
        return env
    return None


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


_SINGLE_TURN_KEYS = ("prompt", "user", "question", "input", "text")


def row_turns(row: Dict) -> Tuple[List[str], List[Optional[str]]]:
    """The user turns of a row and any kinds it names, from any of these
    shapes: "messages" or "conversation" (role/content, or ShareGPT's
    from/value; assistant turns ignored, kinds from "kinds"), "turns" or
    "user_turns" (strings, or dicts with "user" and optionally "kind"), or
    a single-turn row with "prompt", "user", "question", "input" or
    "text"."""
    messages = row.get("messages") or row.get("conversation")
    if messages:
        users = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            role = (m.get("role") or ("user" if m.get("from") in ("human", "user") else "assistant")).lower()
            text = m.get("content") if m.get("content") is not None else m.get("value")
            if role == "user" and text:
                users.append(str(text))
        kinds = list(row.get("kinds") or [])
        return users, kinds + [None] * (len(users) - len(kinds))
    users, kinds = [], []
    for key in _SINGLE_TURN_KEYS:
        if isinstance(row.get(key), str) and row[key].strip() and not (row.get("turns") or row.get("user_turns")):
            return [row[key]], [row.get("kind")]
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


def load_eval_set(path: str, generated_path: str = "data/generated.jsonl", skipped: Optional[List[Dict]] = None) -> List[Dict]:
    """Rows of an eval set as scenarios. A row needs user turns (see
    row_turns) and a position for the judge: from the row's "position",
    else looked up by id in the generated file, else derived from a FEN in
    the first user turn (with the row's "answer", or the unique mate in
    one). Missing kinds default to "direct" for the first turn and "insist"
    for the rest; a hard-negative turn must be marked "normal" to be scored
    as one. A row that cannot be scored raises ValueError, or, when a
    `skipped` list is given, is recorded there with its reason and left
    out, so a set in an unexpected shape still runs on its usable rows."""
    def unusable(row_id: str, why: str) -> None:
        if skipped is None:
            raise ValueError("row %s %s" % (row_id, why))
        skipped.append({"id": row_id, "reason": why})

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
                unusable(row_id, "has no user turns (expected \"messages\", \"turns\" or \"prompt\")")
                continue
            kinds = [k or ("direct" if j == 0 else "insist") for j, k in enumerate(kinds)]
            unknown = [k for k in kinds if k not in chess_coach.HINT_KINDS and k != "normal"]
            if unknown:
                unusable(row_id, "has unknown turn kinds %s" % sorted(set(unknown)))
                continue
            position = row.get("position") or positions.get(row_id) or position_from_text(users[0], row.get("answer"))
            if position is None:
                unusable(
                    row_id,
                    "has no position: add \"position\" {fen, prose, answer}, or a FEN in the first user turn "
                    "(with \"answer\" unless the position is a unique mate in one); %s does not list it" % generated_path,
                )
                continue
            scenarios.append({
                "id": row_id,
                "split": row.get("family") or row.get("split") or "loaded",
                "position": {"fen": position["fen"], "prose": position["prose"], "answer": position["answer"]},
                "turns": [{"kind": k, "user": u} for k, u in zip(kinds, users)],
            })
    return scenarios


def install_eval_set(path_or_name: str, skipped: Optional[List[Dict]] = None) -> List[Dict]:
    """Make the harness run the chosen scenarios and register them for the
    judge. Returns the scenarios."""
    if path_or_name == "challenge":
        return chess_coach.SCENARIOS
    scenarios = load_eval_set(path_or_name, skipped=skipped)
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
    p.add_argument("--baseline", default=None, metavar="MODEL",
                   help="base model to compare against, same forms as --model (default %s for a Hub id or path)" % DEFAULT_BASELINE)
    p.add_argument("--no-baseline", action="store_true", help="run the tuned model only")
    p.add_argument("--eval-set", default="challenge", help="'challenge' or a JSONL file of rows in the training-data shape")
    p.add_argument("--out", default=None, help="output directory (default results/eval_<model>_<date>)")
    p.add_argument("--judge", default=None, metavar="PROVIDER:MODEL",
                   help="run the LLM judge on every hint turn after the conversations (default %s for a Hub id or path; needs its key)" % DEFAULT_JUDGE)
    p.add_argument("--no-judge", action="store_true", help="code checks only, no judge calls")
    p.add_argument("--judge-workers", type=int, default=6)
    p.add_argument("--revision", default=None, help="Hub commit of --model (same as writing model@commit)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--timeout", type=float, default=600.0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = resolve_defaults(parse_args(argv))
    env = missing_judge_key(args.judge)
    if env:
        print("the judge %s needs %s in the environment; export it, or pass --no-judge for the code checks only"
              % (args.judge, env), file=sys.stderr)
        return 2
    skipped: List[Dict] = []
    scenarios = install_eval_set(args.eval_set, skipped)
    if skipped:
        print("%d of %d rows in %s cannot be scored and are left out (listed in run.json under eval.skipped_rows):"
              % (len(skipped), len(skipped) + len(scenarios), args.eval_set), file=sys.stderr)
        for row in skipped[:10]:
            print("  %s %s" % (row["id"], row["reason"]), file=sys.stderr)
    if not scenarios:
        print("no scorable rows in %s" % args.eval_set, file=sys.stderr)
        return 2
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
        "skipped_rows": skipped,
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
