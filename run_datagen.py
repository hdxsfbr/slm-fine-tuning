#!/usr/bin/env python3
"""Training data for the hint-only chess coach.

Verified positions, disjoint from the eval set:

    python run_datagen.py positions --n 400 --seed 0 --out data/positions.jsonl

Teacher rows (resumable; reruns skip finished ids):

    python run_datagen.py generate data/positions.jsonl --n 900 --teacher openrouter:anthropic/claude-haiku-5.5 \
        --out data/generated.jsonl [--workers 6] [--no-reasoning]

The gate, with the same judge and rubric as the ablation:

    python run_datagen.py gate data/generated.jsonl --out data \
        --judge openrouter:anthropic/claude-haiku-5.5 [--no-reasoning]

A v3 batch: fresh positions disjoint from the earlier file, plans with
disguise turns that name a pattern (--mix v3), gate, then merge with v2:

    python run_datagen.py positions --n 400 --seed 1 --exclude data/positions.jsonl --out data/positions_v3.jsonl
    python run_datagen.py generate data/positions_v3.jsonl --n 350 --mix v3 --teacher ... --out data/v3_extra/generated.jsonl
    python run_datagen.py gate data/v3_extra/generated.jsonl --out data/v3_extra --judge ...
    python run_datagen.py merge --out data/v3 data/v2 data/v3_extra
"""
from __future__ import annotations

import argparse
import json
import sys

from datagen.gate import run_gate
from datagen.generate import generate, load_rows
from datagen.merge import merge
from datagen.patterns import generate_textbook
from datagen.positions import generate_positions, interleave_families, load_positions, placements_of, verify, write_positions
from pilot.clients import make_client
from pilot.judge import NO_REASONING, TEMPERATURE


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Training data for the hint-only chess coach.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("positions")
    s.add_argument("--n", type=int, default=400)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", required=True)
    s.add_argument("--exclude", nargs="*", default=[], metavar="POSITIONS",
                   help="earlier positions files whose placements are skipped")
    s.add_argument("--textbook", action="store_true",
                   help="named textbook patterns (datagen/patterns.py) instead of random placements")

    g = sub.add_parser("generate")
    g.add_argument("positions")
    g.add_argument("--n", type=int, required=True, help="conversations to generate")
    g.add_argument("--teacher", required=True, metavar="PROVIDER:MODEL")
    g.add_argument("--out", required=True)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--mix", default="v2", choices=("v2", "v3", "v3b"),
                   help="plan sampler: v2 (one disguise turn in half the plans), v3 (two or three named-pattern disguise turns and a pattern hard negative in every plan), v3b (v3 on textbook positions: the first disguise turn is the textbook question by the position's own name)")
    g.add_argument("--workers", type=int, default=6)
    g.add_argument("--timeout", type=float, default=180.0)
    g.add_argument("--temperature", type=float, default=1.0)
    g.add_argument("--no-reasoning", action="store_true",
                   help="ask OpenRouter to disable hidden reasoning (haiku accepts this; sonnet-5.5 refuses)")
    g.add_argument("--reasoning", default=None, metavar="JSON",
                   help='OpenRouter reasoning settings for models that cannot switch it off, e.g. \'{"effort": "low"}\' or \'{"max_tokens": 300}\'')

    t = sub.add_parser("gate")
    t.add_argument("generated")
    t.add_argument("--out", required=True, help="directory for train.jsonl, synthetic_test.jsonl, manifest.json")
    t.add_argument("--judge", default=None, metavar="PROVIDER:MODEL", help="omit to skip the judge stage (dry run)")
    t.add_argument("--workers", type=int, default=6)
    t.add_argument("--timeout", type=float, default=180.0)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--holdout", type=float, default=0.10)
    t.add_argument("--no-reasoning", action="store_true")
    t.add_argument("--allow-square-free-answers", action="store_true",
                   help="do not require squares or moves in normal-turn answers (how the v1 data was gated)")

    m = sub.add_parser("merge", help="merge gated data directories into one dataset version")
    m.add_argument("sources", nargs="+", help="gated data directories, e.g. data/v2 data/v3_extra")
    m.add_argument("--out", required=True)
    m.add_argument("--seed", type=int, default=0, help="shuffle seed")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.command == "positions":
        exclude = set()
        for path in args.exclude:
            exclude |= placements_of(path)
        if args.textbook:
            positions = generate_textbook(args.n, args.seed, exclude=exclude)
        else:
            positions = generate_positions(args.n, args.seed, exclude=exclude)
        assert all(verify(p) for p in positions)
        write_positions(positions, args.out)
        families = {}
        for p in positions:
            families[p["family"]] = families.get(p["family"], 0) + 1
        print("wrote %d verified positions to %s: %s" % (len(positions), args.out, ", ".join("%s %d" % kv for kv in families.items())))
        return 0
    if args.command == "generate":
        # Families are interleaved so a short run (a sample) and every
        # prefix of a long one cover the mate patterns evenly.
        positions = interleave_families(load_positions(args.positions))
        extra_body = None
        if args.no_reasoning and args.reasoning:
            sys.exit("--no-reasoning and --reasoning exclude each other")
        if args.no_reasoning:
            extra_body = NO_REASONING
        elif args.reasoning:
            extra_body = {"reasoning": json.loads(args.reasoning)}
        result = generate(
            positions, args.n, args.teacher, args.out, seed=args.seed, workers=args.workers, timeout=args.timeout,
            temperature=args.temperature, extra_body=extra_body, mix=args.mix,
        )
        print("generated %d rows now (%d errors), tokens in %d out %d -> %s" % (
            result["generated"], result["errors"], result["usage"]["input_tokens"], result["usage"]["output_tokens"], args.out))
        return 1 if result["errors"] else 0
    if args.command == "gate":
        rows = []
        with open(args.generated, encoding="utf-8") as fh:
            for line in fh:
                rows.append(json.loads(line))
        judge_client = None
        if args.judge:
            judge_client = make_client(args.judge, TEMPERATURE, args.timeout, NO_REASONING if args.no_reasoning else None)
        report = run_gate(rows, args.out, judge_client, judge_workers=args.workers, seed=args.seed, holdout=args.holdout,
                          require_squares=not args.allow_square_free_answers)
        for name, info in report["output"].items():
            print("%s: %d rows, sha256 %s" % (name, info["rows"], info["sha256"][:16]))
        return 0
    if args.command == "merge":
        manifest = merge(args.sources, args.out, seed=args.seed)
        for name, info in manifest["output"].items():
            print("%s: %d rows, sha256 %s" % (name, info["rows"], info["sha256"][:16]))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
