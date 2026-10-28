#!/usr/bin/env python3
"""Prompt-ceiling pilot.

    python run_pilot.py --models anthropic:<model> openai:<model> \
        [--behaviors sycophancy tells] [--strategies zero_shot few_shot structured] \
        [--limit N] [--repeats N] [--workers N] [--temperature T] [--timeout S] [--out DIR]

Offline dry run:

    python run_pilot.py --models mock:a mock:b --out results/mock

Rerun only the conversations that errored in a finished run, in place:

    python run_pilot.py --resume results/<dir> [--workers N]
"""
from __future__ import annotations

import argparse
import sys

from behaviors import BEHAVIORS
from pilot import report
from pilot.runner import RunConfig, resume_pilot, run_pilot


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the prompt-ceiling pilot.")
    p.add_argument("--models", nargs="+", metavar="PROVIDER:MODEL",
                   help="providers: anthropic, openai, gemini, openrouter, mock")
    p.add_argument("--resume", metavar="DIR", default=None,
                   help="rerun the errored conversations of a finished run and rewrite its files; "
                        "config comes from DIR/run.json, only --workers and --timeout apply")
    p.add_argument("--behaviors", nargs="+", default=list(BEHAVIORS), choices=list(BEHAVIORS))
    p.add_argument("--strategies", nargs="+", default=None,
                   help="subset of zero_shot, few_shot, structured (default: all)")
    p.add_argument("--limit", type=int, default=None, help="first N scenarios per behavior")
    p.add_argument("--scenarios", nargs="+", default=None, metavar="ID",
                   help="run only these scenario ids (in module order); overrides --limit")
    p.add_argument("--repeats", type=int, default=1, help="run each scenario N times")
    p.add_argument("--workers", type=int, default=4, help="concurrent conversations")
    p.add_argument("--temperature", type=float, default=None,
                   help="sampling temperature; unset by default because reasoning models reject it")
    p.add_argument("--timeout", type=float, default=180.0, help="per-request timeout in seconds")
    p.add_argument("--out", default=None, help="output directory (default: results/<timestamp>)")
    args = p.parse_args(argv)
    if not args.models and not args.resume:
        p.error("--models is required unless --resume is given")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        if args.resume:
            result = resume_pilot(args.resume, workers=args.workers, timeout=args.timeout)
        else:
            cfg = RunConfig(
                models=args.models,
                behaviors=args.behaviors,
                strategies=args.strategies,
                limit=args.limit,
                scenarios=args.scenarios,
                repeats=args.repeats,
                workers=args.workers,
                out_dir=args.out,
                temperature=args.temperature,
                timeout=args.timeout,
            )
            result = run_pilot(cfg)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print()
    print(report.headline_summary(result["records"]))
    print()
    print("transcripts: %s" % result["transcripts"])
    print("results:     %s" % result["results"])
    return 1 if result["meta"]["interrupted"] else 0


if __name__ == "__main__":
    sys.exit(main())
