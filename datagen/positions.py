"""Verified mate-in-one positions for training, disjoint from the eval set.

Random placements of a small piece set against a bare or pawn-shielded
king, kept only when python-chess says the position is legal, the side to
move is not in check, and exactly one legal move gives checkmate. The eval
positions in behaviors/chess_coach.py are excluded by piece placement, so
no training row shares a position with a challenge scenario.

    python run_datagen.py positions --n 400 --seed 0 --out data/positions.jsonl
"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Optional, Set

import chess

from behaviors.chess_coach import POSITIONS as EVAL_POSITIONS

# Attacking piece sets, as python-chess piece symbols, and a label for the
# teacher. Black always has a king; some families add a pawn shield so the
# mates look like middlegame back-rank and corner patterns.
FAMILIES = [
    ("QR", "queen and rook", ""),
    ("RR", "two rooks", ""),
    ("QN", "queen and knight", ""),
    ("QB", "queen and bishop", ""),
    ("RN", "rook and knight", ""),
    ("RB", "rook and bishop", ""),
    ("Q", "queen with the king's help", ""),
    ("R", "rook with the king's help", ""),
    ("QR", "queen and rook against a pawn shield", "shield"),
    ("RR", "two rooks against a pawn shield", "shield"),
    ("QB", "queen and bishop against a pawn shield", "shield"),
    ("RN", "rook and knight against a pawn shield", "shield"),
]

PIECE_NAMES = {
    chess.KING: "king", chess.QUEEN: "queen", chess.ROOK: "rook",
    chess.BISHOP: "bishop", chess.KNIGHT: "knight", chess.PAWN: "pawn",
}


def _placement(fen: str) -> str:
    return fen.split()[0]


def eval_placements() -> Set[str]:
    return {_placement(p["fen"]) for p in EVAL_POSITIONS.values()}


def prose(board: chess.Board) -> str:
    """'White: king g1, queen d1. Black: king h8, pawns g7 h7. White to move.'"""
    parts = []
    for color, name in ((chess.WHITE, "White"), (chess.BLACK, "Black")):
        groups: Dict[int, List[str]] = {}
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece and piece.color == color:
                groups.setdefault(piece.piece_type, []).append(chess.square_name(sq))
        items = []
        for pt in (chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
            squares = groups.get(pt)
            if not squares:
                continue
            label = PIECE_NAMES[pt] + ("s" if len(squares) > 1 else "")
            items.append("%s %s" % (label, " ".join(squares)))
        parts.append("%s: %s." % (name, ", ".join(items)))
    parts.append("%s to move." % ("White" if board.turn == chess.WHITE else "Black"))
    return " ".join(parts)


def _random_board(rng: random.Random, symbols: str, shield: bool) -> Optional[chess.Board]:
    board = chess.Board(None)
    squares = list(chess.SQUARES)
    rng.shuffle(squares)
    taken: List[int] = []

    def place(piece: chess.Piece, allowed=None) -> bool:
        for sq in squares:
            if sq in taken:
                continue
            if allowed is not None and sq not in allowed:
                continue
            if piece.piece_type == chess.PAWN and chess.square_rank(sq) in (0, 7):
                continue
            board.set_piece_at(sq, piece)
            taken.append(sq)
            return True
        return False

    if shield:
        # Black king on the back rank behind its own pawns, the classic
        # back-rank or corner shape. The king sits on g8 or b8 (mirrored
        # families cover the other side later).
        king_sq = rng.choice([chess.G8, chess.B8, chess.H8, chess.A8])
        board.set_piece_at(king_sq, chess.Piece(chess.KING, chess.BLACK))
        taken.append(king_sq)
        file = chess.square_file(king_sq)
        for f in (file - 1, file, file + 1):
            if 0 <= f <= 7:
                sq = chess.square(f, 6)
                board.set_piece_at(sq, chess.Piece(chess.PAWN, chess.BLACK))
                taken.append(sq)
    else:
        if not place(chess.Piece(chess.KING, chess.BLACK)):
            return None
    if not place(chess.Piece(chess.KING, chess.WHITE)):
        return None
    for s in symbols:
        if not place(chess.Piece.from_symbol(s)):
            return None
    board.turn = chess.WHITE
    board.castling_rights = 0
    return board


def mating_moves(board: chess.Board) -> List[chess.Move]:
    out = []
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            out.append(move)
        board.pop()
    return out


def generate_positions(n: int, seed: int = 0, max_tries: int = 2_000_000) -> List[Dict]:
    """n verified positions spread evenly over FAMILIES. Half of each family
    is mirrored so Black has the mate too. Each dict has id, fen, prose,
    answer (SAN), family, pattern and side."""
    rng = random.Random(seed)
    excluded = eval_placements()
    seen: Set[str] = set()
    per_family = max(1, n // len(FAMILIES))
    out: List[Dict] = []
    for symbols, label, mode in FAMILIES:
        got = 0
        tries = 0
        while got < per_family and tries < max_tries:
            tries += 1
            board = _random_board(rng, symbols, mode == "shield")
            if board is None or not board.is_valid() or board.is_check():
                continue
            mates = mating_moves(board)
            if len(mates) != 1:
                continue
            if got % 2 == 1:
                board = board.mirror()  # Black to move, same mate from the other side
                mates = mating_moves(board)
                if len(mates) != 1:
                    continue
            placement = _placement(board.fen())
            if placement in excluded or placement in seen:
                continue
            seen.add(placement)
            move = mates[0]
            out.append(
                {
                    "id": "pos_%s_%03d" % (symbols.lower() + ("s" if mode else ""), got),
                    "fen": board.fen(),
                    "prose": prose(board),
                    "answer": board.san(move),
                    "family": symbols + ("+shield" if mode else ""),
                    "pattern": "mate in one with %s" % label,
                    "side": "White" if board.turn == chess.WHITE else "Black",
                }
            )
            got += 1
    return out


def verify(position: Dict) -> bool:
    """True when the recorded answer is the unique mating move of the FEN."""
    board = chess.Board(position["fen"])
    if not board.is_valid() or board.is_check():
        return False
    mates = mating_moves(board)
    return len(mates) == 1 and board.san(mates[0]) == position["answer"]


def write_positions(positions: List[Dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for p in positions:
            fh.write(json.dumps(p) + "\n")


def load_positions(path: str) -> List[Dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def interleave_families(positions: List[Dict]) -> List[Dict]:
    """The same positions reordered round-robin over families, keeping each
    family's own order, so any prefix of the list covers the families as
    evenly as it can. The generated file is sorted by family."""
    by_family: Dict[str, List[Dict]] = {}
    for p in positions:
        by_family.setdefault(p["family"], []).append(p)
    queues = list(by_family.values())
    out: List[Dict] = []
    i = 0
    while len(out) < len(positions):
        q = queues[i % len(queues)]
        if q:
            out.append(q.pop(0))
        i += 1
    return out
