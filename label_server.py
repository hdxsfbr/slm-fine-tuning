#!/usr/bin/env python3
"""A page for hand-labeling judge calibration items.

Serves the items of a labels file (run_judge.py sample writes one) one at a
time: the board from the FEN in the user's turn, the user's turn, the
coach's reply and the move the coach must not reveal; two buttons (the
reply identifies the move, or it is a hint) and a note. Labels go to a
separate file in the same row shape, with labeled_by and labeled_at, so
the original labels stay as history and `run_judge.py calibrate --labels
<out>` reads the new file as is. Saving is per item and the page resumes
where it left off. A second file of disputed items (judge_check.py's
disagreements_to_label.jsonl, filtered to one model) can be queued after
the first; its two judges' verdicts are shown only after the item is
labeled.

    python label_server.py --items results/ablation_chess_2026-10-27/labels.jsonl \\
        --out results/ablation_chess_2026-10-27/labels_andre.jsonl --labeler Andre \\
        --disputed results/judge_check_2026-10-29/eval_v2/disagreements_to_label.jsonl --disputed-model adapter
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "label", "index.html")
MAX_BODY_BYTES = 16 * 1024
MAX_NOTE_CHARS = 500
_FEN = re.compile(r"(?<![A-Za-z0-9/])((?:[pnbrqkPNBRQK1-8]{1,8}/){7}[pnbrqkPNBRQK1-8]{1,8}(?:\s+[wb](?:\s+\S+){0,4})?)")

# Fields copied from the source item into the labeled row.
ITEM_FIELDS = ("key", "model", "strategy", "scenario_id", "turn", "kind", "answer", "user", "reply",
               "haiku_leak", "haiku_reasoning", "gemini_leak", "gemini_reasoning")


def read_jsonl(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def fen_of(text: str) -> Optional[str]:
    m = _FEN.search(text or "")
    return m.group(1).strip() if m else None


def scenario_fen(scenario_id: str) -> Optional[str]:
    """The FEN of a challenge scenario by id: only a conversation's first
    turn carries the FEN, and most labeled turns come later."""
    try:
        from behaviors import chess_coach
    except ImportError:  # the page still works without the board
        return None
    for s in chess_coach.SCENARIOS:
        if s["id"] == scenario_id:
            pos = s.get("position")
            if isinstance(pos, str):  # scenarios name their position; POSITIONS holds the FEN
                pos = chess_coach.POSITIONS.get(pos)
            return pos.get("fen") if isinstance(pos, dict) else None
    return None


class LabelStore:
    """Items in order, labels keyed by item key, written whole on every save."""

    def __init__(self, items_path: str, out_path: str, labeler: str,
                 disputed_path: Optional[str] = None, disputed_model: Optional[str] = None):
        self.out_path = out_path
        self.labeler = labeler
        self.lock = threading.Lock()
        self.items: List[Dict] = []
        for row in read_jsonl(items_path):
            self.items.append(self._item(row, "calibration"))
        if disputed_path:
            for row in read_jsonl(disputed_path):
                if disputed_model and disputed_model not in str(row.get("model", "")):
                    continue
                self.items.append(self._item(row, "disputed"))
        self.labels: Dict[str, Dict] = {}
        for row in read_jsonl(out_path):
            if row.get("label") in (True, False):
                self.labels[row["key"]] = row

    @staticmethod
    def _item(row: Dict, queue: str) -> Dict:
        item = {k: row.get(k) for k in ITEM_FIELDS if k in row}
        item["queue"] = queue
        item["fen"] = fen_of(row.get("user", "")) or scenario_fen(str(row.get("scenario_id", "")))
        return item

    def public_item(self, item: Dict, labeled: bool) -> Dict:
        """What the page sees: the judges' verdicts only once labeled, and
        never the source file's own label."""
        out = {k: item.get(k) for k in ("key", "queue", "scenario_id", "turn", "kind", "answer", "user", "reply", "fen", "model")}
        if labeled and item["queue"] == "disputed":
            out["judges"] = {k: item.get(k) for k in ("haiku_leak", "haiku_reasoning", "gemini_leak", "gemini_reasoning")}
        return out

    def state(self) -> Dict:
        with self.lock:
            items = []
            for it in self.items:
                lab = self.labels.get(it["key"])
                public = self.public_item(it, lab is not None)
                if lab:
                    public["label"] = lab["label"]
                    public["note"] = lab.get("note", "")
                items.append(public)
            done = sum(1 for it in self.items if it["key"] in self.labels)
            return {"items": items, "done": done, "total": len(self.items), "labeler": self.labeler, "out": self.out_path,
                    "calibrate": "python run_judge.py calibrate <run directory> --labels %s" % self.out_path}

    def save(self, key: str, label: bool, note: str) -> Dict:
        if not isinstance(label, bool):
            raise ValueError("label must be true or false")
        note = str(note or "")[:MAX_NOTE_CHARS]
        with self.lock:
            item = next((it for it in self.items if it["key"] == key), None)
            if item is None:
                raise KeyError(key)
            row = {k: v for k, v in item.items() if k not in ("fen",)}
            row.update({"label": label, "note": note, "labeled_by": self.labeler,
                        "labeled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            self.labels[key] = row
            os.makedirs(os.path.dirname(self.out_path) or ".", exist_ok=True)
            with open(self.out_path, "w", encoding="utf-8") as fh:
                for it in self.items:
                    if it["key"] in self.labels:
                        fh.write(json.dumps(self.labels[it["key"]], ensure_ascii=False) + "\n")
            return {"ok": True, "done": len(self.labels), "total": len(self.items)}


class Handler(BaseHTTPRequestHandler):
    store: LabelStore = None  # set by make_server

    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            with open(PAGE, "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self._json(200, self.store.state())
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path != "/api/label":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            return self._json(413, {"error": "body too large"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            result = self.store.save(str(body.get("key")), body.get("label"), body.get("note", ""))
        except KeyError:
            return self._json(404, {"error": "unknown item"})
        except (ValueError, TypeError) as e:
            return self._json(400, {"error": str(e)})
        return self._json(200, result)


def make_server(host: str, port: int, store: LabelStore) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Hand-label judge calibration items in a browser.")
    p.add_argument("--items", required=True, help="labels file to relabel (run_judge.py sample shape)")
    p.add_argument("--out", required=True, help="where the new labels go (JSONL, same shape plus labeled_by and labeled_at)")
    p.add_argument("--labeler", default="Andre")
    p.add_argument("--disputed", default=None, help="judge_check.py disagreements file to queue after the items")
    p.add_argument("--disputed-model", default=None, help="keep only disputed rows whose model contains this text")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7866)
    args = p.parse_args(argv)
    store = LabelStore(args.items, args.out, args.labeler, args.disputed, args.disputed_model)
    server = make_server(args.host, args.port, store)
    print("labeling %d items (%d done) at http://%s:%d/ -> %s" % (len(store.items), len(store.labels), args.host, server.server_address[1], args.out), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
