#!/usr/bin/env python3
"""Web demo: the same conversation through the base model and the tuned
adapter, side by side in the browser, so a grader can type any prompt and
watch both answer.

    .venv-train/bin/python demo_server.py --model hdxsfbr/qwen3-1.7b-chess-coach-hints@<commit> \
        --baseline unsloth/Qwen3-1.7B --port 7865

Then open http://127.0.0.1:7865/. The page keeps nothing but what is on
screen; this server holds one history per model, behind one lock, so turns
are generated one at a time on the one GPU. The models, the system prompt
and the token budget are the ones demo.py and eval.py use.

Stdlib only. Endpoints (JSON):

    GET  /                      the page, demo/index.html
    GET  /api/health            specs, loaded revisions, the stored fen, user turns so far
    GET  /api/opening?fen=...   the opening user turn for a FEN; stores the fen and the text
    GET  /api/history           the stored fen and opening, and both histories, so a page
                                opened later shows the conversation so far
    POST /api/turn              {"model": "base"|"tuned", "text": ...} -> {"text", "seconds"}
    POST /api/reset             clears both histories (the fen and opening stay)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from behaviors.chess_coach import STRATEGIES
from demo import MAX_TOKENS, opening_from_fen
from eval import normalize_spec, with_revision
from pilot.clients import make_client

MODELS = ("base", "tuned")
CLIENT_TIMEOUT_S = 600.0
MAX_BODY_BYTES = 64 * 1024
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(HERE, "demo", "index.html")


def log(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


class DemoState:
    """Two clients, two histories, one lock. The lock covers generation as
    well as the histories, so concurrent turns run one after the other."""

    def __init__(self, specs: Dict[str, str], clients: Dict[str, object], system: str = STRATEGIES["zero_shot"]):
        self.specs = specs
        self.clients = clients
        self.system = system
        self.histories: Dict[str, List[Dict[str, str]]] = {name: [] for name in MODELS}
        self.fen: Optional[str] = None
        self.opening: Optional[str] = None
        self.lock = threading.Lock()

    def describe(self, name: str) -> Dict[str, Optional[str]]:
        c = self.clients[name]
        return {
            "spec": self.specs[name],
            "revision": getattr(c, "revision", None),
            "base": getattr(c, "base", None),
            "base_revision": getattr(c, "base_revision", None),
        }

    def health(self) -> Dict:
        with self.lock:
            turns = max(sum(1 for m in h if m["role"] == "user") for h in self.histories.values())
            return {"base": self.describe("base"), "tuned": self.describe("tuned"), "fen": self.fen, "turns": turns}

    def opening_for(self, fen: str) -> str:
        """The opening user turn for a FEN, remembered so a page opened
        later can show the position. Raises ValueError on a bad FEN."""
        text = opening_from_fen(fen)
        with self.lock:
            self.fen = fen
            self.opening = text
        return text

    def history(self) -> Dict:
        with self.lock:
            out: Dict[str, object] = {"fen": self.fen, "opening": self.opening}
            for name in MODELS:
                out[name] = [{"role": m["role"], "content": m["content"]} for m in self.histories[name]]
            return out

    def turn(self, name: str, text: str) -> Dict:
        with self.lock:
            history = self.histories[name]
            history.append({"role": "user", "content": text})
            t0 = time.time()
            try:
                reply = self.clients[name].chat(self.system, history, MAX_TOKENS)
            except Exception:
                history.pop()  # keep the conversation well formed for the next turn
                raise
            history.append({"role": "assistant", "content": reply.text})
            return {"text": reply.text, "seconds": round(time.time() - t0, 2)}

    def reset(self) -> None:
        """Clears the conversations; the fen and opening stay."""
        with self.lock:
            for h in self.histories.values():
                h.clear()


def build_state(model: str, baseline: str = "unsloth/Qwen3-1.7B", revision: Optional[str] = None, temperature: Optional[float] = None) -> DemoState:
    """The two specs and clients, built exactly as demo.py builds them."""
    specs = {"base": normalize_spec(baseline), "tuned": with_revision(normalize_spec(model), revision)}
    log("loading %s and %s ..." % (specs["base"], specs["tuned"]))
    clients = {name: make_client(spec, temperature, CLIENT_TIMEOUT_S) for name, spec in specs.items()}
    for name, c in clients.items():
        if hasattr(c, "revision"):
            log("%s: %s (revision %s, base %s at %s)" % (name, specs[name], c.revision, c.base, c.base_revision))
    return DemoState(specs, clients)


class BadRequest(Exception):
    """Client error: answered with 400 and the message."""


class Handler(BaseHTTPRequestHandler):
    server_version = "ChessCoachDemo/1.0"

    @property
    def state(self) -> DemoState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format, *args):  # noqa: A002 (stdlib signature)
        pass  # one line per request is written in _serve instead

    def do_GET(self) -> None:
        self._serve("GET")

    def do_POST(self) -> None:
        self._serve("POST")

    def _serve(self, method: str) -> None:
        t0 = time.time()
        path = urlsplit(self.path).path
        try:
            status, payload = self._route(method, path)
        except BadRequest as e:
            status, payload = 400, {"error": str(e)}
        except Exception as e:  # a model or client failure must not take the server down
            status, payload = 500, {"error": "%s: %s" % (type(e).__name__, e)}
        if isinstance(payload, bytes):
            self._write(status, "text/html; charset=utf-8", payload)
        else:
            self._write(status, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))
        log("%s %s %d %.2fs" % (method, self.path, status, time.time() - t0))

    def _route(self, method: str, path: str) -> Tuple[int, object]:
        if method == "GET" and path == "/":
            if not os.path.isfile(INDEX_PATH):
                return 404, {"error": "demo/index.html is missing"}
            with open(INDEX_PATH, "rb") as fh:
                return 200, fh.read()
        if method == "GET" and path == "/api/health":
            return 200, self.state.health()
        if method == "GET" and path == "/api/opening":
            query = parse_qs(urlsplit(self.path).query)
            fen = (query.get("fen") or [""])[0].strip()
            if not fen:
                raise BadRequest("fen is required")
            try:
                return 200, {"text": self.state.opening_for(fen)}
            except Exception as e:
                raise BadRequest("invalid FEN: %s" % e)
        if method == "GET" and path == "/api/history":
            return 200, self.state.history()
        if method == "POST" and path == "/api/turn":
            body = self._json_body()
            model = body.get("model")
            text = body.get("text")
            if model not in MODELS:
                raise BadRequest("model must be one of %s" % ", ".join(MODELS))
            if not isinstance(text, str) or not text.strip():
                raise BadRequest("text must be a non-empty string")
            return 200, self.state.turn(model, text.strip())
        if method == "POST" and path == "/api/reset":
            self.state.reset()
            return 200, {"ok": True}
        return 404, {"error": "not found"}

    def _json_body(self) -> Dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise BadRequest("bad Content-Length")
        if length <= 0:
            raise BadRequest("a JSON body is required")
        if length > MAX_BODY_BYTES:
            raise BadRequest("body too large")
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise BadRequest("body is not valid JSON")
        if not isinstance(body, dict):
            raise BadRequest("body must be a JSON object")
        return body

    def _write(self, status: int, content_type: str, data: bytes) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the page went away while a reply was being generated


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], state: DemoState):
        super().__init__(address, Handler)
        self.state = state


def make_server(host: str, port: int, state: DemoState) -> DemoServer:
    """Bound but not yet serving; port 0 picks a free port
    (server.server_address[1])."""
    return DemoServer((host, port), state)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Base vs tuned, side by side, in the browser.")
    p.add_argument("--model", required=True, help="tuned adapter: path or Hub id, optionally @commit")
    p.add_argument("--baseline", default="unsloth/Qwen3-1.7B")
    p.add_argument("--revision", default=None)
    p.add_argument("--temperature", type=float, default=None, help="unset means greedy, as in the eval")
    p.add_argument("--port", type=int, default=7865)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    state = build_state(args.model, args.baseline, args.revision, args.temperature)
    server = make_server(args.host, args.port, state)
    log("serving on http://%s:%d/ (Ctrl-C stops)" % server.server_address[:2])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
