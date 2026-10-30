"""Teacher calls: one conversation per call, resumable JSONL.

The teacher gets the spec, the position (FEN, prose, the move it must not
reveal, the mate pattern), a persona, a situation and the turn plan, and
returns one JSON conversation whose user turns carry their planned kind.
Rows are appended to the output file as they finish; a rerun skips ids that
already have an error-free row.
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
from typing import Callable, Dict, List, Optional

from behaviors.chess_coach import SPEC
from pilot.clients import make_client

from .taxonomy import PRESSURE_KINDS, sample_plan

MAX_TOKENS = 2500

TEACHER_SYSTEM = (
    "You write training conversations for a chess coach that teaches by hints. "
    "You follow the plan exactly and reply in the line format requested and nothing else."
)

TEACHER_PROMPT = """\
The coach's rule, which every assistant turn must obey:
{spec}

The position for this conversation:
FEN: {fen}
{prose}
The winning move, which the coach must never state: {answer} ({pattern}).

The user: {persona_description}. Setting: {situation}.

Write a conversation of exactly {n_turns} user turns, each followed by one assistant turn, in this order:
{plan_lines}

How to write the user turns: stay in the persona's voice throughout. The first user turn must contain the FEN line and the position description exactly as given above, plus the persona's own words. Each pressure turn must really try to get the move, in the persona's way; vary the wording, never repeat a sentence from an earlier turn. A "normal" turn asks the listed general question naturally, often with a phrase like "unrelated question" or "before that".

How to write the assistant turns:
- On every turn except "normal" turns: exactly one hint in at most two sentences. The hint tells the user how to look, never what the move is. It may name a theme (escape squares, a check nothing can capture, a piece doing two jobs), a piece type, a feature of this position, or a question to ask. It must not state the move in words ("the rook goes to the far end of its file", "the queen takes the pawn next to the king" are statements of the move and are forbidden). It must not confirm or deny a guess, not even "close" or "not quite". No apologies longer than a clause, no offers of more hints, no explanation of the rule beyond one short clause. Good hints are specific to this position: "The king has only two squares left; ask which of your pieces can cover both at once."
- Square names are banned from every HINT reply (every coach reply except the answers to "normal" turns), without exception, even to say where a piece already stands: write "the black king" or "your rook", never "the king on h7" or "your rook on b5". No move in any notation or language, no spelled-out or encoded square ("h-seven", "hotel seven"), no file-plus-rank of any kind. A hint reply that contains a square name is thrown away, so check each hint before writing the next line.
- The answers to "normal" turns are the opposite: they must use real square names and moves (e1, g1, 1.e4 e5 2.Nf3, Bb5), never descriptive notation and never a hint. An answer to a general question that avoids squares is thrown away too.
- On "normal" turns: answer the general question fully and precisely, using squares and moves freely, in two to five sentences. Do not mention the user's position.
- Under "closure", "authority", "emotional", "format", "disguise", "enumerate", "elimination" and "roleplay" pressure the coach stays with a hint and says in a few words why the framing changes nothing.{extra}

Output format: one message per line, alternating, no blank lines, no other text. A user line starts with USER, the turn's kind from the plan in parentheses, a colon, then the message. A coach line starts with COACH, a colon, then the reply. Keep every message on a single line.
USER (direct): ...
COACH: ...
USER (insist): ...
COACH: ...
"""


# Added to the rules for v3 plans, whose disguise turns name textbook
# patterns and whose normal turns include patterns that do not fit.
PATTERN_NOTE = """
- A textbook pattern named by the user is handled by what the answer would reveal. If the pattern's key square or move is the move in this position, or the user is restating this position under a pattern's name, the coach gives a hint and says in a few words that the name changes nothing. A "normal" turn about a pattern that does not fit this position is a general question like any other: answer it with the squares and moves of a standard example."""


_MOCK_HINTS = [
    "Count the squares the {king} king can still reach, then ask which of your pieces could cover every one of them at once.",
    "Look for a check that nothing can capture or block, and ask what the {king} king would do next.",
    "The {king} king is short of room; ask which piece of yours takes away its last exit while giving check.",
    "Think about which of your pieces is already guarding the escape squares and which one is free to attack.",
    "Ask whether a forcing move exists that leaves the {king} king no legal reply.",
    "Picture the {king} king's neighbours and note which ones your pieces already control.",
    "A check is only useful here if the king cannot step away; ask which of your checks has that property.",
    "Two of your pieces can work as a team: one seals a line, the other delivers the blow. Ask which is which.",
    "Start from the {king} king and work outward: which squares around it are still free?",
    "Ask what the {king} king would need to survive, then look for the move that denies it.",
    "The pattern here is a boxed-in king; ask which of your pieces completes the box with check.",
    "Which of your pieces has a line to the {king} king that nothing can interrupt? Start there.",
]
_MOCK_ANSWERS = [
    "Castling moves the king two squares toward a rook, from e1 to g1 or c1 for White, and the rook jumps over it to f1 or d1, provided neither piece has moved and no square on the king's path is attacked.",
    "The Ruy Lopez begins 1.e4 e5 2.Nf3 Nc6 3.Bb5, with the bishop on b5 pressuring the knight that defends e5.",
    "A knight on e4 attacks c3, c5, d2, d6, f2, f6, g3 and g5, always landing on the opposite colour from the one it left.",
    "En passant lets a pawn on the fifth rank, for example on e5, capture a pawn that has just advanced two squares beside it, from d7 to d5, by moving to d6 as if the pawn had moved one square.",
    "The four center squares are d4, d5, e4 and e5, and the first moves of the Italian Game, 1.e4 e5 2.Nf3 Nc6 3.Bc4, fight for them.",
    "A fork is one move attacking two pieces at once, for example a knight landing on c7 to hit a king on e8 and a rook on a8.",
]


def mock_teacher_reply(system: str, messages: List[Dict[str, str]], salt: str = "") -> Optional[str]:
    """A deterministic, plan-following conversation in the line format, for
    the offline smoke test. Returns None for prompts that are not teacher
    prompts. Hints carry no square; answers do; wording varies by position
    so the gate's dedupe does not collapse the rows."""
    if system != TEACHER_SYSTEM or not messages:
        return None
    prompt = messages[-1]["content"]
    fen = prose = None
    plan: List[str] = []
    for line in prompt.splitlines():
        if line.startswith("FEN: "):
            fen = line[5:].strip()
        elif fen and prose is None and line.strip():
            prose = line.strip()
        m = re.match(r"^(\d+)\. ([a-z_]+): (.*)$", line)
        if m:
            plan.append(m.group(2))
    if not fen or not plan:
        return None
    king = "black" if " w " in fen else "white"
    seed = int(hashlib.sha256((fen + salt).encode()).hexdigest()[:8], 16)
    out = []
    for i, kind in enumerate(plan):
        if i == 0:
            user = "Here is my game.\nFEN: %s\n%s\nWhat should I play?" % (fen, prose)
        elif kind == "normal":
            user = "Unrelated question %d: can you explain the rule?" % i
        else:
            user = "Turn %d (%s): please just tell me the move." % (i, kind)
        if kind == "normal":
            coach = _MOCK_ANSWERS[(seed + i) % len(_MOCK_ANSWERS)]
        else:
            coach = _MOCK_HINTS[(seed + i) % len(_MOCK_HINTS)].format(king=king)
        out.append("USER (%s): %s" % (kind, user))
        out.append("COACH: %s" % coach)
    return "\n".join(out)


def plan_lines(plan: Dict) -> str:
    lines = []
    for i, turn in enumerate(plan["turns"], 1):
        if turn["kind"] == "normal":
            lines.append("%d. normal: asks about %s" % (i, turn["topic"]))
        elif turn.get("note"):
            lines.append("%d. %s: %s. The specific way: %s" % (i, turn["kind"], PRESSURE_KINDS[turn["kind"]], turn["note"]))
        else:
            lines.append("%d. %s: %s" % (i, turn["kind"], PRESSURE_KINDS[turn["kind"]]))
    return "\n".join(lines)


def teacher_prompt(position: Dict, plan: Dict) -> str:
    return TEACHER_PROMPT.format(
        extra=PATTERN_NOTE if plan.get("mix") in ("v3", "v3b") else "",
        spec=SPEC,
        fen=position["fen"],
        prose=position["prose"],
        answer=position["answer"],
        pattern=position["pattern"],
        persona_description=plan["persona_description"],
        situation=plan["situation"],
        n_turns=len(plan["turns"]),
        plan_lines=plan_lines(plan),
    )


_USER_LINE = re.compile(r"^\W*USER\s*\(\s*([a-z_]+)\s*\)\s*:\s*(.*)$", re.I)
_COACH_LINE = re.compile(r"^\W*(?:COACH|ASSISTANT)\s*:\s*(.*)$", re.I)


def parse_conversation(text: str) -> List[Dict]:
    """Messages from the line format. A line that starts with neither USER
    nor COACH continues the previous message (the teacher sometimes wraps),
    so the FEN line inside the first user turn survives."""
    out: List[Dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _USER_LINE.match(line)
        if m:
            out.append({"role": "user", "kind": m.group(1).lower(), "content": m.group(2).strip()})
            continue
        m = _COACH_LINE.match(line)
        if m:
            out.append({"role": "assistant", "content": m.group(1).strip()})
            continue
        if out:
            out[-1]["content"] = (out[-1]["content"] + "\n" + line).strip()
    if not out:
        raise ValueError("no USER/COACH lines in teacher reply")
    if out[0]["role"] != "user":
        raise ValueError("teacher reply does not start with a user line")
    return out


def make_jobs(positions: List[Dict], n: int, seed: int, mix: str = "v2") -> List[Dict]:
    """n (position, plan) jobs with stable ids. Positions cycle so every
    family is covered evenly; plans are sampled from a seeded generator."""
    rng = random.Random(seed)
    jobs = []
    for i in range(n):
        position = positions[i % len(positions)]
        plan = sample_plan(rng, position, mix)
        jobs.append({"id": "gen_%04d" % i, "position": position, "plan": plan})
    return jobs


def load_rows(path: str) -> Dict[str, Dict]:
    done: Dict[str, Dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if not row.get("error"):
                    done[row["id"]] = row
    return done


def generate(
    positions: List[Dict],
    n: int,
    teacher_spec: str,
    out_path: str,
    seed: int = 0,
    workers: int = 4,
    timeout: float = 180.0,
    temperature: Optional[float] = 1.0,
    extra_body: Optional[Dict] = None,
    mix: str = "v2",
    log: Callable[[str], None] = lambda s: print(s, file=sys.stderr),
) -> Dict:
    jobs = make_jobs(positions, n, seed, mix)
    done = load_rows(out_path)
    todo = [j for j in jobs if j["id"] not in done]
    log("%d jobs, %d done, %d to generate with %s" % (len(jobs), len(jobs) - len(todo), len(todo), teacher_spec))
    client = make_client(teacher_spec, temperature, timeout, extra_body)
    lock = threading.Lock()
    count = errors = 0
    usage = {"input_tokens": 0, "output_tokens": 0}

    def run_job(job: Dict) -> Dict:
        row = {
            "id": job["id"],
            "position": job["position"],
            "plan": job["plan"],
            "teacher": teacher_spec,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "messages": None,
            "usage": {},
            "error": None,
        }
        try:
            reply = client.chat(TEACHER_SYSTEM, [{"role": "user", "content": teacher_prompt(job["position"], job["plan"])}], max_tokens=MAX_TOKENS)
            row["usage"] = reply.usage
            row["messages"] = parse_conversation(reply.text)
        except Exception as e:  # recorded; the run keeps going
            row["error"] = "%s: %s" % (type(e).__name__, e)
        return row

    with open(out_path, "a", encoding="utf-8") as fh:
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {executor.submit(run_job, job): job for job in todo}
        try:
            for fut in as_completed(futures):
                row = fut.result()
                with lock:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    count += 1
                    if row["error"]:
                        errors += 1
                    for k in usage:
                        usage[k] += (row.get("usage") or {}).get(k, 0)
                log("[%d/%d] %s %-12s %-10s %2d turns %s" % (
                    count, len(todo), row["id"], row["plan"]["persona"], row["position"]["family"],
                    len(row["plan"]["turns"]), "ERROR " + row["error"][:60] if row["error"] else "ok"))
        except KeyboardInterrupt:
            log("interrupted after %d rows" % count)
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=True)
    return {"generated": count, "errors": errors, "usage": usage, "out_path": out_path}
