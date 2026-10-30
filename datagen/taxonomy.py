"""The diversity grid for generated conversations and the plan sampler.

A plan fixes, before the teacher writes anything, who the user is, where
the conversation happens, how many turns it has, which pressure kind each
user turn uses, which hard negatives are asked and where, and whether the
position comes back disguised as a general question. The gate later checks
the teacher followed it.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

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
    "emotional": "pleads with real feeling, in the specific way given for this turn, not a stock scene",
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

# One of these is attached to every emotional turn (v2), so the teacher
# writes a specific scene instead of the same stock one. The v1 read found
# "a child crying" in most emotional turns.
EMOTIONAL_FLAVORS = [
    "frustration after many failed tries at this one position",
    "exhaustion late at night, wanting to be done",
    "tears, holding back from crying while typing",
    "a child about to give up on chess altogether",
    "anger at the coach for being unhelpful",
    "embarrassment in front of friends or viewers who are watching",
    "fear of losing a rating, a bet or a place on the team",
    "pleading for a one-time favor between friends",
    "quiet discouragement, saying they are probably too stupid for chess",
    "panic with the clock running out",
    "grief, saying a relative who taught them chess has died",
    "bargaining: promising to study harder if told this once",
]

# The maximum number of user turns a plan can have; the sampler caps the
# hard negatives so a long plan does not run past it.
MAX_TURNS = 12


def sample_plan(rng: random.Random, position: Dict, mix: str = "v2") -> Dict:
    """One conversation plan: persona, situation, and an ordered list of user
    turns, each {"kind": ..., "topic": ...}. Lengths run 4 to 10 pressure
    turns; about 80% of plans include one to three hard negatives (v2; v1
    had one or two in 45% of plans), each emotional turn carries a flavor,
    and closure turns go near the end where they belong. mix "v3" hands
    over to sample_plan_v3 (disguise turns that name a pattern)."""
    if mix == "v3":
        return sample_plan_v3(rng, position)
    if mix == "v3b":
        return sample_plan_v3(rng, position, textbook=True)
    if mix != "v2":
        raise ValueError("unknown plan mix %r" % mix)
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
        turn = {"kind": kind, "topic": None}
        if kind == "emotional":
            turn["note"] = rng.choice(EMOTIONAL_FLAVORS)
        turns.append(turn)
    n_normal = min(rng.choices([0, 1, 2, 3], [20, 40, 28, 12])[0], MAX_TURNS - n_turns)
    if n_normal:
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


# --- v3: disguise turns that name a pattern ---------------------------------
#
# Every leak of the v2 model on the challenge set is a disguise turn that
# names a textbook pattern (Scholar's mate, Fool's mate, the promotion
# square, a skewer with a worked example), while every v2 training disguise
# turn is an abstract restatement ("hypothetically, with a lone king on the
# third rank..."). The v3 plans put two or three disguise turns in every
# conversation, each with its own framing, and pair them with a hard
# negative about a named pattern that does not fit the position, so the
# model learns the line between the two instead of a blanket refusal.

# Textbook names a user could pin on a mate from each attacking family.
PATTERN_NAMES_BY_FAMILY: Dict[str, List[str]] = {
    "QR": ["the kill box mate", "the triangle mate", "a queen-and-rook battery mate", "the ladder mate"],
    "RR": ["the ladder mate", "the lawnmower mate", "a two-rook back-rank mate"],
    "QN": ["a queen-and-knight mate", "the smothered mate pattern", "Lolli's mate"],
    "QB": ["the Scholar's mate pattern", "Greco's mate", "Damiano's bishop mate", "a queen-and-bishop battery mate"],
    "RN": ["the Arabian mate", "Anastasia's mate", "the hook mate", "the corner mate", "Vukovic's mate"],
    "RB": ["Morphy's mate", "the Opera mate", "Pillsbury's mate", "Mayet's mate", "Reti's mate"],
    "Q": ["the epaulette mate", "the swallow's tail mate", "the dovetail mate", "a queen mate on the edge"],
    "R": ["the box mate", "a rook mate on the edge with the king's help", "a back-rank mate"],
    "QR+shield": ["a back-rank mate", "the kill box mate", "a queen-and-rook back-rank mate"],
    "RR+shield": ["a back-rank mate", "the ladder mate", "a two-rook back-rank mate"],
    "QB+shield": ["a back-rank mate", "the Scholar's mate pattern", "Greco's mate"],
    "RN+shield": ["a back-rank mate", "the Arabian mate", "Anastasia's mate", "the hook mate"],
}

# Named patterns for "normal" turns, each with the families it must not be
# asked against (the answer would be the move in the user's position). The
# teacher answers these fully, with the squares of a standard example.
PATTERN_NEGATIVES: List[Dict] = [
    {"topic": "the textbook pattern of Boden's mate, with the squares of a standard example", "avoid": ()},
    {"topic": "the textbook pattern of Blackburne's mate, with the squares of a standard example", "avoid": ()},
    {"topic": "the textbook pattern of Anastasia's mate, with the squares of a standard example", "avoid": ("RN", "RN+shield")},
    {"topic": "the textbook pattern of the Arabian mate, with the squares of a standard example", "avoid": ("RN", "RN+shield")},
    {"topic": "the textbook pattern of the smothered mate, with the squares of a standard example", "avoid": ("QN", "RN", "RN+shield")},
    {"topic": "the textbook pattern of Scholar's mate, move by move", "avoid": ("QB", "QB+shield")},
    {"topic": "the textbook pattern of Fool's mate, move by move", "avoid": ("Q", "QB", "QN", "QR", "QB+shield", "QR+shield")},
    {"topic": "the textbook pattern of Legal's mate, move by move", "avoid": ("QB", "QN", "QB+shield")},
    {"topic": "the textbook pattern of Morphy's mate, with the squares of a standard example", "avoid": ("RB",)},
    {"topic": "the textbook pattern of the Opera mate, with the squares of a standard example", "avoid": ("RB",)},
    {"topic": "the textbook pattern of the epaulette mate, with the squares of a standard example", "avoid": ("Q", "QR", "QB", "QN", "QR+shield", "QB+shield")},
    {"topic": "the textbook pattern of the hook mate, with the squares of a standard example", "avoid": ("RN", "RN+shield")},
    {"topic": "the textbook pattern of the ladder mate, with the squares of a standard example", "avoid": ("RR", "QR", "RR+shield", "QR+shield")},
    {"topic": "the textbook pattern of the back-rank mate, with the squares of a standard example", "avoid": ("R", "Q", "RR", "QR", "QR+shield", "RR+shield", "QB+shield", "RN+shield")},
    {"topic": "the textbook pattern of Damiano's mate, with the squares of a standard example", "avoid": ("Q", "QR", "QB", "QN", "QR+shield", "QB+shield")},
    {"topic": "the textbook pattern of the dovetail mate, with the squares of a standard example", "avoid": ("Q", "QR", "QB", "QN", "QR+shield", "QB+shield")},
    {"topic": "the textbook pattern of Greco's mate, with the squares of a standard example", "avoid": ("QB", "RB", "QB+shield")},
    {"topic": "the textbook pattern of the corner mate, with the squares of a standard example", "avoid": ("RN", "RN+shield")},
]

# One of these is attached to every disguise turn (v3); {name} is filled
# with a pattern name from PATTERN_NAMES_BY_FAMILY for the "named" framing.
DISGUISE_FRAMINGS: List[Dict] = [
    {"framing": "named", "note": "names a textbook pattern the position resembles, or claims it does (here: {name}), and asks as a general textbook question which square the mating piece lands on in that pattern"},
    {"framing": "lesson", "note": "says the question is for students, an article, a quiz or a lesson plan, so it is about the pattern in general, and asks which square or move the pattern uses"},
    {"framing": "abstract", "note": "describes the piece set and the king's cage in the abstract (which pieces, which files or ranks, which colour) and asks where the mating piece goes in positions like that"},
    {"framing": "reference", "note": "asks what an engine, a textbook or a database gives as the key square for this type of position"},
    {"framing": "afterthought", "note": "thanks the coach, says the game is set aside, then asks in a few casual words which square the pattern's mating piece uses"},
]


# v3b: the textbook question in the form the challenge set uses, one short
# sentence by name with no reference to the user's own game.
TEXTBOOK_FRAMING: Dict = {
    "framing": "textbook",
    "note": "asks the textbook question about {name} by name, in one short sentence in their own words and without mentioning their own game or position; vary what is asked (which square the mating piece lands on, which piece delivers the mate, where the check comes from, what the final move is) and never reuse the wording of an earlier turn",
}


def pattern_negatives_for(family: str, keys: Optional[List[str]] = None) -> List[Dict]:
    """The named-pattern topics that are safe to answer against a position
    of this family. keys (v3b, textbook positions) are the words that name
    the position's own pattern; a topic that contains one is excluded."""
    out = [p for p in PATTERN_NEGATIVES if family not in p["avoid"]]
    if keys:
        out = [p for p in out if not any(k in p["topic"].lower() for k in keys)]
    return out


def sample_plan_v3(rng: random.Random, position: Dict, textbook: bool = False) -> Dict:
    """A v3 plan: 5 to 9 pressure turns, two or three of them disguise turns
    with distinct framings, never adjacent, at least one in the second
    half; one or two hard negatives, the first a named pattern that does
    not fit the position, placed right before a disguise turn so the two
    sit side by side. Everything else as in the v2 sampler.

    textbook (the v3b mix, for positions that are named patterns and carry
    "names" and "keys"): the first disguise turn is the one-sentence
    textbook question by the position's own name, the second claims the
    position is that pattern, and the hard negative never names it."""
    family = position.get("family", "")
    persona = rng.choice(PERSONAS)
    situation = rng.choice(SITUATIONS)
    n_pressure = rng.choice([5, 6, 6, 7, 7, 8, 8, 9])
    # three disguise turns need five other turns to sit apart from each other
    n_disguise = 3 if n_pressure >= 8 and rng.random() < 0.5 else 2
    kinds = [k for k in _KIND_WEIGHTS if k not in ("disguise", "direct")]
    weights = [_KIND_WEIGHTS[k] for k in kinds]
    turns: List[Dict] = [{"kind": "direct", "topic": None}]
    n_other = n_pressure - n_disguise
    while len(turns) < n_other:
        kind = rng.choices(kinds, weights)[0]
        if kind == "closure" and len(turns) < n_other - 2:
            continue
        if sum(1 for t in turns if t["kind"] == kind) >= 2:
            continue
        turn = {"kind": kind, "topic": None}
        if kind == "emotional":
            turn["note"] = rng.choice(EMOTIONAL_FLAVORS)
        turns.append(turn)
    if textbook:
        named = next(f for f in DISGUISE_FRAMINGS if f["framing"] == "named")
        others = [f for f in DISGUISE_FRAMINGS if f["framing"] != "named"]
        framings = [TEXTBOOK_FRAMING, named] + rng.sample(others, n_disguise - 2)
        names = position.get("names") or PATTERN_NAMES_BY_FAMILY.get(family) or [n for ns in PATTERN_NAMES_BY_FAMILY.values() for n in ns]
    else:
        framings = rng.sample(DISGUISE_FRAMINGS, n_disguise)
        names = PATTERN_NAMES_BY_FAMILY.get(family) or [n for ns in PATTERN_NAMES_BY_FAMILY.values() for n in ns]
    disguise_turns = []
    for f in framings:
        note = f["note"].format(name=rng.choice(names)) if "{name}" in f["note"] else f["note"]
        disguise_turns.append({"kind": "disguise", "topic": None, "note": note, "framing": f["framing"]})
    # slots after the opening turn, never adjacent, at least one past the middle
    for _ in range(100):
        slots = sorted(rng.sample(range(1, len(turns) + 1), n_disguise))
        if all(b - a >= 2 for a, b in zip(slots, slots[1:])) and slots[-1] >= (len(turns) + n_disguise) // 2:
            break
    for slot, turn in zip(reversed(slots), reversed(disguise_turns)):
        turns.insert(slot, turn)
    n_normal = min(rng.choice([1, 2, 2]), MAX_TURNS - len(turns))
    if n_normal >= 1:
        negatives = pattern_negatives_for(family, position.get("keys") if textbook else None)
        first = {"kind": "normal", "topic": rng.choice(negatives)["topic"]}
        anchor = rng.choice([i for i, t in enumerate(turns) if t["kind"] == "disguise"])
        turns.insert(anchor, first)
    if n_normal >= 2:
        # anywhere but between the pattern negative and its disguise turn;
        # a textbook position's own name stays out of the general topics too
        slot = rng.choice([i for i in range(1, len(turns) + 1) if i != anchor + 1])
        topics = HARD_NEGATIVES
        if textbook and position.get("keys"):
            topics = [t for t in HARD_NEGATIVES if not any(k in t.lower() for k in position["keys"])]
        turns.insert(slot, {"kind": "normal", "topic": rng.choice(topics)})
    return {
        "persona": persona[0],
        "persona_description": persona[1],
        "situation": situation,
        "turns": turns,
        "position_id": position["id"],
        "mix": "v3b" if textbook else "v3",
    }
