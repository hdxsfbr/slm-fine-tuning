#!/usr/bin/env python3
"""Rescore a finished run with the current scorers and rewrite its files.

    python rescore.py results/<dir>

Scores are pure functions over the recorded messages, so a scorer fix (a
regex false positive, a changed expect pattern) is applied to the transcripts
without spending credits. transcripts.jsonl gets new score fields in place,
results.md is regenerated, and run.json records when and with which code the
rescore happened. Records with an error are left as they are.
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
from pilot.runner import RESULTS, RUN_META, TRANSCRIPTS, RunConfig, _git_sha, _job_key, _record_key, build_jobs


def rescore_record(record: Dict) -> Dict:
    """Return the record with its score recomputed from its messages."""
    if record.get("error"):
        return record
    module = BEHAVIORS[record["behavior"]]
    scenario = next((s for s in module.SCENARIOS if s["id"] == record["scenario_id"]), None)
    if scenario is None and hasattr(module, "get_scenario"):
        scenario = module.get_scenario(record["scenario_id"])
    if scenario is None:
        raise KeyError("behavior %s has no scenario %r" % (record["behavior"], record["scenario_id"]))
    record["score"] = module.score_messages(scenario, record["messages"])
    record["group"] = scenario.get(module.GROUP_FIELD)
    return record


def rescore_run(out_dir: str) -> Dict:
    from eval import register_from_dir  # loaded eval sets (eval.py runs) carry their scenarios

    register_from_dir(out_dir)
    with open(os.path.join(out_dir, RUN_META), encoding="utf-8") as fh:
        meta = json.load(fh)
    path = os.path.join(out_dir, TRANSCRIPTS)
    with open(path, encoding="utf-8") as fh:
        records: List[Dict] = [rescore_record(json.loads(line)) for line in fh]
    # The run wrote records in completion order; put them back in job order
    # so the report's model and strategy order matches the original run.
    order = {_job_key(job): i for i, job in enumerate(build_jobs(RunConfig(**meta["config"])))}
    records.sort(key=lambda r: order.get(_record_key(r), len(order)))
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    meta["rescored_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta["rescored_git_sha"] = _git_sha()
    with open(os.path.join(out_dir, RUN_META), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    with open(os.path.join(out_dir, RESULTS), "w", encoding="utf-8") as fh:
        fh.write(report.render(records, meta))
    return {"records": records, "meta": meta, "out_dir": out_dir}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Rescore a finished pilot run in place.")
    p.add_argument("out_dir", help="run directory holding transcripts.jsonl and run.json")
    args = p.parse_args(argv)
    result = rescore_run(args.out_dir)
    print(report.headline_summary(result["records"]))
    print("\nrewrote %s and %s" % (os.path.join(args.out_dir, TRANSCRIPTS), os.path.join(args.out_dir, RESULTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
