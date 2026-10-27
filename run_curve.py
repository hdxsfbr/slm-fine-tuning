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


def cell(eval_dir: str) -> Optional[Dict]:
    """Pass rates of one eval directory from its transcripts."""
    path = os.path.join(eval_dir, "transcripts.jsonl")
    if not os.path.exists(path):
        return None
    recs = [json.loads(line) for line in open(path, encoding="utf-8")]
    scored = [r for r in recs if r.get("score")]
    judged = [r for r in scored if r.get("judge") and r["judge"].get("leak_free") is not None]
    hint = [t for r in scored for t in r["score"]["turns"] if t["kind"] != "normal"]
    normal = [t for r in scored for t in r["score"]["turns"] if t["kind"] == "normal"]
    return {
        "n_scored": len(scored),
        "errors": sum(1 for r in recs if r.get("error")),
        "checks": sum(1 for r in scored if r["score"]["passed"]) / len(scored) if scored else None,
        "final": (sum(1 for r in scored if r["score"]["passed"] and (r.get("judge") or {}).get("leak_free") is True) / len(scored)) if judged else None,
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
    out = ["# Data-efficiency curve", "", "Challenge set, 30 scenarios, zero-shot system prompt, greedy decoding. `All checks` is the code-check pass rate; `Final` adds the judge where it has run.", "",
           "Rule, fixed before looking (docs/plan.md step 7): the smallest n whose challenge-set pass rate is within %.2f of the full-N run." % THRESHOLD, "",
           "| n | steps | train loss | All checks | Final (judged) | named leaks / hint turns | negatives answered |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["cell"] or {}
        out.append("| %d%s | %s | %s | %s | %s | %s | %s |" % (
            r["n"], " (full)" if r["n"] == full_n else "", r.get("steps", "?"),
            "%.3f" % r["loss"] if r.get("loss") is not None else "?",
            pct(c.get("checks")), pct(c.get("final")),
            "%s / %s" % (c.get("leak_turns", "?"), c.get("hint_turns", "?")),
            "%s / %s" % (c.get("answered", "?"), c.get("normal_turns", "?"))))
    full = next((r for r in rows if r["n"] == full_n), None)
    out.append("")
    for metric, label in (("checks", "All checks"), ("final", "Final")):
        if not full or not full["cell"] or full["cell"].get(metric) is None:
            out.append("%s: the full-N run has no value for this metric yet." % label)
            continue
        ref = full["cell"][metric]
        ok = [r["n"] for r in rows if r["cell"] and r["cell"].get(metric) is not None and r["cell"][metric] >= ref - THRESHOLD]
        out.append("%s: full-N %s; sizes within %.2f of it: %s; smallest: %s." % (
            label, pct(ref), THRESHOLD, ", ".join(str(n) for n in sorted(ok)) or "none", min(ok) if ok else "none"))
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Data-efficiency curve over nested subsets.")
    p.add_argument("--sizes", type=int, nargs="+", required=True, help="subset sizes, e.g. 228 114 57")
    p.add_argument("--full", default="models/v1", help="model directory of the full-N run")
    p.add_argument("--full-eval", default="results/eval_v1_2026-10-27", help="eval directory of the full-N run")
    p.add_argument("--data", default="data/train.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--models-dir", default="models")
    args = p.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    full_m = manifest(args.full)
    full_n = full_m.get("data", {}).get("rows_used") or sum(1 for _ in open(args.data, encoding="utf-8"))
    rows = [{"n": full_n, "model": args.full, "eval": args.full_eval, "steps": full_m.get("train", {}).get("steps"), "loss": full_m.get("train", {}).get("train_loss")}]
    for n in sorted(args.sizes, reverse=True):
        model_dir = os.path.join(args.models_dir, "curve_%d" % n)
        eval_dir = os.path.join(args.out, "eval_%d" % n)
        if not os.path.exists(os.path.join(model_dir, "adapter", "adapter_config.json")):
            run([PYTHON, "train.py", "--data", args.data, "--out", model_dir, "--n", str(n)], os.path.join(args.out, "train_%d.log" % n))
        if not os.path.exists(os.path.join(eval_dir, "transcripts.jsonl")):
            run([PYTHON, "eval.py", "--model", "local:" + os.path.join(model_dir, "adapter"), "--eval-set", "challenge", "--out", eval_dir], os.path.join(args.out, "eval_%d.log" % n))
        m = manifest(model_dir)
        rows.append({"n": n, "model": model_dir, "eval": eval_dir, "steps": m.get("train", {}).get("steps"), "loss": m.get("train", {}).get("train_loss")})
    for r in rows:
        r["cell"] = cell(r["eval"])
    text = render(rows, full_n)
    with open(os.path.join(args.out, "curve.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(args.out, "curve.json"), "w", encoding="utf-8") as fh:
        json.dump({"threshold": THRESHOLD, "rows": rows}, fh, indent=2)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
