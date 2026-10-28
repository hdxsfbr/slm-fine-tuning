"""LLM judge over recorded transcripts.

The judge never talks to the subject model. It reads a finished run's
transcripts.jsonl, asks each behavior module for the items its rubric should
see (judge_items), sends each one to one fixed judge model at temperature 0,
and writes the verdicts back as a "judge" field next to "score" in every
record. Raw judge replies go to judge.jsonl in the run directory, one line
per item, so the judging is reproducible and auditable and a rerun only
repeats the items that errored.

Calibration: sample_items() draws a seeded, kind-stratified sample of items
as a labels file to be filled in by hand BEFORE the judge runs; agreement()
compares the hand labels with the judge's verdicts and lists every
disagreement. The rubric gets fixed, never the labels.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import sys
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

from behaviors import BEHAVIORS

from . import report
from .clients import make_client
from .runner import RESULTS, RUN_META, TRANSCRIPTS, _git_sha

JUDGE_FILE = "judge.jsonl"
# The verdict is two short fields, but claude-opus-5.5 through OpenRouter
# sometimes spends a few hundred hidden reasoning tokens first and returned
# empty replies at 300, so the budget is generous.
MAX_TOKENS = 1024
TEMPERATURE = 0.0
# OpenRouter request field that switches hidden reasoning off. Haiku-5.5
# billed about 540 output tokens per verdict for a 60-token reply.
NO_REASONING = {"reasoning": {"enabled": False}}


def item_key(record: Dict, item: Dict) -> str:
    return "|".join(
        [record["model"], record["behavior"], record["strategy"], record["scenario_id"], str(record["repeat"]), str(item["turn"])]
    )


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)
_LEAK_FALLBACK = re.compile(r'"leak"\s*:\s*(true|false)', re.I)
_REASON_FALLBACK = re.compile(r'"reasoning"\s*:\s*"([^"\n]*)', re.I)  # closing quote optional: cut-off replies


def parse_verdict(text: str) -> Dict:
    """{"leak": bool, "reasoning": str} from a judge reply. Tolerates code
    fences and prose around the JSON; falls back to regexes when the JSON
    does not parse. Raises ValueError when no verdict can be read."""
    m = _JSON_BLOCK.search(text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict) and isinstance(data.get("leak"), bool):
                return {"leak": data["leak"], "reasoning": str(data.get("reasoning", "")).strip()}
        except ValueError:
            pass
    m = _LEAK_FALLBACK.search(text)
    if not m:
        raise ValueError("no verdict in judge reply: %r" % text[:200])
    r = _REASON_FALLBACK.search(text)
    return {"leak": m.group(1).lower() == "true", "reasoning": r.group(1).strip() if r else ""}


def judge_item(client, module, item: Dict, key: str) -> Dict:
    """One judge call. The mock provider answers from a stable hash so the
    pipeline can run offline."""
    if getattr(client, "provider", None) == "mock":
        return {"leak": zlib.crc32(key.encode("utf-8")) % 5 == 0, "reasoning": "mock verdict", "raw": "", "usage": {}}
    system, user = module.judge_prompt(item)
    reply = client.chat(system, [{"role": "user", "content": user}], max_tokens=MAX_TOKENS)
    verdict = parse_verdict(reply.text)
    verdict["raw"] = reply.text
    verdict["usage"] = reply.usage
    return verdict


def load_records(out_dir: str) -> List[Dict]:
    with open(os.path.join(out_dir, TRANSCRIPTS), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def load_judgments(out_dir: str, judge_spec: Optional[str] = None, current_rubric: bool = True) -> Dict[str, Dict]:
    """Error-free verdicts already in judge.jsonl, keyed by item key. A later
    line for the same key replaces an earlier one. With judge_spec, only that
    judge model's verdicts count, so two judges can be compared on the same
    run and a rerun with a different judge starts from zero. With
    current_rubric, verdicts made under an older rubric version are ignored,
    so a rubric change re-judges everything."""
    path = os.path.join(out_dir, JUDGE_FILE)
    done: Dict[str, Dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("error"):
                    continue
                if judge_spec is not None and row.get("judge") != judge_spec:
                    continue
                if current_rubric and row.get("rubric") != getattr(BEHAVIORS[row["behavior"]], "JUDGE_RUBRIC_VERSION", None):
                    continue
                done[row["key"]] = row
    return done


def collect_items(records: List[Dict]) -> List[Dict]:
    """Every judgeable item of every error-free record, with its key and a
    pointer to its record."""
    items = []
    for record in records:
        if record.get("error") or not record.get("score"):
            continue
        module = BEHAVIORS[record["behavior"]]
        if not hasattr(module, "judge_items"):
            continue
        for item in module.judge_items(record):
            items.append({"record": record, "item": item, "key": item_key(record, item)})
    return items


def merge_verdicts(records: List[Dict], judgments: Dict[str, Dict], judge_spec: str) -> int:
    """Put the verdicts into the records' judge fields. Returns the number
    of records that got a judge field."""
    judged = 0
    for record in records:
        if record.get("error") or not record.get("score"):
            continue
        module = BEHAVIORS[record["behavior"]]
        if not hasattr(module, "judge_items"):
            continue
        verdicts = {}
        for item in module.judge_items(record):
            row = judgments.get(item_key(record, item))
            if row is not None:
                verdicts[item["turn"]] = {"leak": row.get("leak"), "reasoning": row.get("reasoning", ""), "error": row.get("error")}
        record["judge"] = module.judge_aggregate(record, verdicts, judge_spec)
        if record["judge"] is not None:
            judged += 1
    return judged


def judge_run(
    out_dir: str,
    judge_spec: str,
    workers: int = 4,
    timeout: float = 180.0,
    limit: Optional[int] = None,
    log: Callable[[str], None] = lambda s: print(s, file=sys.stderr),
    extra_body: Optional[Dict] = None,
) -> Dict:
    """Judge every item of the run in out_dir that has no error-free verdict
    yet, then rewrite transcripts.jsonl, run.json and results.md."""
    with open(os.path.join(out_dir, RUN_META), encoding="utf-8") as fh:
        meta = json.load(fh)
    records = load_records(out_dir)
    items = collect_items(records)
    done = load_judgments(out_dir, judge_spec)
    todo = [x for x in items if x["key"] not in done]
    if limit:
        todo = todo[:limit]
    log("%d items, %d already judged, %d to judge with %s" % (len(items), len(items) - len([x for x in items if x["key"] not in done]), len(todo), judge_spec))
    client = make_client(judge_spec, TEMPERATURE, timeout, extra_body)

    lock = threading.Lock()
    errors = 0
    count = 0
    judge_path = os.path.join(out_dir, JUDGE_FILE)
    with open(judge_path, "a", encoding="utf-8") as fh:
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {}
        for x in todo:
            module = BEHAVIORS[x["record"]["behavior"]]
            futures[executor.submit(judge_item, client, module, x["item"], x["key"])] = x
        try:
            for fut in as_completed(futures):
                x = futures[fut]
                record, item = x["record"], x["item"]
                row = {
                    "key": x["key"],
                    "model": record["model"],
                    "behavior": record["behavior"],
                    "strategy": record["strategy"],
                    "scenario_id": record["scenario_id"],
                    "repeat": record["repeat"],
                    "turn": item["turn"],
                    "kind": item.get("kind"),
                    "judge": judge_spec,
                    "rubric": BEHAVIORS[record["behavior"]].JUDGE_RUBRIC_VERSION,
                    "judged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "leak": None,
                    "reasoning": "",
                    "raw": "",
                    "usage": {},
                    "error": None,
                }
                try:
                    row.update(fut.result())
                except Exception as e:  # recorded; the run keeps going
                    row["error"] = "%s: %s" % (type(e).__name__, e)
                with lock:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    count += 1
                    if row["error"]:
                        errors += 1
                    else:
                        done[row["key"]] = row
                log(
                    "[%d/%d] %-28s %-11s %-22s turn %d %-10s %s"
                    % (count, len(todo), record["model"][:28], record["strategy"], record["scenario_id"][:22], item["turn"] + 1, item.get("kind", ""), "ERROR" if row["error"] else ("LEAK" if row["leak"] else "ok"))
                )
        except KeyboardInterrupt:
            log("interrupted; merging the %d verdicts so far" % count)
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=True)

    judged = merge_verdicts(records, done, judge_spec)
    with open(os.path.join(out_dir, TRANSCRIPTS), "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    meta["judge"] = {
        "model": judge_spec,
        "rubrics": sorted({BEHAVIORS[r["behavior"]].JUDGE_RUBRIC_VERSION for r in records if r.get("judge")}),
        "judged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "items": len(items),
        "judged_items": len([x for x in items if x["key"] in done]),
        "records_judged": judged,
        "errors_this_run": errors,
        "git_sha": _git_sha(),
    }
    with open(os.path.join(out_dir, RUN_META), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    with open(os.path.join(out_dir, RESULTS), "w", encoding="utf-8") as fh:
        fh.write(report.render(records, meta))
    return {"records": records, "meta": meta, "out_dir": out_dir, "judged_now": count, "errors": errors}


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def sample_items(out_dir: str, n: int, seed: int) -> List[Dict]:
    """A seeded sample of n judgeable items, drawn round-robin over the item
    kinds so every pressure kind is represented, as rows for a labels file:
    everything a human needs to label, with label set to null."""
    records = load_records(out_dir)
    items = collect_items(records)
    rng = random.Random(seed)
    by_kind: Dict[str, List[Dict]] = {}
    for x in items:
        by_kind.setdefault(x["item"].get("kind", "?"), []).append(x)
    for bucket in by_kind.values():
        rng.shuffle(bucket)
    kinds = sorted(by_kind)
    rng.shuffle(kinds)
    picked: List[Dict] = []
    while len(picked) < n and any(by_kind.values()):
        for kind in kinds:
            if by_kind[kind] and len(picked) < n:
                picked.append(by_kind[kind].pop())
    rows = []
    for x in picked:
        r, it = x["record"], x["item"]
        rows.append(
            {
                "key": x["key"],
                "model": r["model"],
                "strategy": r["strategy"],
                "scenario_id": r["scenario_id"],
                "turn": it["turn"] + 1,
                "kind": it.get("kind"),
                "answer": it.get("answer"),
                "user": it["user"],
                "reply": it["reply"],
                "label": None,
                "note": "",
            }
        )
    return rows


def write_labels_template(rows: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def current_judge(out_dir: str) -> Optional[str]:
    """The judge model recorded by the last judge_run on this directory."""
    with open(os.path.join(out_dir, RUN_META), encoding="utf-8") as fh:
        return (json.load(fh).get("judge") or {}).get("model")


def agreement(out_dir: str, labels_path: str, judge_spec: Optional[str] = None) -> Dict:
    """Hand labels (label: true means the reply identifies the move) against
    the judge's verdicts. Returns counts, a confusion matrix with leak as the
    positive class, and every disagreement. The judge defaults to the one
    recorded in run.json."""
    judge_spec = judge_spec or current_judge(out_dir)
    judgments = load_judgments(out_dir, judge_spec)
    labeled = []
    with open(labels_path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if isinstance(row.get("label"), bool):
                labeled.append(row)
    tp = fp = fn = tn = 0
    missing = 0
    disagreements = []
    for row in labeled:
        j = judgments.get(row["key"])
        if j is None:
            missing += 1
            continue
        human, machine = row["label"], bool(j["leak"])
        if human and machine:
            tp += 1
        elif human and not machine:
            fn += 1
        elif machine:
            fp += 1
        else:
            tn += 1
        if human != machine:
            disagreements.append({**{k: row[k] for k in ("key", "kind", "answer", "user", "reply", "label", "note")}, "judge_leak": machine, "judge_reasoning": j.get("reasoning", "")})
    compared = tp + fp + fn + tn
    return {
        "judge": judge_spec,
        "labeled": len(labeled),
        "compared": compared,
        "missing_judgments": missing,
        "agree": tp + tn,
        "agreement": (tp + tn) / compared if compared else None,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "disagreements": disagreements,
    }


def agreement_fresh(out_dir: str, labels_path: str, judge_spec: str, extra_body: Optional[Dict] = None,
                    workers: int = 4, timeout: float = 180.0) -> Dict:
    """Judge only the labeled items with the given judge configuration,
    without touching the run's files, and return the agreement. Verdicts go
    to <labels_path>.<tag>.jsonl so the check is auditable. This is how a
    cheaper judge configuration (for example reasoning switched off) is
    calibrated before it gates training data."""
    labeled = []
    with open(labels_path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if isinstance(row.get("label"), bool):
                labeled.append(row)
    items = {x["key"]: x for x in collect_items(load_records(out_dir))}
    client = make_client(judge_spec, TEMPERATURE, timeout, extra_body)
    tag = "noreasoning" if extra_body else "default"
    verdict_path = "%s.%s.jsonl" % (labels_path, tag)
    verdicts: Dict[str, Dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for row in labeled:
            x = items.get(row["key"])
            if x is None:
                continue
            module = BEHAVIORS[x["record"]["behavior"]]
            futures[executor.submit(judge_item, client, module, x["item"], x["key"])] = row["key"]
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                verdicts[key] = {**fut.result(), "error": None}
            except Exception as e:
                verdicts[key] = {"leak": None, "reasoning": "", "error": "%s: %s" % (type(e).__name__, e)}
    with open(verdict_path, "w", encoding="utf-8") as fh:
        for key, v in verdicts.items():
            fh.write(json.dumps({"key": key, "judge": judge_spec, "extra_body": extra_body, **v}, ensure_ascii=False) + "\n")
    tp = fp = fn = tn = 0
    missing = 0
    disagreements = []
    for row in labeled:
        v = verdicts.get(row["key"])
        if v is None or v.get("error"):
            missing += 1
            continue
        human, machine = row["label"], bool(v["leak"])
        tp += human and machine
        fn += human and not machine
        fp += (not human) and machine
        tn += (not human) and (not machine)
        if human != machine:
            disagreements.append({**{k: row[k] for k in ("key", "kind", "answer", "user", "reply", "label", "note")}, "judge_leak": machine, "judge_reasoning": v.get("reasoning", "")})
    compared = tp + fp + fn + tn
    return {"judge": "%s (%s)" % (judge_spec, tag), "labeled": len(labeled), "compared": compared, "missing_judgments": missing,
            "agree": tp + tn, "agreement": (tp + tn) / compared if compared else None, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "disagreements": disagreements, "verdicts_path": verdict_path}


def render_agreement(result: Dict) -> str:
    lines = [
        "judge %s" % result.get("judge"),
        "labeled %d, compared %d, missing judgments %d" % (result["labeled"], result["compared"], result["missing_judgments"]),
        "agreement %s (%d of %d)" % ("n/a" if result["agreement"] is None else "%.0f%%" % (100 * result["agreement"]), result["agree"], result["compared"]),
        "leak as positive: tp %d, fp %d, fn %d, tn %d" % (result["tp"], result["fp"], result["fn"], result["tn"]),
    ]
    for d in result["disagreements"]:
        lines.append("")
        lines.append("DISAGREEMENT %s (%s, answer %s): human %s, judge %s" % (d["key"], d["kind"], d["answer"], d["label"], d["judge_leak"]))
        lines.append("  user:  " + d["user"][:200].replace("\n", " "))
        lines.append("  reply: " + d["reply"][:400].replace("\n", " "))
        lines.append("  human note:  " + d["note"])
        lines.append("  judge said:  " + d["judge_reasoning"])
    return "\n".join(lines)
