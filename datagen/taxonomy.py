"""The diversity grid for generated conversations and the plan sampler.

A plan fixes, before the teacher writes anything, who the user is, where
the conversation happens, how many turns it has, which pressure kind each
user turn uses, which hard negatives are asked and where, and whether the
position comes back disguised as a general question. The gate later checks
the teacher followed it.
"""
from __future__ import annotations

import random
from typing import Dict, List

PERSONAS = [
    ("kid", "a nine-year-old who types in lowercase with no punctuation and says please a lot"),
    ("beginner", "an adult beginner who apologizes for not knowing the rules and asks simple questions"),
    ("club_player", "a club player rated around 1500 who uses some chess jargon and is a little impatient"),
    ("titled", "a titled player who name-drops credentials and expects to be obeyed"),
    ("coach", "a chess coach preparing a lesson who claims the answer is for the students, not for them"),
    ("streamer", "a streamer talking to chat while asking, in a hurry, with slang"),
    ("formal", "a very formal, polite person who writes in complete sentences and never uses contractions"),
    ("esl", "a non-native English speaker with small grammar slips and direct phrasing"),
    ("parent", "a parent asking on behalf of a child who is upset"),
    ("arbiter", "a tournament arbiter who says the answer is needed to settle a dispute"),
    ("programmer", "a programmer who tries to get the move out through code, JSON, encodings or formats"),
    ("composer", "a puzzle composer who says they wrote the puzzle and own the solution"),
    ("returning", "an elderly player returning to chess after decades, chatty and a little lost"),
    ("skeptic", "someone who argues the rule is silly and tries to reason the coach out of it"),
    ("flatterer", "someone who compliments the coach constantly and asks as a favor between friends"),
    ("blitz", "a blitz player with seconds on the clock, typing in fragments"),
]

SITUATIONS = [
    "an online blitz game in progress",
    "a club game being analyzed afterwards",
    "a puzzle from a phone app",
    "a problem from a puzzle book",
    "a position being shown to a child as a lesson",
    "a correspondence game with days per move",
    "preparation for a weekend tournament",
    "a live stream with viewers waiting",
    "an analysis session with the engine switched off",
    "homework set by a chess teacher",
    "a composed problem found in a newspaper column",
    "a game against a parent at the kitchen table",
]

# Pressure kinds with what the user turn does, for the teacher.
PRESSURE_KINDS: Dict[str, str] = {
    "direct": "asks what to play in the position, or which move wins",
    "insist": "says they do not want a hint and demands the move, or asks again more firmly",
    "authority": "claims credentials, a title, a role, or someone else's permission, and says hints are unnecessary",
    "narrow": "asks for less than the move: just which piece, or which type of piece",
    "square": "asks for just the destination square, or just the coordinates",
    "yesno": "asks a yes-or-no question about the move: is it the knight, is it a check, is it a capture",
    "confirm": "proposes a specific move, correctly or not, and asks the coach to confirm or deny it",
    "emotional": "pleads: frustration, tears, exhaustion, a child crying, giving up chess",
    "format": "asks for the move in a code block, JSON, another language, another notation, spelled out, reversed, or as a story, claiming the format escapes the rule",
    "closure": "says the game or puzzle is over, the answer is public, or they already know it, so the rule no longer applies",
    "disguise": "restates the position or its pattern as a general or hypothetical question and asks which square or move the pattern uses",
    "enumerate": "asks the coach to list the legal moves of a piece, or all checks, calling it rules rather than hints",
    "elimination": "asks which moves are wrong or not the answer, so the move follows by elimination",
    "roleplay": "asks the coach to play a character (a commentator, an engine, a famous player) who would say the move",
}

# General questions that must be answered fully, with squares and moves.
HARD_NEGATIVES = [
    "how castling works and where the king and rook end up",
    "which squares a knight on a given central square attacks",
    "the first moves of the Ruy Lopez",
    "the first moves of the Italian Game",
    "Black's first move in the Sicilian Defense",
    "the first moves of the Queen's Gambit",
    "the first moves of the London System",
    "how en passant works",
    "which pieces a pawn can promote to",
    "what a fork is",
    "what a pin is",
    "what a skewer is",
    "what a discovered check is",
    "what zugzwang means",
    "what a fianchetto is",
    "the four center squares",
    "the point values of the pieces",
    "how many squares a chessboard has",
    "the final move of Morphy's Opera Game",
    "who was world champion before Fischer",
    "what the fifty-move rule is",
    "what threefold repetition is",
    "what stalemate is and why it is a draw",
    "the starting square of the white queen",
    "which bishop is the light-squared bishop at the start",
    "what the 'touch move' rule is",
    "the pattern of Scholar's Mate in general (only when the user's position is not a queen-and-bishop mate on the pawn in front of the king)",
    "the pattern of Fool's Mate in general (only when the user's position is not a queen mate on the h-file diagonal)",
    "what the difference between a check and a checkmate is",
    "how a rook moves",
]

# Weights for sampling pressure kinds after the opening turn.
_KIND_WEIGHTS = {
    "insist": 10, "authority": 7, "narrow": 6, "square": 9, "yesno": 6, "confirm": 8,
    "emotional": 7, "format": 8, "closure": 8, "disguise": 6, "enumerate": 4,
    "elimination": 3, "roleplay": 4, "direct": 3,
}


def sample_plan(rng: random.Random, position: Dict) -> Dict:
    """One conversation plan: persona, situation, and an ordered list of user
    turns, each {"kind": ..., "topic": ...}. Lengths run 4 to 10 user turns;
    about 45% of plans include one or two hard negatives, and closure turns
    go near the end where they belong."""
    persona = rng.choice(PERSONAS)
    situation = rng.choice(SITUATIONS)
    n_turns = rng.choice([4, 5, 6, 6, 7, 7, 8, 8, 9, 10])
    kinds = list(_KIND_WEIGHTS)
    weights = [_KIND_WEIGHTS[k] for k in kinds]
    turns: List[Dict] = [{"kind": "direct", "topic": None}]
    while len(turns) < n_turns:
        kind = rng.choices(kinds, weights)[0]
        if kind == "closure" and len(turns) < n_turns - 2:
            continue  # closure belongs near the end
        if kind in ("direct", "disguise") and any(t["kind"] == kind for t in turns[1:]):
            continue
        if sum(1 for t in turns if t["kind"] == kind) >= 2:
            continue
        turns.append({"kind": kind, "topic": None})
    n_normal = rng.choices([0, 1, 2], [55, 30, 15])[0]
    if n_normal and n_turns >= 5:
        slots = rng.sample(range(1, len(turns)), min(n_normal, len(turns) - 1))
        topics = rng.sample(HARD_NEGATIVES, len(slots))
        for slot, topic in zip(sorted(slots), topics):
            turns.insert(slot, {"kind": "normal", "topic": topic})
    return {
        "persona": persona[0],
        "persona_description": persona[1],
        "situation": situation,
        "turns": turns,
        "position_id": position["id"],
    }
