"""Merge gated data directories into one dataset version.

v3 = the v2 rows plus a batch generated with the v3 plan mix, each gated on
its own. Rows keep their source as an id prefix, both splits are shuffled
with a seed, and the merge refuses to write a set whose test rows share a
position with its train rows (the FEN placement is read from the first user
turn, which the gate requires every row to carry).

    python run_datagen.py merge --out data/v3 data/v2 data/v3_extra
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import re
from typing import Dict, List, Optional, Tuple

_PLACEMENT = re.compile(r"(?<![A-Za-z0-9/])(?:[pnbrqkPNBRQK1-8]{1,8}/){7}[pnbrqkPNBRQK1-8]{1,8}(?![A-Za-z0-9/])")

FILES = ("train.jsonl", "synthetic_test.jsonl")


def placement_of(row: Dict) -> Optional[str]:
    """The piece placement in the row's first user turn, or None."""
    for m in row["messages"]:
        if m["role"] == "user":
            found = _PLACEMENT.search(m["content"])
            return found.group(0) if found else None
    return None


def _read(path: str) -> List[Dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merge(sources: List[str], out_dir: str, seed: int = 0) -> Dict:
    """Write train.jsonl, synthetic_test.jsonl, manifest.json and
    gate_report.md into out_dir from the gated files of each source
    directory. Returns the manifest."""
    os.makedirs(out_dir, exist_ok=True)
    manifest: Dict = {"merged_from": [], "seed": seed}
    splits: Dict[str, List[Dict]] = {name: [] for name in FILES}
    for src in sources:
        name = os.path.basename(os.path.normpath(src))
        entry = {"path": src, "name": name}
        for fname in FILES:
            path = os.path.join(src, fname)
            rows = _read(path)
            for row in rows:
                row = dict(row)
                row["id"] = "%s/%s" % (name, row["id"])
                splits[fname].append(row)
            entry[fname] = {"rows": len(rows), "sha256": _sha256(path)}
        src_manifest = os.path.join(src, "manifest.json")
        if os.path.exists(src_manifest):
            with open(src_manifest, encoding="utf-8") as fh:
                m = json.load(fh)
            entry["gate"] = {k: m.get(k) for k in ("stages", "judge", "holdout", "require_squares", "gated_at") if k in m}
        manifest["merged_from"].append(entry)
    rng = random.Random(seed)
    for rows in splits.values():
        rng.shuffle(rows)
    train_places = {placement_of(r) for r in splits["train.jsonl"]}
    test_places = {placement_of(r) for r in splits["synthetic_test.jsonl"]}
    missing = sum(1 for p in list(train_places) + list(test_places) if p is None)
    if missing:
        raise ValueError("%d rows carry no FEN placement in their first user turn" % missing)
    shared = train_places & test_places
    if shared:
        raise ValueError("%d placements are in both train and test: %s" % (len(shared), sorted(shared)[:3]))
    ids = [r["id"] for rows in splits.values() for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate row ids after prefixing")
    manifest["holdout"] = {
        "by": "position",
        "test_placements": len(test_places),
        "placements_shared_with_train": 0,
    }
    manifest["output"] = {}
    for fname, rows in splits.items():
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["output"][fname.split(".")[0]] = {"path": path, "rows": len(rows), "sha256": _sha256(path)}
    manifest["families"] = _count(splits["train.jsonl"], lambda r: r["family"])
    manifest["kinds"] = _count(splits["train.jsonl"], None)
    manifest["personas"] = _count(splits["train.jsonl"], lambda r: r["persona"])
    manifest["merged_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    with open(os.path.join(out_dir, "gate_report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_report(manifest))
    return manifest


def _count(rows: List[Dict], key) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        values = r["kinds"] if key is None else [key(r)]
        for v in values:
            out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def render_report(manifest: Dict) -> str:
    out = ["# Merged data report", "", "- Merged: %s" % manifest["merged_at"], "- Shuffle seed: %d" % manifest["seed"], ""]
    out += ["| Source | train rows | test rows | gated |", "|---|---|---|---|"]
    for e in manifest["merged_from"]:
        gate = e.get("gate", {})
        out.append("| `%s` | %d | %d | %s |" % (e["path"], e["train.jsonl"]["rows"], e["synthetic_test.jsonl"]["rows"], gate.get("gated_at", "see its own gate_report.md")))
    out.append("")
    out.append("Each source was gated on its own (structure, dedupe, code checks, judge, leakage, split held out by position); its gate_report.md has the stage counts. Row ids carry the source name as a prefix.")
    out.append("")
    out.append("## Output")
    out.append("")
    for name, info in manifest["output"].items():
        out.append("- `%s`: %d rows, sha256 `%s`" % (os.path.basename(info["path"]), info["rows"], info["sha256"]))
    out.append("")
    h = manifest["holdout"]
    out.append("Held out by position: %d test placements, %d shared with train." % (h["test_placements"], h["placements_shared_with_train"]))
    out.append("")
    out.append("## Coverage of the training rows")
    out.append("")
    out.append("Families: " + ", ".join("%s %d" % kv for kv in manifest["families"].items()))
    out.append("")
    out.append("User-turn kinds: " + ", ".join("%s %d" % kv for kv in manifest["kinds"].items()))
    out.append("")
    out.append("Personas: " + ", ".join("%s %d" % kv for kv in manifest["personas"].items()))
    return "\n".join(out) + "\n"
