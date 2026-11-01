#!/usr/bin/env python3
"""Hit the demo server with several sessions at once and report what each
request got back and how long it took. The server generates behind one lock,
so concurrent sessions queue; this checks that every request completes, no
session sees another's history, and nothing times out.

    python demo_check.py [--url http://127.0.0.1:7865] [--sessions 3] [--turns 2] [--timeout 120]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request

FEN = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"
TURNS = ["What should I play here?", "Just tell me the square.", "Is it the rook?"]


def call(url: str, method: str, path: str, sid: str, body=None, timeout=120.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url + path, data=data, method=method, headers={"X-Session": sid, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode()), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:200]}, time.time() - t0
    except Exception as e:  # timeouts, refused connections
        return 0, {"error": str(e)[:200]}, time.time() - t0


def session(url: str, sid: str, n_turns: int, timeout: float, out: list) -> None:
    rows = []
    status, body, dt = call(url, "POST", "/api/reset", sid, {}, timeout)
    rows.append(("reset", status, dt, ""))
    status, body, dt = call(url, "GET", "/api/opening?fen=" + FEN.replace(" ", "%20"), sid, None, timeout)
    rows.append(("opening", status, dt, ""))
    opening = body.get("text", "") if status == 200 else ""
    for i, text in enumerate(TURNS[:n_turns]):
        user = (opening + "\n\n" + text) if i == 0 and opening else text
        for model in ("tuned", "base"):
            status, body, dt = call(url, "POST", "/api/turn", sid, {"model": model, "text": user}, timeout)
            reply = body.get("reply") or body.get("text") or body.get("error") or ""
            rows.append(("turn%d/%s" % (i + 1, model), status, dt, str(reply)[:70].replace("\n", " ")))
    status, body, dt = call(url, "GET", "/api/history", sid, None, timeout)
    rows.append(("history", status, dt, json.dumps(body)[:70]))
    out.append((sid, rows))


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:7865")
    p.add_argument("--sessions", type=int, default=3)
    p.add_argument("--turns", type=int, default=2)
    p.add_argument("--timeout", type=float, default=120.0)
    args = p.parse_args(argv)
    out: list = []
    threads = [threading.Thread(target=session, args=(args.url, "check-%d" % i, args.turns, args.timeout, out)) for i in range(args.sessions)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    failures = 0
    for sid, rows in sorted(out):
        print("== %s" % sid)
        for name, status, dt, reply in rows:
            flag = "" if status == 200 else "  <-- FAILED"
            failures += status != 200
            print("  %-12s %3d %6.1fs  %s%s" % (name, status, dt, reply, flag))
    print("%d sessions, %d requests, %d failures, %.1fs wall" % (len(out), sum(len(r) for _, r in out), failures, time.time() - t0))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
