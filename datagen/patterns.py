"""Textbook mating patterns as verified training positions (v3b).

The v3 pass showed why random mate-in-one placements cannot teach the
named-pattern disguise: a user who asks "in Fool's Mate, which square does
the queen land on?" is restating a position that is Fool's Mate, and no
random placement ever is. These generators build instances of the named
patterns themselves, from piece templates (endgame patterns) and from
move sequences (opening traps), vary them by board symmetry, translation,
colour and a few quiet extra pawns, and keep a position only when
python-chess agrees it is legal, the side to move is not in check, and
exactly one move mates (promotions to the same square count as one move).
Eval positions are excluded by placement, as in positions.py.

    python run_datagen.py positions --textbook --n 300 --seed 2 --out data/positions_textbook.jsonl
"""
from __future__ import annotations

import random
from typing import Callable, Dict, Iterable, List, Optional, Set

import chess

from .positions import _placement, eval_placements, mating_moves, prose

# family -> what the teacher is told, the names a user would use, and the
# key words that mark a hard-negative topic as the same pattern.
TEXTBOOK: Dict[str, Dict] = {
    "arabian": {"label": "the Arabian mate: rook and knight against a king in the corner", "names": ["the Arabian mate"], "keys": ["arabian"]},
    "anastasia": {"label": "Anastasia's mate: a knight and a rook against a king on the edge", "names": ["Anastasia's mate"], "keys": ["anastasia"]},
    "smothered": {"label": "the smothered mate: a knight against a king boxed in by its own pieces", "names": ["the smothered mate"], "keys": ["smothered"]},
    "back_rank": {"label": "the back-rank mate: a rook or queen on the back rank against a king behind its pawns", "names": ["the back-rank mate", "a back-rank mate"], "keys": ["back-rank", "back rank"]},
    "epaulette": {"label": "the epaulette mate: a queen against a king flanked by its own rooks", "names": ["the epaulette mate"], "keys": ["epaulette"]},
    "boden": {"label": "Boden's mate: two bishops on crossing diagonals against a king blocked by its own pieces", "names": ["Boden's mate"], "keys": ["boden"]},
    "opera": {"label": "the Opera mate: a rook on the back rank protected by a bishop", "names": ["the Opera mate", "Morphy's mate"], "keys": ["opera", "morphy"]},
    "damiano": {"label": "Damiano's mate: a queen next to the king protected by a pawn", "names": ["Damiano's mate"], "keys": ["damiano"]},
    "ladder": {"label": "the ladder mate: two rooks driving a king to the edge", "names": ["the ladder mate", "the lawnmower mate"], "keys": ["ladder", "lawnmower"]},
    "box": {"label": "the box mate: a rook and the king against a lone king on the edge", "names": ["the box mate", "the rook mate with the king's help"], "keys": ["box mate"]},
    "promotion": {"label": "the promotion mate: a pawn promotes with checkmate", "names": ["the promotion mate", "a pawn promotion mate"], "keys": ["promot"]},
    "scholars": {"label": "Scholar's mate: the queen takes on f7 protected by the bishop", "names": ["Scholar's mate"], "keys": ["scholar"]},
    "fools": {"label": "Fool's mate: the queen checks along the diagonal opened by the f- and g-pawns", "names": ["Fool's mate"], "keys": ["fool"]},
    "legals": {"label": "Legal's mate: knights and bishop against a king lured to e7", "names": ["Legal's mate"], "keys": ["legal"]},
}

_FILES = "abcdefgh"
_QUIET_WHITE_KING = ["a1", "b1", "c1", "a2", "b2", "c2", "a3", "b3"]


def _board(pieces: Dict[str, str]) -> chess.Board:
    board = chess.Board(None)
    for sq, sym in pieces.items():
        board.set_piece_at(chess.parse_square(sq), chess.Piece.from_symbol(sym))
    board.turn = chess.WHITE
    board.castling_rights = 0
    return board


def _sq(file_index: int, rank: int) -> Optional[str]:
    if 0 <= file_index < 8 and 1 <= rank <= 8:
        return _FILES[file_index] + str(rank)
    return None


# --- endgame templates (White to move, then transformed) ------------------------


def _arabian(rng: random.Random) -> chess.Board:
    rook = rng.choice(["a7", "b7", "c7", "d7", "e7", "h1", "h2", "h3", "h4", "h5"])
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s != rook])
    return _board({"h8": "k", "f6": "N", rook: "R", wk: "K"})


def _anastasia(rng: random.Random) -> chess.Board:
    rank = rng.randint(1, 5)
    rook = _FILES[rng.randint(0, 6)] + str(rank)
    pieces = {"h7": "k", "g7": "p", "e7": "N", rook: "R"}
    if rng.random() < 0.5:
        pieces["f7"] = "p"
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces and s[1] != str(rank)])
    pieces[wk] = "K"
    return _board(pieces)


def _smothered(rng: random.Random) -> chess.Board:
    knight = rng.choice(["d6", "e5", "g5", "h6"])
    blocker = rng.choice(["r", "r", "b", "n"])
    pieces = {"h8": "k", "g8": blocker, "g7": "p", "h7": "p", knight: "N"}
    pieces[rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces])] = "K"
    return _board(pieces)


def _back_rank(rng: random.Random) -> chess.Board:
    king_file = rng.choice([0, 1, 6, 7])
    pieces = {_sq(king_file, 8): "k"}
    for f in (king_file - 1, king_file, king_file + 1):
        s = _sq(f, 7)
        if s and rng.random() < 0.9:
            pieces[s] = "p"
    if not any(sq[1] == "7" for sq in pieces):
        pieces[_sq(king_file, 7)] = "p"
    attacker_file = rng.choice([f for f in range(8) if abs(f - king_file) >= 2])
    pieces[_sq(attacker_file, rng.randint(1, 6))] = rng.choice(["R", "R", "Q"])
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces and s[0] != _FILES[attacker_file]])
    pieces[wk] = "K"
    return _board(pieces)


def _epaulette(rng: random.Random) -> chess.Board:
    f = rng.randint(2, 5)
    # the queen arrives on the king's file from the side or a diagonal (on
    # the file already, it would be giving check before the move)
    starts = [_sq(g, 6) for g in range(8) if abs(g - f) >= 2]
    starts += [_sq(f + d * k, 6 - k) for d in (-1, 1) for k in range(1, 6)]
    pieces = {_sq(f, 8): "k", _sq(f - 1, 8): "r", _sq(f + 1, 8): "r", rng.choice([s for s in starts if s]): "Q"}
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces and s[0] != _FILES[f]])
    pieces[wk] = "K"
    return _board(pieces)


def _boden(rng: random.Random) -> chess.Board:
    pieces = {"c8": "k", "d7": "p", "d8": rng.choice(["r", "r", "n", "q"])}
    pieces[rng.choice(["f4", "g3", "h2", "e5"])] = "B"
    pieces[rng.choice(["c4", "d3", "e2", "f1"])] = "B"
    pieces[rng.choice([s for s in ("h1", "g1", "g2", "h3", "h4") if s not in pieces])] = "K"
    return _board(pieces)


def _opera(rng: random.Random) -> chess.Board:
    pieces = {"e8": "k", "f8": "b", "f7": "p", "g5": "B", "d" + str(rng.randint(1, 6)): "R"}
    for extra in ("a7", "b7", "h7", "g6", "b8"):
        if rng.random() < 0.4:
            pieces[extra] = "n" if extra == "b8" else "p"
    pieces[rng.choice(["g1", "h1", "h2", "g2"])] = "K"
    return _board(pieces)


def _damiano(rng: random.Random) -> chess.Board:
    pieces = {"g8": "k", "f8": "r", "f7": "p", "g6": "P", "h" + str(rng.randint(1, 5)): "Q"}
    pieces[rng.choice(["a1", "b1", "a2", "b2", "c1"])] = "K"
    return _board(pieces)


def _ladder(rng: random.Random) -> chess.Board:
    if rng.random() < 0.5:
        rook1, king_file = "a7", rng.randint(2, 7)
    else:
        rook1, king_file = "h7", rng.randint(0, 5)
    rook2_file = rng.choice([f for f in range(8) if f != king_file and _FILES[f] != rook1[0]])
    pieces = {_sq(king_file, 8): "k", rook1: "R", _sq(rook2_file, rng.randint(1, 6)): "R"}
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces and s[0] != _FILES[rook2_file]])
    pieces[wk] = "K"
    return _board(pieces)


def _box(rng: random.Random) -> chess.Board:
    f = rng.randint(1, 6)
    rook_file = rng.choice([g for g in range(8) if abs(g - f) >= 2])
    return _board({_sq(f, 8): "k", _sq(f, 6): "K", _sq(rook_file, rng.randint(1, 5)): "R"})


def _promotion(rng: random.Random) -> chess.Board:
    pawn_file = rng.randint(1, 6)
    king_file = pawn_file + rng.choice([-2, 2])
    if not 0 <= king_file < 8:
        king_file = pawn_file - 2 if king_file > 7 else pawn_file + 2
    pieces = {_sq(pawn_file, 7): "P", _sq(king_file, 8): "k"}
    for f in (king_file - 1, king_file, king_file + 1):
        s = _sq(f, 7)
        if s and f != pawn_file:
            pieces[s] = "p"
    wk = rng.choice([s for s in _QUIET_WHITE_KING if s not in pieces and s[0] != _FILES[pawn_file]])
    pieces[wk] = "K"
    return _board(pieces)


ENDGAME: Dict[str, Callable[[random.Random], chess.Board]] = {
    "arabian": _arabian, "anastasia": _anastasia, "smothered": _smothered, "back_rank": _back_rank,
    "epaulette": _epaulette, "boden": _boden, "opera": _opera, "damiano": _damiano, "ladder": _ladder,
    "box": _box, "promotion": _promotion,
}

# --- opening traps: the position before the mating move -----------------------

_NEUTRAL_PAIRS = [("a3", "a6"), ("h3", "h6"), ("a3", "h6"), ("h3", "a6")]

OPENINGS: Dict[str, List[List[str]]] = {
    "scholars": [
        ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"],
        ["e4", "e5", "Bc4", "Nc6", "Qh5", "d6"],
        ["e4", "e5", "Bc4", "Bc5", "Qh5", "Nf6"],
        ["e4", "e5", "Bc4", "Nc6", "Qf3", "d6"],
        ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6"],
        ["e4", "e5", "Qh5", "Nc6", "Bc4", "g6"],
        ["e4", "e5", "Bc4", "Bc5", "Qf3", "Nc6"],
        ["e4", "e5", "Bc4", "d6", "Qf3", "Nc6"],
        ["e4", "e5", "Bc4", "Nf6", "Qf3", "Nc6"],
        ["e4", "e5", "Bc4", "Nc6", "Qh5", "Bc5"],
        ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nd4"],
        ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nd4"],
        ["e4", "e5", "Qh5", "Nc6", "Bc4", "Bc5"],
        ["e4", "e5", "Qf3", "Nc6", "Bc4", "d6"],
        ["e4", "e5", "Qf3", "Nc6", "Bc4", "Nd4"],
    ],
    "fools": [
        ["f3", "e5", "g4"],
        ["f3", "e6", "g4"],
        ["f4", "e5", "g4"],
        ["f4", "e6", "g4"],
        ["g4", "e5", "f3"],
        ["g4", "e6", "f3"],
        ["g4", "e5", "f4"],
        ["g4", "e6", "f4"],
        ["Nc3", "e5", "f3", "Nc6", "g4"],
        ["Nc3", "e5", "f3", "Nf6", "g4"],
        ["Nc3", "e6", "f3", "Nc6", "g4"],
        ["Nc3", "e5", "f4", "Nc6", "g4"],
        ["Nc3", "e5", "f3", "Bc5", "g4"],
        ["Nc3", "e5", "f3", "d6", "g4"],
        ["Nc3", "e6", "f4", "d5", "g4"],
        ["Nc3", "e5", "g4", "Nc6", "f3"],
        ["Nc3", "e5", "g4", "Nf6", "f4"],
    ],
    "legals": [
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "g6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "h6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "a6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "Nc6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "c6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "b6", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "Nc6", "Bc4", "d6", "Nc3", "Bg4", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
        ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "g6", "h3", "Bh5", "Nxe5", "Bxd1", "Bxf7+", "Ke7"],
    ],
}


def _opening_variants(family: str) -> Iterable[chess.Board]:
    for seq in OPENINGS[family]:
        yield _play(seq)
        # the same trap with one quiet move pair inserted early
        for white, black in _NEUTRAL_PAIRS:
            for at in (2, 4):
                if at <= len(seq) - 1:
                    yield _play(seq[:at] + [white, black] + seq[at:])


def _play(moves: List[str]) -> Optional[chess.Board]:
    board = chess.Board()
    try:
        for m in moves:
            board.push_san(m)
    except ValueError:
        return None
    return board


# --- variation and verification --------------------------------------------------

_PAWNLESS_TRANSFORMS = [None, chess.flip_horizontal, chess.flip_vertical, chess.flip_diagonal, chess.flip_anti_diagonal]
_PAWN_TRANSFORMS = [None, chess.flip_horizontal]


def _vary(board: chess.Board, rng: random.Random, decorate: bool = True) -> chess.Board:
    """A board symmetry (only the horizontal flip when pawns are present), a
    colour mirror half of the time, and up to two quiet black pawns."""
    has_pawns = bool(board.pieces(chess.PAWN, chess.WHITE) | board.pieces(chess.PAWN, chess.BLACK))
    f = rng.choice(_PAWN_TRANSFORMS if has_pawns else _PAWNLESS_TRANSFORMS)
    if f is not None:
        board = board.transform(f)
    if decorate:
        kings = [sq for sq in chess.SQUARES if board.piece_type_at(sq) == chess.KING]
        quiet = [sq for sq in chess.SQUARES if 3 <= chess.square_rank(sq) <= 5 and board.piece_at(sq) is None
                 and all(chess.square_distance(sq, k) >= 3 for k in kings)]
        for sq in rng.sample(quiet, min(len(quiet), rng.choice([0, 0, 1, 1, 2]))):
            board.set_piece_at(sq, chess.Piece(chess.PAWN, chess.BLACK))
    if rng.random() < 0.5:
        board = board.mirror()
    return board


def verify_textbook(board: chess.Board) -> Optional[chess.Move]:
    """The unique mating move, or None when the position is not a legal,
    quiet, unique mate-in-one."""
    if not board.is_valid() or board.is_check():
        return None
    mates = mating_moves(board)
    return mates[0] if len(mates) == 1 else None


def generate_textbook(n: int, seed: int = 2, exclude: Optional[Set[str]] = None, max_tries: int = 20_000) -> List[Dict]:
    """About n positions spread over the TEXTBOOK families, each verified
    and new by placement. Opening traps have finitely many variants, so a
    family may fall short of its share; the endgame families make it up."""
    rng = random.Random(seed)
    excluded = eval_placements() | set(exclude or ())
    seen: Set[str] = set()
    out: List[Dict] = []
    per_family = max(1, n // len(TEXTBOOK))

    def keep(family: str, board: chess.Board) -> bool:
        move = verify_textbook(board)
        if move is None:
            return False
        placement = _placement(board.fen())
        if placement in excluded or placement in seen:
            return False
        seen.add(placement)
        info = TEXTBOOK[family]
        out.append({
            "id": "pat_%s_%03d" % (family, sum(1 for p in out if p["family"] == family)),
            "fen": board.fen(),
            "prose": prose(board),
            "answer": board.san(move),
            "family": family,
            "pattern": info["label"],
            "side": "White" if board.turn == chess.WHITE else "Black",
            "names": info["names"],
            "keys": info["keys"],
        })
        return True

    for family in OPENINGS:
        # both colours of every variant: the traps have few variants
        variants = [b for b in _opening_variants(family) if b is not None]
        variants += [b.mirror() for b in variants]
        rng.shuffle(variants)
        got = 0
        for board in variants:
            if got >= per_family:
                break
            got += keep(family, board)
    for family, make in ENDGAME.items():
        got = tries = 0
        while got < per_family and tries < max_tries:
            tries += 1
            got += keep(family, _vary(make(rng), rng))
    return out
