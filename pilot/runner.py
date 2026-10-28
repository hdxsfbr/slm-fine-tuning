"""Runs every (model, behavior, strategy, scenario, repeat) combination
concurrently, records one JSON line per conversation, and writes results.md.

A conversation that raises is recorded with an "error" field and a null
score; the run keeps going. Ctrl-C writes the report for whatever finished.
resume_pilot() reruns only the errored conversations of a finished run and
rewrites its files in place.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from behaviors import BEHAVIORS

from . import report
from .clients import make_client

TRANSCRIPTS = "transcripts.jsonl"
RESULTS = "results.md"
RUN_META = "run.json"


@dataclass
class RunConfig:
    models: List[str]
    behaviors: List[str] = field(default_factory=lambda: list(BEHAVIORS))
    strategies: Optional[List[str]] = None
    limit: Optional[int] = None
    repeats: int = 1
    workers: int = 4
    out_dir: Optional[str] = None
    temperature: Optional[float] = None
    timeout: float = 180.0
    scenarios: Optional[List[str]] = None  # scenario ids to run; None means all (then --limit applies)


def default_out_dir() -> str:
    return os.path.join("results", dt.datetime.now().strftime("%Y%m%d_%H%M%S"))


def _git_sha() -> Optional[str]:
    """HEAD sha, with "-dirty" appended when the tree has uncommitted changes,
    so a results file never claims to pin code it did not run."""
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        return sha + ("-dirty" if status else "")
    except Exception:
        return None


def _validate(cfg: RunConfig) -> None:
    for name in cfg.behaviors:
        if name not in BEHAVIORS:
            raise ValueError("unknown behavior %r (available: %s)" % (name, ", ".join(BEHAVIORS)))
    if cfg.strategies:
        for name in cfg.behaviors:
            known = BEHAVIORS[name].STRATEGIES
            for s in cfg.strategies:
                if s not in known:
                    raise ValueError("behavior %r has no strategy %r (available: %s)" % (name, s, ", ".join(known)))
    if cfg.repeats < 1 or cfg.workers < 1:
        raise ValueError("--repeats and --workers must be at least 1")
    if cfg.scenarios:
        known = {s["id"] for name in cfg.behaviors for s in BEHAVIORS[name].SCENARIOS}
        unknown = [sid for sid in cfg.scenarios if sid not in known]
        if unknown:
            raise ValueError("unknown scenario ids: %s" % ", ".join(unknown))


def select_scenarios(module, cfg: RunConfig) -> List[Dict]:
    """The scenarios of one behavior that a config selects: the listed ids
    (in the module's order), else the first --limit, else all."""
    if cfg.scenarios:
        wanted = set(cfg.scenarios)
        return [s for s in module.SCENARIOS if s["id"] in wanted]
    return module.SCENARIOS[: cfg.limit] if cfg.limit else module.SCENARIOS


def build_jobs(cfg: RunConfig) -> List[Dict]:
    jobs = []
    for model in cfg.models:
        for name in cfg.behaviors:
            module = BEHAVIORS[name]
            strategies = cfg.strategies or list(module.STRATEGIES)
            scenarios = select_scenarios(module, cfg)
            for strategy in strategies:
                for scenario in scenarios:
                    for repeat in range(cfg.repeats):
                        jobs.append(
                            {
                                "index": len(jobs),
                                "model": model,
                                "behavior": name,
                                "strategy": strategy,
                                "scenario": scenario,
                                "repeat": repeat,
                            }
                        )
    return jobs


def _job_key(job: Dict) -> Tuple:
    return (job["model"], job["behavior"], job["strategy"], job["scenario"]["id"], job["repeat"])


def _record_key(record: Dict) -> Tuple:
    return (record["model"], record["behavior"], record["strategy"], record["scenario_id"], record["repeat"])


def load_run(out_dir: str) -> Tuple[RunConfig, Dict[Tuple, Dict]]:
    """The config of a previous run and its error-free records, keyed per
    conversation, so a resume reruns only what failed."""
    with open(os.path.join(out_dir, RUN_META), encoding="utf-8") as fh:
        saved = json.load(fh)["config"]
    cfg = RunConfig(**saved)
    cfg.out_dir = out_dir
    kept: Dict[Tuple, Dict] = {}
    path = os.path.join(out_dir, TRANSCRIPTS)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                record = json.loads(line)
                if not record["error"]:
                    kept[_record_key(record)] = record
    return cfg, kept


def run_job(job: Dict, client) -> Dict:
    module = BEHAVIORS[job["behavior"]]
    scenario = job["scenario"]
    record = {
        "behavior": job["behavior"],
        "model": job["model"],
        "strategy": job["strategy"],
        "scenario_id": scenario["id"],
        "group": scenario.get(module.GROUP_FIELD),
        "repeat": job["repeat"],
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "system": None,
        "messages": [],
        "score": None,
        "error": None,
        "meta": {},
        "elapsed_s": 0.0,
    }
    t0 = time.time()
    try:
        result = module.run(client, job["strategy"], scenario)
        record.update({k: result[k] for k in ("system", "messages", "score")})
        record["meta"] = result.get("meta", {})
    except Exception as e:  # recorded, the run keeps going
        record["error"] = "%s: %s" % (type(e).__name__, e)
    record["elapsed_s"] = round(time.time() - t0, 2)
    return record


def _status(record: Dict) -> str:
    if record["error"]:
        return "ERROR"
    score = record["score"]
    if score.get("valid") is False:
        return "INVALID"
    return "PASS" if score.get("passed") else "FAIL"


def resume_pilot(
    out_dir: str,
    workers: Optional[int] = None,
    timeout: Optional[float] = None,
    log: Callable[[str], None] = lambda s: print(s, file=sys.stderr),
) -> Dict:
    """Rerun the errored conversations of the run in out_dir and rewrite its
    transcripts, run.json and results.md. Everything else comes from the
    saved config; workers and timeout can be changed."""
    cfg, kept = load_run(out_dir)
    if workers is not None:
        cfg.workers = workers
    if timeout is not None:
        cfg.timeout = timeout
    return run_pilot(cfg, log, kept=kept)


def run_pilot(
    cfg: RunConfig,
    log: Callable[[str], None] = lambda s: print(s, file=sys.stderr),
    kept: Optional[Dict[Tuple, Dict]] = None,
) -> Dict:
    _validate(cfg)
    out_dir = cfg.out_dir or default_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    # Fail fast on missing API keys before any job starts.
    clients = {spec: make_client(spec, cfg.temperature, cfg.timeout) for spec in cfg.models}
    jobs = build_jobs(cfg)
    kept = kept or {}
    records: List[Optional[Dict]] = [kept.get(_job_key(job)) for job in jobs]
    todo = [job for job in jobs if _job_key(job) not in kept]
    started = dt.datetime.now(dt.timezone.utc)
    log("%d conversations -> %s%s" % (len(todo), out_dir, " (%d kept from the previous run)" % len(kept) if kept else ""))

    lock = threading.Lock()
    done = 0
    interrupted = False
    transcripts_path = os.path.join(out_dir, TRANSCRIPTS)
    with open(transcripts_path, "w", encoding="utf-8") as fh:
        for record in records:
            if record is not None:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        executor = ThreadPoolExecutor(max_workers=cfg.workers)
        futures = {executor.submit(run_job, job, clients[job["model"]]): job for job in todo}
        try:
            for fut in as_completed(futures):
                job = futures[fut]
                record = fut.result()
                with lock:
                    records[job["index"]] = record
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fh.flush()
                    done += 1
                log(
                    "[%d/%d] %-10s %-28s %-11s %-22s %-7s %5.1fs"
                    % (
                        done,
                        len(todo),
                        record["behavior"],
                        record["model"][:28],
                        record["strategy"],
                        record["scenario_id"][:22],
                        _status(record),
                        record["elapsed_s"],
                    )
                )
        except KeyboardInterrupt:
            interrupted = True
            log("interrupted; writing results for the %d finished conversations" % done)
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=True)

    finished_records = [r for r in records if r is not None]
    finished = dt.datetime.now(dt.timezone.utc)
    meta = {
        "config": asdict(cfg),
        "out_dir": out_dir,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "interrupted": interrupted,
        "jobs": len(jobs),
        "kept_from_previous_run": len(kept),
        "completed": len(finished_records),
        "errors": sum(1 for r in finished_records if r["error"]),
        "git_sha": _git_sha(),
        "python": platform.python_version(),
    }
    with open(os.path.join(out_dir, RUN_META), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    results_path = os.path.join(out_dir, RESULTS)
    with open(results_path, "w", encoding="utf-8") as fh:
        fh.write(report.render(finished_records, meta))
    return {
        "records": finished_records,
        "meta": meta,
        "out_dir": out_dir,
        "transcripts": transcripts_path,
        "results": results_path,
    }
