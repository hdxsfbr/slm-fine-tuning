"""The gate: nothing the teacher wrote is trusted.

Stages, each recorded in the report with how many rows it dropped:

    structure   alternating roles, every user turn has its planned kind,
                the first user turn carries the FEN, every message 15 to
                2000 characters
    dedupe      normalized text of all assistant turns, exact match
    checks      hint turns: no square or move, at most two sentences, no
                affirmation on confirm turns; normal turns: not a refusal
                and at least twelve words
    judge       every hint turn through the same judge and rubric as the
                ablation; a row fails if any hint turn states the move
    leakage     no FEN or user message shared with the eval scenarios
    split       stratified by position family, 10% held out as the
                synthetic test set; sha256 of each file in the manifest
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple

from behaviors import chess_coach as c
from pilot.judge import judge_item

MIN_CHARS = 15
MAX_CHARS = 2000
MIN_NORMAL_WORDS = 12
_REFUSAL = re.compile(r"\b(hint|can't (?:answer|tell|say|list)|cannot (?:answer|tell|say|list)|won't (?:answer|tell|say|list)|not going to (?:answer|tell|say))\b", re.I)
_NORMALIZE = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    return _NORMALIZE.sub(" ", text.lower()).strip()


def check_structure(row: Dict) -> Optional[str]:
    msgs = row.get("messages") or []
    plan_kinds = [t["kind"] for t in row["plan"]["turns"]]
    if len(msgs) != 2 * len(plan_kinds):
        return "turn count %d, plan wants %d" % (len(msgs) // 2, len(plan_kinds))
    for i, m in enumerate(msgs):
        want = "user" if i % 2 == 0 else "assistant"
        if m["role"] != want:
            return "role order broken at message %d" % i
        if not (MIN_CHARS <= len(m["content"]) <= MAX_CHARS):
            return "message %d has %d characters" % (i, len(m["content"]))
    got_kinds = [m["kind"] for m in msgs[0::2]]
    if got_kinds != plan_kinds:
        return "kinds %s differ from plan %s" % (got_kinds, plan_kinds)
    if row["position"]["fen"].split()[0] not in msgs[0]["content"]:
        return "first user turn does not carry the FEN"
    return None


def check_turns(row: Dict, require_squares: bool = True) -> Tuple[bool, List[Dict]]:
    """Code checks per assistant turn, reusing the scorer of the behavior.

    require_squares makes a normal-turn answer fail unless it names at least
    one square or move. The v1 data was gated without it, and the v1 model
    learned to answer rules questions without squares; see the README."""
    msgs = row["messages"]
    results = []
    ok_all = True
    for i in range(0, len(msgs), 2):
        kind = msgs[i]["kind"]
        reply = msgs[i + 1]["content"]
        if kind == "normal":
            words = len(reply.split())
            refusal = bool(_REFUSAL.search(reply))
            has_squares = bool(c.find_leaks(reply))
            ok = words >= MIN_NORMAL_WORDS and not refusal and (has_squares or not require_squares)
            results.append({"turn": i // 2, "kind": kind, "ok": ok, "words": words, "refusal": refusal, "squares": has_squares})
        else:
            t = c.score_turn({"kind": kind}, reply)
            ok = bool(t["ok"])
            results.append({"turn": i // 2, "kind": kind, "ok": ok, "leaks": t["leaks"], "sentences": t["sentences"], "affirmed": t["affirmed"]})
        ok_all = ok_all and ok
    return ok_all, results


def judge_items_for(row: Dict) -> List[Dict]:
    msgs = row["messages"]
    items = []
    for i in range(0, len(msgs), 2):
        if msgs[i]["kind"] == "normal":
            continue
        items.append({
            "turn": i // 2,
            "kind": msgs[i]["kind"],
            "user": msgs[i]["content"],
            "reply": msgs[i + 1]["content"],
            "position": "FEN: %s\n%s" % (row["position"]["fen"], row["position"]["prose"]),
            "answer": row["position"]["answer"],
        })
    return items


def _judge_key(row: Dict, item: Dict) -> str:
    return "%s|%d" % (row["id"], item["turn"])


def load_verdicts(path: str) -> Dict[str, Dict]:
    done: Dict[str, Dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                v = json.loads(line)
                if not v.get("error") and v.get("rubric") == c.JUDGE_RUBRIC_VERSION:
                    done[v["key"]] = v
    return done


def judge_rows(rows: List[Dict], judge_client, cache_path: str, workers: int = 6,
               log: Callable[[str], None] = lambda s: print(s, file=sys.stderr)) -> Dict[str, Dict]:
    """Judge every hint turn of the given rows, caching verdicts in
    cache_path (one line per item, same shape as the ablation's judge.jsonl).
    Returns the verdict map for all items of these rows."""
    done = load_verdicts(cache_path)
    todo = []
    for row in rows:
        for item in judge_items_for(row):
            key = _judge_key(row, item)
            if key not in done:
                todo.append((row, item, key))
    log("judge: %d items, %d cached, %d to judge" % (len(todo) + sum(1 for r in rows for it in judge_items_for(r) if _judge_key(r, it) in done), len(done), len(todo)))
    lock = threading.Lock()
    count = 0
    with open(cache_path, "a", encoding="utf-8") as fh:
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {executor.submit(judge_item, judge_client, c, item, key): (row, item, key) for row, item, key in todo}
        try:
            for fut in as_completed(futures):
                row, item, key = futures[fut]
                v = {"key": key, "row_id": row["id"], "turn": item["turn"], "kind": item["kind"], "judge": judge_client.spec,
                     "rubric": c.JUDGE_RUBRIC_VERSION, "leak": None, "reasoning": "", "raw": "", "usage": {}, "error": None,
                     "judged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
                try:
                    v.update(fut.result())
                except Exception as e:
                    v["error"] = "%s: %s" % (type(e).__name__, e)
                with lock:
                    fh.write(json.dumps(v, ensure_ascii=False) + "\n")
                    fh.flush()
                    count += 1
                    if not v["error"]:
                        done[key] = v
                if count % 50 == 0 or count == len(todo):
                    log("judge: %d/%d" % (count, len(todo)))
        except KeyboardInterrupt:
            log("judge interrupted after %d items" % count)
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=True)
    return done


def eval_fingerprints() -> Tuple[set, set]:
    fens = {p["fen"].split()[0] for p in c.POSITIONS.values()}
    user_texts = {normalize(t["user"]) for s in c.SCENARIOS for t in s["turns"]}
    return fens, user_texts


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def run_gate(rows: List[Dict], out_dir: str, judge_client=None, judge_workers: int = 6, seed: int = 0,
             holdout: float = 0.10, require_squares: bool = True,
             log: Callable[[str], None] = lambda s: print(s, file=sys.stderr)) -> Dict:
    """Apply every stage, write train.jsonl, synthetic_test.jsonl, rejected.jsonl,
    gate_report.md and manifest.json into out_dir. Returns the report dict."""
    os.makedirs(out_dir, exist_ok=True)
    report: Dict = {"stages": [], "input": len(rows)}
    rejected: List[Dict] = []

    def stage(name: str, keep: List[Dict], dropped: List[Tuple[Dict, str]]) -> List[Dict]:
        report["stages"].append({"stage": name, "in": len(keep) + len(dropped), "out": len(keep), "dropped": len(dropped)})
        for row, why in dropped:
            rejected.append({"id": row["id"], "stage": name, "why": why})
        log("gate %-10s in %4d  out %4d  dropped %4d" % (name, len(keep) + len(dropped), len(keep), len(dropped)))
        return keep

    # structure
    keep, drop = [], []
    for row in rows:
        if row.get("error"):
            drop.append((row, "teacher error: " + row["error"][:80]))
            continue
        why = check_structure(row)
        (drop if why else keep).append((row, why) if why else row)
    rows = stage("structure", keep, drop)

    # dedupe
    seen = set()
    keep, drop = [], []
    for row in rows:
        key = normalize(" ".join(m["content"] for m in row["messages"] if m["role"] == "assistant"))
        if key in seen:
            drop.append((row, "duplicate assistant text"))
        else:
            seen.add(key)
            keep.append(row)
    rows = stage("dedupe", keep, drop)

    # code checks
    keep, drop = [], []
    for row in rows:
        ok, results = check_turns(row, require_squares)
        row["checks"] = results
        if ok:
            keep.append(row)
        else:
            bad = [r for r in results if not r["ok"]]
            drop.append((row, "; ".join("turn %d (%s) %s" % (r["turn"] + 1, r["kind"], "leaks %s" % r["leaks"] if r.get("leaks") else ("%d sentences" % r["sentences"] if r.get("sentences") and r["sentences"] > c.MAX_SENTENCES else ("affirmed" if r.get("affirmed") else ("refusal" if r.get("refusal") else ("no squares in the answer" if r.get("squares") is False and r.get("words", 0) >= MIN_NORMAL_WORDS else "%d words" % r.get("words", 0)))))) for r in bad)))
    rows = stage("checks", keep, drop)
    report["require_squares"] = require_squares

    # judge
    if judge_client is not None:
        cache = os.path.join(out_dir, "judge_gen.jsonl")
        verdicts = judge_rows(rows, judge_client, cache, judge_workers, log)
        keep, drop = [], []
        for row in rows:
            items = judge_items_for(row)
            vs = [verdicts.get(_judge_key(row, it)) for it in items]
            if any(v is None for v in vs):
                drop.append((row, "judge error or missing verdict"))
                continue
            leaks = [(it["turn"] + 1, it["kind"], v["reasoning"]) for it, v in zip(items, vs) if v["leak"]]
            row["judge"] = {"model": judge_client.spec, "rubric": c.JUDGE_RUBRIC_VERSION, "leaks": leaks}
            if leaks:
                drop.append((row, "; ".join("turn %d (%s) %s" % l for l in leaks[:3])))
            else:
                keep.append(row)
        rows = stage("judge", keep, drop)
        usage_in = sum(v.get("usage", {}).get("input_tokens", 0) for v in verdicts.values())
        usage_out = sum(v.get("usage", {}).get("output_tokens", 0) for v in verdicts.values())
        report["judge"] = {"model": judge_client.spec, "rubric": c.JUDGE_RUBRIC_VERSION, "verdicts": len(verdicts),
                           "input_tokens": usage_in, "output_tokens": usage_out}

    # leakage against the eval scenarios
    fens, user_texts = eval_fingerprints()
    keep, drop = [], []
    for row in rows:
        if row["position"]["fen"].split()[0] in fens:
            drop.append((row, "position is an eval position"))
            continue
        if any(normalize(m["content"]) in user_texts for m in row["messages"] if m["role"] == "user"):
            drop.append((row, "user turn identical to an eval scenario turn"))
            continue
        keep.append(row)
    rows = stage("leakage", keep, drop)

    # split, stratified by position family
    rng = random.Random(seed)
    by_family: Dict[str, List[Dict]] = {}
    for row in rows:
        by_family.setdefault(row["position"]["family"], []).append(row)
    train, test = [], []
    for family in sorted(by_family):
        bucket = by_family[family]
        rng.shuffle(bucket)
        k = int(round(holdout * len(bucket)))
        test += bucket[:k]
        train += bucket[k:]
    rng.shuffle(train)
    rng.shuffle(test)

    def strip(row: Dict) -> Dict:
        return {
            "id": row["id"],
            "family": row["position"]["family"],
            "persona": row["plan"]["persona"],
            "kinds": [m["kind"] for m in row["messages"] if m["role"] == "user"],
            "messages": [{"role": m["role"], "content": m["content"]} for m in row["messages"]],
        }

    paths = {}
    for name, subset in (("train", train), ("synthetic_test", test)):
        path = os.path.join(out_dir, name + ".jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for row in subset:
                fh.write(json.dumps(strip(row), ensure_ascii=False) + "\n")
        paths[name] = {"path": path, "rows": len(subset), "sha256": sha256_of(path)}
    with open(os.path.join(out_dir, "rejected.jsonl"), "w", encoding="utf-8") as fh:
        for r in rejected:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    report["output"] = paths
    report["families"] = {f: len(b) for f, b in sorted(by_family.items())}
    report["kinds"] = {}
    for row in rows:
        for m in row["messages"]:
            if m["role"] == "user":
                report["kinds"][m["kind"]] = report["kinds"].get(m["kind"], 0) + 1
    report["personas"] = {}
    for row in rows:
        report["personas"][row["plan"]["persona"]] = report["personas"].get(row["plan"]["persona"], 0) + 1
    report["gated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    with open(os.path.join(out_dir, "gate_report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_report(report, rejected))
    return report


def render_report(report: Dict, rejected: List[Dict]) -> str:
    out = ["# Data gate report", "", "- Gated: %s" % report.get("gated_at"), "- Input rows: %d" % report["input"], ""]
    out += ["| Stage | In | Out | Dropped |", "|---|---|---|---|"]
    for s in report["stages"]:
        out.append("| %s | %d | %d | %d |" % (s["stage"], s["in"], s["out"], s["dropped"]))
    out.append("")
    if report.get("judge"):
        j = report["judge"]
        out.append("Judge: %s, rubric %s, %d verdicts, %d input and %d output tokens." % (j["model"], j["rubric"], j["verdicts"], j["input_tokens"], j["output_tokens"]))
        out.append("")
    out.append("## Output")
    out.append("")
    for name, info in report["output"].items():
        out.append("- `%s`: %d rows, sha256 `%s`" % (os.path.basename(info["path"]), info["rows"], info["sha256"]))
    out.append("")
    out.append("## Coverage of the gated rows")
    out.append("")
    out.append("Families: " + ", ".join("%s %d" % kv for kv in report["families"].items()))
    out.append("")
    out.append("User-turn kinds: " + ", ".join("%s %d" % kv for kv in sorted(report["kinds"].items(), key=lambda kv: -kv[1])))
    out.append("")
    out.append("Personas: " + ", ".join("%s %d" % kv for kv in sorted(report["personas"].items(), key=lambda kv: -kv[1])))
    out.append("")
    out.append("## Rejections by stage and reason (first 40)")
    out.append("")
    for r in rejected[:40]:
        out.append("- %s [%s] %s" % (r["id"], r["stage"], r["why"]))
    return "\n".join(out) + "\n"
