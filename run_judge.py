#!/usr/bin/env python3
"""LLM judge over a finished pilot run.

Draw a seeded sample to hand-label BEFORE judging:

    python run_judge.py sample results/<dir> --n 30 --seed 0 --out results/<dir>/labels.jsonl

Judge every hint turn of the run (reruns only items without a verdict):

    python run_judge.py run results/<dir> --judge openrouter:anthropic/claude-opus-5.5 [--workers 4] [--limit N]

Compare the hand labels with the verdicts and list every disagreement:

    python run_judge.py calibrate results/<dir> --labels results/<dir>/labels.jsonl

Write the verdicts as one self-contained line per judged turn (user turn,
reply, verdict, reasoning, model, scenario, judge), the file a grader reads:

    python run_judge.py export results/<dir> --out results/<dir>/judged_turns.jsonl
"""
from __future__ import annotations

import argparse
import sys

from pilot import report
from pilot.judge import NO_REASONING, agreement, agreement_fresh, export_judgments, judge_run, render_agreement, sample_items, write_labels_template


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM judge over a finished pilot run.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sample", help="write a labels file to fill in by hand")
    s.add_argument("out_dir")
    s.add_argument("--n", type=int, default=30)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", required=True, help="labels file to write (JSONL)")

    r = sub.add_parser("run", help="judge the run's hint turns and rewrite its files")
    r.add_argument("out_dir")
    r.add_argument("--judge", required=True, metavar="PROVIDER:MODEL")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--timeout", type=float, default=180.0)
    r.add_argument("--limit", type=int, default=None, help="judge only the first N unjudged items")
    r.add_argument("--no-reasoning", action="store_true",
                   help="send OpenRouter's reasoning.enabled=false so the judge does not bill hidden reasoning tokens")

    c = sub.add_parser("calibrate", help="agreement between hand labels and the judge")
    c.add_argument("out_dir")
    c.add_argument("--labels", required=True)
    c.add_argument("--judge", default=None, metavar="PROVIDER:MODEL",
                   help="judge model to compare (default: the one recorded in run.json)")
    c.add_argument("--fresh", action="store_true",
                   help="judge the labeled items again now with --judge (and --no-reasoning if given) instead of reading judge.jsonl")
    c.add_argument("--no-reasoning", action="store_true")
    c.add_argument("--tag", default=None,
                   help="name for the fresh verdicts file, <labels>.<tag>.jsonl (default: the reasoning mode)")

    e = sub.add_parser("export", help="one self-contained JSONL line per judged turn")
    e.add_argument("out_dir")
    e.add_argument("--out", required=True)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from eval import register_from_dir  # loaded eval sets (eval.py runs) carry their scenarios

    register_from_dir(args.out_dir)
    if args.command == "sample":
        rows = sample_items(args.out_dir, args.n, args.seed)
        write_labels_template(rows, args.out)
        print("wrote %d items to %s; fill in label (true = identifies the move) and note" % (len(rows), args.out))
        return 0
    if args.command == "run":
        result = judge_run(
            args.out_dir, args.judge, workers=args.workers, timeout=args.timeout, limit=args.limit,
            extra_body=NO_REASONING if args.no_reasoning else None,
        )
        print(report.headline_summary(result["records"]))
        print("\njudged %d items now, %d errors; rewrote %s" % (result["judged_now"], result["errors"], args.out_dir))
        return 1 if result["errors"] else 0
    if args.command == "calibrate":
        if args.fresh:
            if not args.judge:
                print("--fresh needs --judge", file=sys.stderr)
                return 2
            result = agreement_fresh(args.out_dir, args.labels, args.judge, NO_REASONING if args.no_reasoning else None, tag=args.tag)
            print(render_agreement(result))
            print("\nverdicts: " + result["verdicts_path"])
        else:
            print(render_agreement(agreement(args.out_dir, args.labels, args.judge)))
        return 0
    if args.command == "export":
        n = export_judgments(args.out_dir, args.out)
        print("wrote %d judged turns to %s" % (n, args.out))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
