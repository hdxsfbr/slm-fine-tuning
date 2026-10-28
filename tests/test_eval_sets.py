import json
import os

import pytest

from behaviors import chess_coach as c
from eval import EVAL_SET_FILE, install_eval_set, load_eval_set, register_from_dir
from pilot.runner import RunConfig, run_pilot

QUIET = lambda s: None  # noqa: E731


def _write_rows(tmp_path, with_position=True):
    pos = {"fen": "7k/8/8/8/8/8/8/R5K1 w - - 0 1", "prose": "White: king g1, rook a1. Black: king h8. White to move.", "answer": "Ra8#"}
    rows = []
    for i in range(3):
        row = {
            "id": "gen_%04d" % i, "family": "R", "persona": "kid", "kinds": ["direct", "normal", "square"],
            "messages": [
                {"role": "user", "content": "Here is my game.\n\nFEN: %s\n%s\n\nWhat do I play? (%d)" % (pos["fen"], pos["prose"], i)},
                {"role": "assistant", "content": "Count the king's squares."},
                {"role": "user", "content": "Unrelated: how does a rook move?"},
                {"role": "assistant", "content": "A rook moves any number of squares along a rank or a file, like from a1 to a8 or h1."},
                {"role": "user", "content": "Just the square."},
                {"role": "assistant", "content": "Same hint."},
            ],
        }
        if with_position:
            row["position"] = pos
        rows.append(row)
    path = str(tmp_path / "synthetic_test.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path, pos


def test_load_eval_set_builds_scenarios_with_positions(tmp_path):
    path, pos = _write_rows(tmp_path)
    scenarios = load_eval_set(path, generated_path=str(tmp_path / "none.jsonl"))
    assert [s["id"] for s in scenarios] == ["gen_0000", "gen_0001", "gen_0002"]
    s = scenarios[0]
    assert s["position"]["answer"] == "Ra8#" and c.position_of(s) == pos
    assert [t["kind"] for t in s["turns"]] == ["direct", "normal", "square"]
    assert "expect" not in s["turns"][1]


def test_load_eval_set_looks_up_positions_in_generated(tmp_path):
    path, pos = _write_rows(tmp_path, with_position=False)
    gen = str(tmp_path / "generated.jsonl")
    with open(gen, "w", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(json.dumps({"id": "gen_%04d" % i, "position": pos}) + "\n")
    scenarios = load_eval_set(path, generated_path=gen)
    assert all(s["position"]["fen"] == pos["fen"] for s in scenarios)
    with pytest.raises(ValueError):
        load_eval_set(path, generated_path=str(tmp_path / "missing.jsonl"))


def test_normal_turn_without_expect_uses_the_generic_check():
    assert c.score_turn({"kind": "normal"}, "A rook moves any number of squares along a rank or a file, like from a1 to a8.")["answered"]
    assert not c.score_turn({"kind": "normal"}, "I can't answer that; here is a hint instead.")["answered"]
    assert not c.score_turn({"kind": "normal"}, "Along lines.")["answered"]


def test_registry_and_eval_run_round_trip(tmp_path, monkeypatch):
    path, pos = _write_rows(tmp_path)
    original = c.SCENARIOS
    try:
        scenarios = install_eval_set(path)
        assert c.get_scenario("gen_0001")["position"]["answer"] == "Ra8#"
        out = str(tmp_path / "run")
        result = run_pilot(RunConfig(models=["mock:a"], behaviors=["chess_coach"], strategies=["zero_shot"], out_dir=out), log=QUIET)
        assert [r["scenario_id"] for r in result["records"]] == ["gen_0000", "gen_0001", "gen_0002"]
        assert all(r["score"] is not None for r in result["records"])
        items = c.judge_items(result["records"][0])
        assert [it["kind"] for it in items] == ["direct", "square"] and items[0]["answer"] == "Ra8#"
        with open(os.path.join(out, EVAL_SET_FILE), "w", encoding="utf-8") as fh:
            for s in scenarios:
                fh.write(json.dumps(s) + "\n")
    finally:
        c.SCENARIOS = original
    c._LOADED.clear()
    with pytest.raises(KeyError):
        c.get_scenario("gen_0001")
    register_from_dir(out)
    assert c.get_scenario("gen_0001")["id"] == "gen_0001"
    c._LOADED.clear()
