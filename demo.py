#!/usr/bin/env python3
"""Side-by-side demo: the same conversation through the base model and the
tuned adapter, with the harness's zero-shot system prompt, so a grader can
type any prompt and watch both answer.

    .venv-train/bin/python demo.py --model models/v2/adapter --baseline unsloth/Qwen3-1.7B \
        --prompt "FEN: 6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1. White to move. What should I play?"

    .venv-train/bin/python demo.py --model <hf-repo-id>@<commit> --baseline unsloth/Qwen3-1.7B --chat

--prompt runs one user turn and prints both replies (repeat --prompt for a
scripted multi-turn conversation: every prompt is sent to both models in
the same conversation). --chat reads turns from stdin until an empty line.
--fen builds the opening turn from a FEN with python-chess, so the position
is described the way the eval set describes it. Both models see the same
history, each with its own earlier replies.
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from behaviors.chess_coach import STRATEGIES
from eval import normalize_spec, with_revision
from pilot.clients import make_client

MAX_TOKENS = 400


def opening_from_fen(fen: str) -> str:
    import chess
    from datagen.positions import prose

    board = chess.Board(fen)
    return "Here is my game.\n\nFEN: %s\n%s\n\nWhat should I play?" % (board.fen(), prose(board))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Base vs tuned, side by side, on any prompt.")
    p.add_argument("--model", required=True, help="tuned adapter: path or Hub id, optionally @commit")
    p.add_argument("--baseline", default="unsloth/Qwen3-1.7B")
    p.add_argument("--revision", default=None)
    p.add_argument("--prompt", action="append", default=[], help="a user turn; repeat for a scripted conversation")
    p.add_argument("--fen", default=None, help="build the opening turn from this FEN")
    p.add_argument("--chat", action="store_true", help="read further user turns from stdin")
    p.add_argument("--temperature", type=float, default=None, help="unset means greedy, as in the eval")
    args = p.parse_args(argv)

    specs = {"base": normalize_spec(args.baseline), "tuned": with_revision(normalize_spec(args.model), args.revision)}
    print("loading %s and %s ..." % (specs["base"], specs["tuned"]), file=sys.stderr)
    clients = {name: make_client(spec, args.temperature, 600.0) for name, spec in specs.items()}
    for name, c in clients.items():
        if hasattr(c, "revision"):
            print("%s: %s (revision %s, base %s at %s)" % (name, specs[name], c.revision, c.base, c.base_revision), file=sys.stderr)
    system = STRATEGIES["zero_shot"]  # the prompt train.py trained with and eval.py evaluates with

    histories: Dict[str, List[Dict[str, str]]] = {name: [] for name in clients}
    turns = list(args.prompt)
    if args.fen:
        turns.insert(0, opening_from_fen(args.fen))

    def ask(user: str) -> None:
        print("\n=== USER\n%s" % user)
        for name, c in clients.items():
            histories[name].append({"role": "user", "content": user})
            reply = c.chat(system, histories[name], MAX_TOKENS)
            histories[name].append({"role": "assistant", "content": reply.text})
            print("\n--- %s (%s)\n%s" % (name.upper(), specs[name], reply.text))

    for user in turns:
        ask(user)
    if args.chat:
        print("\n(type a user turn and press Enter; an empty line ends the chat)", file=sys.stderr)
        for line in sys.stdin:
            line = line.rstrip("\n")
            if not line.strip():
                break
            ask(line)
    if not turns and not args.chat:
        p.error("give --prompt, --fen or --chat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
