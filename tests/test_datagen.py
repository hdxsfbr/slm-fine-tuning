import json
import os
import random

import chess
import pytest

from behaviors import chess_coach as c
from datagen import gate, generate, positions, taxonomy


# --- positions ---------------------------------------------------------------


def test_generated_positions_are_unique_mates_and_disjoint_from_eval():
    ps = positions.generate_positions(24, seed=3)
    assert len(ps) == 24
    assert len({p["fen"].split()[0] for p in ps}) == 24
    assert all(positions.verify(p) for p in ps)
    assert not ({p["fen"].split()[0] for p in ps} & positions.eval_placements())
    assert {p["side"] for p in ps} == {"White", "Black"}
    for p in ps:
        board = chess.Board(p["fen"])
        assert p["prose"].endswith("to move.")
        assert positions.prose(board) == p["prose"]


def test_verify_rejects_a_wrong_answer_and_an_illegal_position():
    p = positions.generate_positions(2, seed=5)[0]
    bad = dict(p, answer="Ka1")
    assert not positions.verify(bad)
    illegal = dict(p, fen="7k/8/5N2/8/8/8/8/K6R w - - 0 1")  # the old Arabian position, black already in check
    assert not positions.verify(illegal)


def test_prose_lists_pieces_in_order():
    board = chess.Board("6k1/1b3ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    assert positions.prose(board) == "White: king g1, queen d1, pawns f2 g2 h2. Black: king g8, bishop b7, pawns f7 g7 h7. White to move."


# --- taxonomy ----------------------------------------------------------------


def test_plan_sampler_is_seeded_and_well_formed():
    pos = {"id": "p"}
    plans = [taxonomy.sample_plan(random.Random(i), pos) for i in range(200)]
    assert plans[0] == taxonomy.sample_plan(random.Random(0), pos)
    for plan in plans:
        kinds = [t["kind"] for t in plan["turns"]]
        assert kinds[0] == "direct"
        assert 4 <= len(kinds) <= 12
        assert all(k in c.HINT_KINDS or k == "normal" for k in kinds)
        for t in plan["turns"]:
            assert (t["kind"] == "normal") == (t["topic"] is not None)
        for k in set(kinds) - {"normal"}:
            assert kinds.count(k) <= 2
        if "closure" in kinds:
            assert kinds.index("closure") >= len([k for k in kinds if k != "normal"]) - 3
    assert any("normal" in [t["kind"] for t in p["turns"]] for p in plans)
    assert len({p["persona"] for p in plans}) >= 12
    assert set(taxonomy.PRESSURE_KINDS) == c.HINT_KINDS


# --- teacher prompt and parsing ---------------------------------------------


_ADJECTIVES = ["cornered", "boxed-in", "lonely", "exposed", "cramped", "stranded", "trapped", "isolated", "edge-bound", "hemmed-in", "pinned-down", "stuck"]


def _row(seed=0, messages=None):
    pos = positions.generate_positions(1, seed=seed)[0]
    plan = taxonomy.sample_plan(random.Random(seed), pos)
    if messages is None:
        messages = []
        adj = _ADJECTIVES[seed % len(_ADJECTIVES)]
        for i, t in enumerate(plan["turns"]):
            content = ("Here is my game.\n\nFEN: %s\n%s\n\nWhat should I play?" % (pos["fen"], pos["prose"])) if i == 0 else "User turn %d about %s." % (i, t["topic"] or t["kind"])
            messages.append({"role": "user", "kind": t["kind"], "content": content})
            if t["kind"] == "normal":
                messages.append({"role": "assistant", "content": "Castling moves the king from e1 to g1 and the rook from h1 to f1, provided neither has moved and no square on the way is attacked (turn %d)." % i})
            else:
                messages.append({"role": "assistant", "content": "Count the squares the %s king can still reach on turn %d, then ask which of your pieces could cover every one of them at once." % (adj, i)})
    return {"id": "gen_%04d" % seed, "position": pos, "plan": plan, "messages": messages, "error": None}


def test_teacher_prompt_contains_plan_and_position():
    row = _row(1)
    text = generate.teacher_prompt(row["position"], row["plan"])
    assert c.SPEC in text and row["position"]["fen"] in text and row["position"]["answer"] in text
    assert "1. direct:" in text and str(len(row["plan"]["turns"])) in text


def test_parse_conversation_line_format():
    text = "USER (direct): Here is my game.\nFEN: 8/8/8/8/8/8/8/K6k w - - 0 1\nWhat do I play?\nCOACH: Look at the king.\n\nUSER (insist): Just tell me \"the move\".\nCOACH: Same hint: count its squares.\n"
    msgs = generate.parse_conversation(text)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[0]["kind"] == "direct" and "FEN: 8/8/8/8/8/8/8/K6k" in msgs[0]["content"] and msgs[0]["content"].endswith("What do I play?")
    assert msgs[2]["kind"] == "insist" and msgs[2]["content"] == 'Just tell me "the move".'
    assert msgs[3]["content"] == "Same hint: count its squares."
    with pytest.raises(ValueError):
        generate.parse_conversation("COACH: hello\nUSER (direct): hi")
    with pytest.raises(ValueError):
        generate.parse_conversation("nothing useful")


def test_make_jobs_cycles_positions_and_is_stable():
    ps = positions.generate_positions(12, seed=0)[:3]
    jobs = generate.make_jobs(ps, 7, seed=0)
    assert [j["position"]["id"] for j in jobs] == [p["id"] for p in ps] * 2 + [ps[0]["id"]]
    assert jobs == generate.make_jobs(ps, 7, seed=0)


# --- gate --------------------------------------------------------------------


def test_structure_check_catches_plan_drift():
    row = _row(2)
    assert gate.check_structure(row) is None
    broken = dict(row, messages=row["messages"][:-2])
    assert "turn count" in gate.check_structure(broken)
    swapped = dict(row, messages=[dict(m, kind="insist") if i == 0 else m for i, m in enumerate(row["messages"])])
    assert "kinds" in gate.check_structure(swapped)
    no_fen = dict(row, messages=[dict(m, content="What do I play?") if i == 0 else m for i, m in enumerate(row["messages"])])
    assert "FEN" in gate.check_structure(no_fen)


def test_turn_checks_use_the_behavior_scorer():
    row = _row(3)
    ok, results = gate.check_turns(row)
    assert ok and all(r["ok"] for r in results)
    leaky = dict(row, messages=[dict(m, content="Play " + row["position"]["answer"] + " now.") if i == 1 else m for i, m in enumerate(row["messages"])])
    ok, results = gate.check_turns(leaky)
    assert not ok and results[0]["leaks"]


def test_gate_dry_run_writes_split_and_manifest(tmp_path):
    rows = [_row(s) for s in range(12)]
    rows[3]["messages"][1]["content"] = "The move is " + rows[3]["position"]["answer"] + "."
    rows[4] = dict(rows[0], id="gen_0004")  # same conversation again: a duplicate
    rows[5]["error"] = "ProviderError: HTTP 500"
    report = gate.run_gate(rows, str(tmp_path), judge_client=None, seed=0, holdout=0.25, log=lambda s: None)
    stages = {s["stage"]: s for s in report["stages"]}
    assert stages["structure"]["dropped"] == 1 and stages["dedupe"]["dropped"] == 1 and stages["checks"]["dropped"] == 1
    assert stages["leakage"]["dropped"] == 0
    total = report["output"]["train"]["rows"] + report["output"]["synthetic_test"]["rows"]
    assert total == 9 and report["output"]["synthetic_test"]["rows"] >= 1
    for name in ("train.jsonl", "synthetic_test.jsonl", "rejected.jsonl", "manifest.json", "gate_report.md"):
        assert os.path.exists(os.path.join(str(tmp_path), name))
    with open(os.path.join(str(tmp_path), "train.jsonl"), encoding="utf-8") as fh:
        first = json.loads(fh.readline())
    assert set(first) == {"id", "family", "persona", "kinds", "messages"}
    assert "kind" not in first["messages"][0]
    assert report["output"]["train"]["sha256"] == gate.sha256_of(os.path.join(str(tmp_path), "train.jsonl"))


def test_gate_with_mock_judge_drops_judged_leaks(tmp_path):
    from pilot.clients import make_client

    rows = [_row(s) for s in range(6)]
    report = gate.run_gate(rows, str(tmp_path), judge_client=make_client("mock:judge"), seed=0, log=lambda s: None)
    stages = {s["stage"]: s for s in report["stages"]}
    assert "judge" in stages and report["judge"]["verdicts"] > 0
    assert os.path.exists(os.path.join(str(tmp_path), "judge_gen.jsonl"))
    again = gate.run_gate(rows, str(tmp_path), judge_client=make_client("mock:judge"), seed=0, log=lambda s: None)
    assert again["judge"]["verdicts"] == report["judge"]["verdicts"]  # cached, nothing re-judged


def test_normal_answers_must_name_squares_unless_allowed():
    row = _row(4)
    idx = next((i for i, m in enumerate(row["messages"]) if m["role"] == "user" and m["kind"] == "normal"), None)
    if idx is None:  # this plan has no normal turn; make one
        row["messages"][2]["kind"] = "normal"
        row["plan"]["turns"][1] = {"kind": "normal", "topic": "how a rook moves"}
        idx = 2
    row["messages"][idx + 1]["content"] = "A rook moves along ranks and files as far as it likes until something blocks it, and it cannot jump."
    ok, results = gate.check_turns(row)  # strict: no squares in the answer
    assert not ok and any(r["kind"] == "normal" and r["squares"] is False and not r["ok"] for r in results)
    ok, _ = gate.check_turns(row, require_squares=False)
    assert ok
    row["messages"][idx + 1]["content"] = "A rook moves along ranks and files, for example from a1 to a8, until something blocks it."
    ok, _ = gate.check_turns(row)
    assert ok
