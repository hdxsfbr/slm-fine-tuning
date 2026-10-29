#!/usr/bin/env python3
"""Data-efficiency curve: train on nested subsets, evaluate each, report.

    .venv-train/bin/python run_curve.py --sizes 228 114 57 --full models/v1 --out results/curve_2026-10-27

For each size n, trains an adapter on the first n rows of train.py's fixed
permutation (so N/2 is a subset of N) into models/curve_<n>, evaluates it
on the challenge set into <out>/eval_<n>, and renders <out>/curve.md with
the pass rates next to the full-N run. Training and evaluation steps that
already exist are skipped, so the script can be rerun after an
interruption. No API calls: the table is code checks; run_judge.py on each
eval directory adds the judged column later.

The threshold rule is fixed before the numbers are looked at (docs/plan.md,
step 7): the smallest n whose challenge-set pass rate is within 0.05 of the
full-N run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

THRESHOLD = 0.05
PYTHON = sys.executable


def run(cmd: List[str], log_path: str) -> None:
    print("$ " + " ".join(cmd), file=sys.stderr)
    with open(log_path, "w", encoding="utf-8") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, check=True)


def cell(eval_dir: str, model_contains: Optional[str] = None) -> Optional[Dict]:
    """Pass rates of one eval directory from its transcripts, with the
    behavior module's own aggregate so the curve and the results tables
    agree. Errored conversations count as failures (they stay in the
    denominator). model_contains keeps only the records of one model, for
    an eval directory that also holds the baseline."""
    path = os.path.join(eval_dir, "transcripts.jsonl")
    if not os.path.exists(path):
        return None
    from behaviors import chess_coach
    from eval import register_from_dir

    register_from_dir(eval_dir)
    recs = [json.loads(line) for line in open(path, encoding="utf-8")]
    if model_contains:
        recs = [r for r in recs if model_contains in r.get("model", "")]
    if not recs:
        return None
    scored = [r for r in recs if r.get("score")]
    judged = [r for r in scored if r.get("judge") and r["judge"].get("leak_free") is not None]
    hint = [t for r in scored for t in r["score"]["turns"] if t["kind"] != "normal"]
    normal = [t for r in scored for t in r["score"]["turns"] if t["kind"] == "normal"]
    agg = chess_coach.aggregate(recs)
    spec_k, spec_n = agg["spec_adherence"]
    return {
        "n": len(recs),
        "n_scored": len(scored),
        "errors": agg["errors"],
        "checks": agg["overall"][0] / len(recs) if recs else None,
        "spec": spec_k / spec_n if spec_n else None,
        "final": (agg["final"][0] / len(recs)) if judged else None,
        "leak_turns": sum(1 for t in hint if t["leaks"]),
        "hint_turns": len(hint),
        "answered": sum(1 for t in normal if t["answered"]),
        "normal_turns": len(normal),
    }


def manifest(model_dir: str) -> Dict:
    path = os.path.join(model_dir, "manifest.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def pct(x: Optional[float]) -> str:
    return "n/a" if x is None else "%d%%" % round(100 * x)


def render(rows: List[Dict], full_n: int) -> str:
    out = ["# Data-efficiency curve", "",
           "Challenge set, 30 scenarios, zero-shot system prompt, greedy decoding. `All checks` is the code-check pass rate per conversation; "
           "`Spec adherence` is the per-turn pass rate (checks and judge); `Robustness` is the per-conversation pass rate with every turn "
           "holding (checks and judge), the headline. Errored conversations count as failures.", "",
           "Rule, fixed before looking (docs/plan.md step 7): the smallest n whose challenge-set pass rate is within %.2f of the full-N run." % THRESHOLD, "",
           "| n | seed | steps | train loss | All checks | Spec adherence (turns) | Robustness (judged) | named leaks / hint turns | negatives answered | errors |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["cell"] or {}
        out.append("| %d%s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["n"], " (full)" if r["n"] == full_n else "", r.get("seed", 3407), r.get("steps", "?"),
            "%.3f" % r["loss"] if r.get("loss") is not None else "?",
            pct(c.get("checks")), pct(c.get("spec")), pct(c.get("final")),
            "%s / %s" % (c.get("leak_turns", "?"), c.get("hint_turns", "?")),
            "%s / %s" % (c.get("answered", "?"), c.get("normal_turns", "?")),
            c.get("errors", "?")))
    # The rule is applied to the mean over seeds per size, against the
    # full-N run's seed-3407 value (the committed v1 model).
    by_n: Dict[int, List[Dict]] = {}
    for r in rows:
        by_n.setdefault(r["n"], []).append(r)
    full = next((r for r in rows if r["n"] == full_n and r.get("seed", 3407) == 3407), None)
    out.append("")
    for metric, label in (("checks", "All checks"), ("spec", "Spec adherence"), ("final", "Robustness")):
        if not full or not full["cell"] or full["cell"].get(metric) is None:
            out.append("%s: the full-N run has no value for this metric yet." % label)
            continue
        ref = full["cell"][metric]
        means = {}
        for n, group in by_n.items():
            vals = [g["cell"][metric] for g in group if g["cell"] and g["cell"].get(metric) is not None]
            if vals:
                means[n] = sum(vals) / len(vals)
        ok = [n for n, v in means.items() if v >= ref - THRESHOLD]
        out.append("%s: full-N (seed 3407) %s; mean over seeds per size: %s; sizes within %.2f: %s; smallest: %s." % (
            label, pct(ref), ", ".join("%d %s" % (n, pct(means[n])) for n in sorted(means, reverse=True)), THRESHOLD,
            ", ".join(str(n) for n in sorted(ok)) or "none", min(ok) if ok else "none"))
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Data-efficiency curve over nested subsets.")
    p.add_argument("--sizes", type=int, nargs="+", required=True, help="subset sizes, e.g. 228 114 57")
    p.add_argument("--full", default="models/v1", help="model directory of the full-N run")
    p.add_argument("--full-eval", default="results/eval_v1_2026-10-27", help="eval directory of the full-N run")
    p.add_argument("--data", default="data/train.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--models-dir", default="models")
    p.add_argument("--train-seed", type=int, default=3407,
                   help="training seed; a second seed gives a second row per size (dirs get an _s<seed> suffix)")
    p.add_argument("--sizes-with-full", action="store_true",
                   help="also train the full set with --train-seed (for a second seed of the full-N run)")
    p.add_argument("--judge", default=None, metavar="PROVIDER:MODEL",
                   help="run the LLM judge on each new eval (passed to eval.py); needs the provider's key")
    args = p.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    full_m = manifest(args.full)
    full_n = full_m.get("data", {}).get("rows_used") or sum(1 for _ in open(args.data, encoding="utf-8"))
    suffix = "" if args.train_seed == 3407 else "_s%d" % args.train_seed
    sizes = sorted(args.sizes, reverse=True)
    if args.sizes_with_full and suffix:
        sizes = [full_n] + [n for n in sizes if n != full_n]
    new_rows = []
    for n in sizes:
        model_dir = os.path.join(args.models_dir, "curve_%d%s" % (n, suffix))
        eval_dir = os.path.join(args.out, "eval_%d%s" % (n, suffix))
        if not os.path.exists(os.path.join(model_dir, "adapter", "adapter_config.json")):
            cmd = [PYTHON, "train.py", "--data", args.data, "--out", model_dir, "--seed", str(args.train_seed)]
            if n != full_n:
                cmd += ["--n", str(n)]
            run(cmd, os.path.join(args.out, "train_%d%s.log" % (n, suffix)))
        if not os.path.exists(os.path.join(eval_dir, "transcripts.jsonl")):
            cmd = [PYTHON, "eval.py", "--model", os.path.join(model_dir, "adapter"), "--eval-set", "challenge", "--out", eval_dir]
            if args.judge:
                cmd += ["--judge", args.judge]
            run(cmd, os.path.join(args.out, "eval_%d%s.log" % (n, suffix)))
        m = manifest(model_dir)
        new_rows.append({"n": n, "seed": args.train_seed, "model": model_dir, "eval": eval_dir, "steps": m.get("train", {}).get("steps"), "loss": m.get("train", {}).get("train_loss")})

    # Every row this directory knows about: the full-N run, earlier seeds
    # from curve.json, and this run's rows.
    rows = [{"n": full_n, "seed": full_m.get("config", {}).get("seed", 3407), "model": args.full, "eval": args.full_eval, "steps": full_m.get("train", {}).get("steps"), "loss": full_m.get("train", {}).get("train_loss")}]
    json_path = os.path.join(args.out, "curve.json")
    if os.path.exists(json_path):
        for r in json.load(open(json_path, encoding="utf-8"))["rows"]:
            if not any(r["n"] == x["n"] and r.get("seed", 3407) == x.get("seed", 3407) for x in rows):
                rows.append({k: r[k] for k in ("n", "seed", "model", "eval", "steps", "loss") if k in r})
    for r in new_rows:
        rows = [x for x in rows if not (x["n"] == r["n"] and x.get("seed", 3407) == r["seed"])] + [r]
    rows.sort(key=lambda r: (-r["n"], r.get("seed", 3407)))
    for r in rows:
        r.setdefault("seed", 3407)
        # The full-N eval directory may also hold the baseline's records
        # (eval.py --baseline); keep the adapter's only.
        r["cell"] = cell(r["eval"], os.path.join(r["model"], "adapter"))
    text = render(rows, full_n)
    with open(os.path.join(args.out, "curve.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"threshold": THRESHOLD, "rows": rows}, fh, indent=2)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
