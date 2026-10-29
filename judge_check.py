#!/usr/bin/env python3
"""Second-family judge check: judge a finished run again with another judge
model and compare the two judges item by item.

The first judge's files are never touched. The run directory is copied
(transcripts.jsonl, run.json, judge.jsonl and eval_set.jsonl when present)
and the second judge appends its verdicts to the copy's judge.jsonl, so both
judges' raw replies sit in one file keyed by item. The copy's results.md is
then the same table under the second judge. judge_check.md and
judge_check.json in the copy hold the comparison: agreement and Cohen's
kappa over the items both judges read, the confusion matrix with leak as
the positive class, the split by pressure kind, Spec adherence and
Robustness per model and strategy under each judge, every disagreement with
both judges' reasoning, and, with --labels, each judge's agreement with the
hand labels.

    python judge_check.py results/eval_v2_2026-10-28 \
        --judge openrouter:google/gemini-3.1-flash-lite \
        --out results/judge_check_2026-10-29/eval_v2 \
        [--cell MODEL STRATEGY ...] [--labels results/<dir>/labels.jsonl] \
        [--workers 4] [--limit N] [--no-reasoning]

--cell keeps only the named model and strategy pairs (repeatable), so an
ablation run can be judged again on its best cells only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from typing import Dict, List, Optional, Tuple

from behaviors import BEHAVIORS
from pilot.judge import JUDGE_FILE, NO_REASONING, agreement, current_judge, judge_run, load_judgments, load_records, merge_verdicts, render_agreement
from pilot.runner import RUN_META, TRANSCRIPTS

EVAL_SET = "eval_set.jsonl"
CHECK_MD = "judge_check.md"
CHECK_JSON = "judge_check.json"

Cell = Tuple[str, str]


def copy_run(src: str, out: str, cells: Optional[List[Cell]] = None) -> int:
    """Copy the run's files into out, keeping only the records and verdicts
    of the given (model, strategy) cells when cells is given. Returns the
    number of records copied."""
    os.makedirs(out, exist_ok=True)
    wanted = set(cells) if cells else None

    def keep(row: Dict) -> bool:
        return wanted is None or (row["model"], row["strategy"]) in wanted

    n = 0
    with open(os.path.join(src, TRANSCRIPTS), encoding="utf-8") as fh, open(os.path.join(out, TRANSCRIPTS), "w", encoding="utf-8") as oh:
        for line in fh:
            if keep(json.loads(line)):
                oh.write(line.rstrip("\n") + "\n")
                n += 1
    src_judge = os.path.join(src, JUDGE_FILE)
    if os.path.exists(src_judge):
        with open(src_judge, encoding="utf-8") as fh, open(os.path.join(out, JUDGE_FILE), "w", encoding="utf-8") as oh:
            for line in fh:
                if keep(json.loads(line)):
                    oh.write(line.rstrip("\n") + "\n")
    with open(os.path.join(src, RUN_META), encoding="utf-8") as fh:
        meta = json.load(fh)
    if wanted:
        config = meta.get("config", {})
        models = [m for m in config.get("models", []) if any(m == c[0] for c in wanted)]
        strategies = [s for s in config.get("strategies", []) if any(s == c[1] for c in wanted)]
        if models:
            config["models"] = models
        if strategies:
            config["strategies"] = strategies
    meta["judge_check"] = {
        "source": src,
        "cells": [list(c) for c in cells] if cells else None,
        "first_judge": (meta.get("judge") or {}).get("model"),
    }
    with open(os.path.join(out, RUN_META), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    eval_set = os.path.join(src, EVAL_SET)
    if os.path.exists(eval_set):
        shutil.copy(eval_set, os.path.join(out, EVAL_SET))
    return n


def kappa(tp: int, fp: int, fn: int, tn: int) -> Optional[float]:
    """Cohen's kappa for two binary raters from their confusion counts."""
    n = tp + fp + fn + tn
    if n == 0:
        return None
    po = (tp + tn) / n
    pe = ((tp + fn) * (tp + fp) + (fp + tn) * (fn + tn)) / (n * n)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def compare(out: str, judge_a: str, judge_b: str) -> Dict:
    """Both judges' error-free verdicts on the copy, item by item, with A as
    the reference, plus the per-cell aggregates under each judge."""
    a = load_judgments(out, judge_a)
    b = load_judgments(out, judge_b)
    common = sorted(set(a) & set(b))
    tp = fp = fn = tn = 0
    by_kind: Dict[str, Dict] = {}
    disagreements = []
    for key in common:
        la, lb = bool(a[key]["leak"]), bool(b[key]["leak"])
        kind = a[key].get("kind") or "?"
        d = by_kind.setdefault(kind, {"n": 0, "agree": 0, "a_leak": 0, "b_leak": 0})
        d["n"] += 1
        d["agree"] += int(la == lb)
        d["a_leak"] += int(la)
        d["b_leak"] += int(lb)
        if la and lb:
            tp += 1
        elif la:
            fn += 1
        elif lb:
            fp += 1
        else:
            tn += 1
        if la != lb:
            disagreements.append(
                {
                    "key": key,
                    "kind": kind,
                    "a_leak": la,
                    "b_leak": lb,
                    "a_reasoning": a[key].get("reasoning", ""),
                    "b_reasoning": b[key].get("reasoning", ""),
                }
            )
    records = load_records(out)
    cells: Dict[str, Dict[str, Dict]] = {}
    for spec, judgments in ((judge_a, a), (judge_b, b)):
        merge_verdicts(records, judgments, spec)
        groups: Dict[Cell, List[Dict]] = {}
        for r in records:
            groups.setdefault((r["model"], r["strategy"]), []).append(r)
        for (model, strategy), recs in sorted(groups.items()):
            agg = BEHAVIORS[recs[0]["behavior"]].aggregate(recs)
            cells.setdefault("%s / %s" % (model, strategy), {})[spec] = {
                "n": agg["n"],
                "spec_adherence": list(agg["spec_adherence"]),
                "final": list(agg["final"]),
                "judge_leak_free": list(agg["judge_leak_free"]),
            }
    n = len(common)
    return {
        "judge_a": judge_a,
        "judge_b": judge_b,
        "items_a": len(a),
        "items_b": len(b),
        "items_common": n,
        "agree": tp + tn,
        "agreement": (tp + tn) / n if n else None,
        "kappa": kappa(tp, fp, fn, tn),
        "confusion": {"both_leak": tp, "a_only": fn, "b_only": fp, "neither": tn},
        "by_kind": by_kind,
        "cells": cells,
        "disagreements": disagreements,
    }


def _pct(pair) -> str:
    passed, total = pair
    return "%d%% (%d/%d)" % (round(100.0 * passed / total), passed, total) if total else "n/a"


def render(result: Dict) -> str:
    a, b = result["judge_a"], result["judge_b"]
    c = result["confusion"]
    lines = ["# Second-family judge check", ""]
    lines.append("- Judge A, the reference: %s" % a)
    lines.append("- Judge B: %s" % b)
    lines.append("- Items with an error-free verdict: A %d, B %d, both %d" % (result["items_a"], result["items_b"], result["items_common"]))
    if result["items_common"]:
        lines.append(
            "- Agreement: %d%% (%d of %d); Cohen's kappa %s"
            % (round(100 * result["agreement"]), result["agree"], result["items_common"], "n/a" if result["kappa"] is None else "%.2f" % result["kappa"])
        )
    lines += ["", "| | B leak | B no leak |", "|---|---|---|"]
    lines.append("| A leak | %d | %d |" % (c["both_leak"], c["a_only"]))
    lines.append("| A no leak | %d | %d |" % (c["b_only"], c["neither"]))
    lines += ["", "## By pressure kind", "", "| kind | items | agree | A leaks | B leaks |", "|---|---|---|---|---|"]
    for kind, d in sorted(result["by_kind"].items()):
        lines.append("| %s | %d | %d%% | %d | %d |" % (kind, d["n"], round(100.0 * d["agree"] / d["n"]), d["a_leak"], d["b_leak"]))
    lines += ["", "## Per model and strategy", "", "| cell | judge | Spec adherence (turns) | Robustness (Final) | leak-free conversations (judge) |", "|---|---|---|---|---|"]
    for cell, per in result["cells"].items():
        for spec in (a, b):
            agg = per.get(spec)
            if agg:
                lines.append("| %s | %s | %s | %s | %s |" % (cell, spec, _pct(agg["spec_adherence"]), _pct(agg["final"]), _pct(agg["judge_leak_free"])))
    labels = result.get("labels")
    if labels:
        lines += ["", "## Against the hand labels (%s)" % labels["path"]]
        for spec in (a, b):
            if spec in labels:
                lines += ["", "### %s" % spec, "", render_agreement(labels[spec]).rstrip()]
    lines += ["", "## Disagreements (%d)" % len(result["disagreements"]), ""]
    for d in result["disagreements"]:
        lines.append("- `%s` (%s): A %s, B %s" % (d["key"], d["kind"], "leak" if d["a_leak"] else "no leak", "leak" if d["b_leak"] else "no leak"))
        lines.append("  - A: %s" % d["a_reasoning"].replace("\n", " ").strip())
        lines.append("  - B: %s" % d["b_reasoning"].replace("\n", " ").strip())
    return "\n".join(lines) + "\n"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Judge a finished run again with a second judge model, on a copy, and compare the judges.")
    p.add_argument("src", help="finished, judged run directory")
    p.add_argument("--judge", required=True, metavar="PROVIDER:MODEL", help="the second judge")
    p.add_argument("--out", required=True, help="directory for the copy and the comparison")
    p.add_argument("--cell", nargs=2, action="append", metavar=("MODEL", "STRATEGY"), help="keep only this model and strategy (repeatable)")
    p.add_argument("--labels", default=None, help="hand labels file; both judges are scored against it")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--limit", type=int, default=None, help="judge only the first N items")
    p.add_argument("--no-reasoning", action="store_true", help="send OpenRouter's reasoning.enabled=false to the second judge")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from eval import register_from_dir  # eval.py runs carry their scenarios in eval_set.jsonl

    first = current_judge(args.src)
    if not first:
        sys.exit("%s has no judge recorded in run.json" % args.src)
    if first == args.judge:
        sys.exit("the second judge must differ from the first (%s)" % first)
    cells = [tuple(c) for c in args.cell] if args.cell else None
    n = copy_run(args.src, args.out, cells)
    if n == 0:
        sys.exit("no records of %s match the cells" % args.src)
    print("copied %d records from %s to %s" % (n, args.src, args.out))
    register_from_dir(args.out)
    res = judge_run(
        args.out, args.judge, workers=args.workers, timeout=args.timeout, limit=args.limit,
        extra_body=NO_REASONING if args.no_reasoning else None,
    )
    result = compare(args.out, first, args.judge)
    if args.labels:
        result["labels"] = {"path": args.labels, first: agreement(args.out, args.labels, first), args.judge: agreement(args.out, args.labels, args.judge)}
    with open(os.path.join(args.out, CHECK_JSON), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    text = render(result)
    with open(os.path.join(args.out, CHECK_MD), "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print("judged %d items now with %s, %d errors; comparison in %s" % (res["judged_now"], args.judge, res["errors"], os.path.join(args.out, CHECK_MD)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
