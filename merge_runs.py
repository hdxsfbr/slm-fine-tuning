#!/usr/bin/env python3
"""Merge finished runs into one directory with a combined report.

    python merge_runs.py results/<a> results/<b> --out results/<merged>

For an ablation run in parts (the pilot's scenarios, then the rest), this
concatenates transcripts.jsonl and judge.jsonl, puts the records in job
order, writes a run.json whose config covers every model, strategy and
scenario of the parts, and renders results.md. A conversation present in two
parts is taken from the later one. The merged directory works with
rescore.py and run_judge.py like any other run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Dict, List

from behaviors import BEHAVIORS
from pilot import report
from pilot.judge import JUDGE_FILE
from pilot.runner import RESULTS, RUN_META, TRANSCRIPTS, RunConfig, _git_sha, _job_key, _record_key, build_jobs


def _read_lines(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _ordered_union(lists: List[List[str]]) -> List[str]:
    out: List[str] = []
    for items in lists:
        for x in items or []:
            if x not in out:
                out.append(x)
    return out


def merge_runs(part_dirs: List[str], out_dir: str) -> Dict:
    metas = []
    by_key: Dict[tuple, Dict] = {}
    judge_rows: List[Dict] = []
    for d in part_dirs:
        with open(os.path.join(d, RUN_META), encoding="utf-8") as fh:
            metas.append(json.load(fh))
        for record in _read_lines(os.path.join(d, TRANSCRIPTS)):
            by_key[_record_key(record)] = record
        judge_rows += _read_lines(os.path.join(d, JUDGE_FILE))

    configs = [m["config"] for m in metas]
    strategies = _ordered_union([c.get("strategies") or [] for c in configs])
    cfg = RunConfig(
        models=_ordered_union([c["models"] for c in configs]),
        behaviors=_ordered_union([c["behaviors"] for c in configs]),
        strategies=strategies or None,
        limit=None,
        repeats=max(c.get("repeats", 1) for c in configs),
        workers=max(c.get("workers", 1) for c in configs),
        out_dir=out_dir,
        temperature=configs[0].get("temperature"),
        timeout=max(c.get("timeout", 180.0) for c in configs),
        scenarios=_ordered_union([c.get("scenarios") or [] for c in configs]) or None,
    )
    # Scenario ids that came in through --limit rather than --scenarios are
    # recovered from the records themselves, so the merged config names
    # exactly the scenarios the parts ran, in module order.
    ran = {r["scenario_id"] for r in by_key.values()}
    cfg.scenarios = [s["id"] for name in cfg.behaviors for s in BEHAVIORS[name].SCENARIOS if s["id"] in ran]
    order = {_job_key(job): i for i, job in enumerate(build_jobs(cfg))}
    records = sorted(by_key.values(), key=lambda r: order.get(_record_key(r), len(order)))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, TRANSCRIPTS), "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, JUDGE_FILE), "w", encoding="utf-8") as fh:
        for row in judge_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    judges = [m.get("judge") for m in metas if m.get("judge")]
    judged = [r for r in records if r.get("judge")]
    meta = {
        "config": cfg.__dict__,
        "out_dir": out_dir,
        "merged_from": part_dirs,
        "merged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "started_at": min(m["started_at"] for m in metas),
        "finished_at": max(m["finished_at"] for m in metas),
        "interrupted": any(m.get("interrupted") for m in metas),
        "jobs": len(records),
        "kept_from_previous_run": 0,
        "completed": len(records),
        "errors": sum(1 for r in records if r.get("error")),
        "git_sha": _git_sha(),
        "python": metas[0].get("python"),
    }
    if judges:
        meta["judge"] = {
            "model": ", ".join(_ordered_union([[j["model"]] for j in judges])),
            "rubrics": _ordered_union([j.get("rubrics", []) for j in judges]),
            "judged_at": max(j["judged_at"] for j in judges),
            "items": sum(j.get("items", 0) for j in judges),
            "judged_items": sum(j.get("judged_items", 0) for j in judges),
            "records_judged": len(judged),
            "errors_this_run": sum(j.get("errors_this_run", 0) for j in judges),
            "git_sha": _git_sha(),
        }
    with open(os.path.join(out_dir, RUN_META), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    with open(os.path.join(out_dir, RESULTS), "w", encoding="utf-8") as fh:
        fh.write(report.render(records, meta))
    return {"records": records, "meta": meta, "out_dir": out_dir}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Merge finished runs into one directory with a combined report.")
    p.add_argument("parts", nargs="+", help="run directories, earliest first")
    p.add_argument("--out", required=True, help="directory to write")
    args = p.parse_args(argv)
    result = merge_runs(args.parts, args.out)
    print(report.headline_summary(result["records"]))
    print("\n%d conversations -> %s" % (len(result["records"]), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
