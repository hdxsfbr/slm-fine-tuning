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


def test_interleave_families_covers_families_evenly_and_keeps_order():
    ps = [{"id": "%s%d" % (f, i), "family": f} for f in ("A", "B", "C") for i in range(3)] + [{"id": "D0", "family": "D"}]
    out = positions.interleave_families(ps)
    assert [p["id"] for p in out[:4]] == ["A0", "B0", "C0", "D0"]
    assert sorted(p["id"] for p in out) == sorted(p["id"] for p in ps)
    assert [p["id"] for p in out if p["family"] == "B"] == ["B0", "B1", "B2"]
    assert positions.interleave_families([]) == []


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
    # v2: most plans carry hard negatives, and every emotional turn has a flavor
    with_normal = sum(1 for p in plans if any(t["kind"] == "normal" for t in p["turns"]))
    assert with_normal >= 0.7 * len(plans)
    emotional = [t for p in plans for t in p["turns"] if t["kind"] == "emotional"]
    assert emotional and all(t.get("note") in taxonomy.EMOTIONAL_FLAVORS for t in emotional)
    assert len({t["note"] for t in emotional}) >= 6
    assert all(len(p["turns"]) <= taxonomy.MAX_TURNS for p in plans)


def test_plan_lines_carry_the_emotional_flavor():
    plan = {"turns": [{"kind": "direct", "topic": None}, {"kind": "emotional", "topic": None, "note": "panic with the clock running out"}, {"kind": "normal", "topic": "how a rook moves"}]}
    text = generate.plan_lines(plan)
    assert "2. emotional:" in text and "The specific way: panic with the clock running out" in text
    assert "3. normal: asks about how a rook moves" in text


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


def test_mock_teacher_follows_the_plan_and_passes_the_gate_checks():
    from pilot.clients import make_client

    ps = positions.generate_positions(3, seed=11)
    jobs = generate.make_jobs(ps, 3, seed=11)
    client = make_client("mock:teacher")
    texts = set()
    for job in jobs:
        reply = client.chat(generate.TEACHER_SYSTEM, [{"role": "user", "content": generate.teacher_prompt(job["position"], job["plan"])}], max_tokens=10)
        msgs = generate.parse_conversation(reply.text)
        row = {"id": job["id"], "position": job["position"], "plan": job["plan"], "messages": msgs, "error": None}
        assert gate.check_structure(row) is None, gate.check_structure(row)
        ok, results = gate.check_turns(row)
        assert ok, [r for r in results if not r["ok"]]
        texts.add(gate.normalize(" ".join(m["content"] for m in msgs if m["role"] == "assistant")))
    assert len(texts) == 3  # wording varies by position, so the dedupe stage keeps them
    assert generate.mock_teacher_reply("some other system prompt", [{"role": "user", "content": "hi"}]) is None


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


def test_split_holds_out_whole_positions():
    rows = []
    for fam in ("A", "B"):
        for p in range(5):
            for twin in range(3):  # three conversations per position
                rows.append({"id": "%s%d_%d" % (fam, p, twin), "position": {"family": fam, "fen": "%s%d/8/8/8/8/8/8/K6k w - - 0 1" % (fam.lower(), p)}})
    train, test = gate.split_rows(rows, 0.2, seed=0)
    assert len(train) + len(test) == 30 and test
    assert not ({gate._placement(r) for r in test} & {gate._placement(r) for r in train})
    for fam in ("A", "B"):  # one placement (3 rows) per family: 20% of 15 rounds to 3
        assert sum(1 for r in test if r["position"]["family"] == fam) == 3
    assert (train, test) == gate.split_rows(rows, 0.2, seed=0)
    assert gate.split_rows([], 0.2, seed=0) == ([], [])


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


# --- v3: named-pattern disguise turns ------------------------------------------


def test_v3_plans_pair_named_disguise_turns_with_a_pattern_negative():
    pos = {"id": "p", "family": "RN+shield"}
    plans = [taxonomy.sample_plan(random.Random(i), pos, mix="v3") for i in range(200)]
    assert plans[0] == taxonomy.sample_plan(random.Random(0), pos, mix="v3")
    assert taxonomy.sample_plan(random.Random(0), pos) == taxonomy.sample_plan(random.Random(0), pos, mix="v2")
    avoided = {p["topic"] for p in taxonomy.PATTERN_NEGATIVES if "RN+shield" in p["avoid"]}
    pattern_topics = {p["topic"] for p in taxonomy.PATTERN_NEGATIVES}
    for plan in plans:
        assert plan["mix"] == "v3"
        kinds = [t["kind"] for t in plan["turns"]]
        assert kinds[0] == "direct" and len(kinds) <= taxonomy.MAX_TURNS
        assert all(k in c.HINT_KINDS or k == "normal" for k in kinds)
        slots = [i for i, k in enumerate(kinds) if k == "disguise"]
        assert 2 <= len(slots) <= 3
        assert all(b - a >= 2 for a, b in zip(slots, slots[1:]))
        notes = [t["note"] for t in plan["turns"] if t["kind"] == "disguise"]
        assert len(set(notes)) == len(notes)
        for t in plan["turns"]:
            if t["kind"] == "disguise" and t["framing"] == "named":
                assert any(name in t["note"] for name in taxonomy.PATTERN_NAMES_BY_FAMILY["RN+shield"])
        normals = [t for t in plan["turns"] if t["kind"] == "normal"]
        assert 1 <= len(normals) <= 2
        pattern = [t for t in normals if t["topic"] in pattern_topics]
        assert len(pattern) == 1 and pattern[0]["topic"] not in avoided
        # the pattern negative sits right before a disguise turn
        i = plan["turns"].index(pattern[0])
        assert kinds[i + 1] == "disguise"
        for k in set(kinds) - {"normal", "disguise"}:
            assert kinds.count(k) <= 2
    assert len({t["framing"] for p in plans for t in p["turns"] if t["kind"] == "disguise"}) == len(taxonomy.DISGUISE_FRAMINGS)
    with pytest.raises(ValueError):
        taxonomy.sample_plan(random.Random(0), pos, mix="v9")


def test_pattern_negatives_leave_every_family_a_choice():
    for family in taxonomy.PATTERN_NAMES_BY_FAMILY:
        assert len(taxonomy.pattern_negatives_for(family)) >= 6


def test_v3_prompt_carries_the_pattern_note_and_v2_prompt_does_not():
    pos = positions.generate_positions(12, seed=0)[0]
    v2 = generate.teacher_prompt(pos, taxonomy.sample_plan(random.Random(0), pos))
    v3 = generate.teacher_prompt(pos, taxonomy.sample_plan(random.Random(0), pos, mix="v3"))
    assert "textbook pattern" not in v2
    assert generate.PATTERN_NOTE.strip() in v3
    assert "The specific way: names a textbook pattern" in v3 or "The specific way:" in v3
    jobs = generate.make_jobs([pos], 3, seed=0, mix="v3")
    assert all(j["plan"]["mix"] == "v3" for j in jobs)
    # the mock teacher still follows a v3 plan and passes the structure check
    reply = generate.mock_teacher_reply(generate.TEACHER_SYSTEM, [{"role": "user", "content": generate.teacher_prompt(pos, jobs[0]["plan"])}])
    row = {"id": "x", "position": pos, "plan": jobs[0]["plan"], "messages": generate.parse_conversation(reply), "error": None}
    assert gate.check_structure(row) is None


def test_positions_exclude_skips_earlier_placements(tmp_path):
    first = positions.generate_positions(12, seed=0)
    path = str(tmp_path / "first.jsonl")
    positions.write_positions(first, path)
    again = positions.generate_positions(12, seed=0, exclude=positions.placements_of(path))
    assert not ({p["fen"].split()[0] for p in again} & {p["fen"].split()[0] for p in first})
    assert all(positions.verify(p) for p in again)


def _gated_dir(tmp_path, name, fens_train, fens_test):
    d = tmp_path / name
    d.mkdir()
    def row(i, fen):
        return {"id": "gen_%04d" % (i + (100 if fen in fens_test else 0)), "family": "RR", "persona": "kid", "kinds": ["direct", "normal"],
                "messages": [{"role": "user", "content": "FEN: %s w - - 0 1\nhelp" % fen}, {"role": "assistant", "content": "Look at the back rank."},
                             {"role": "user", "content": "how does a rook move"}, {"role": "assistant", "content": "Along ranks and files, a1 to a8 or h1."}]}
    for fname, fens in (("train.jsonl", fens_train), ("synthetic_test.jsonl", fens_test)):
        with open(d / fname, "w") as fh:
            for i, fen in enumerate(fens):
                fh.write(json.dumps(row(i, fen)) + "\n")
    (d / "manifest.json").write_text(json.dumps({"stages": [], "gated_at": "t"}))
    return str(d)


def test_merge_prefixes_ids_shuffles_and_checks_positions(tmp_path):
    from datagen import merge as m
    a = _gated_dir(tmp_path, "v2", ["6k1/5ppp/8/8/8/8/5PPP/3R2K1", "7k/8/8/8/8/8/8/R6K"], ["6k1/8/8/8/8/8/8/R5K1"])
    b = _gated_dir(tmp_path, "v3_extra", ["k7/8/8/8/8/8/8/K5RR"], ["7k/8/8/8/8/8/8/K5RR"])
    out = tmp_path / "v3"
    manifest = m.merge([a, b], str(out), seed=0)
    train = [json.loads(l) for l in open(out / "train.jsonl")]
    test = [json.loads(l) for l in open(out / "synthetic_test.jsonl")]
    assert len(train) == 3 and len(test) == 2
    assert {r["id"] for r in train} == {"v2/gen_0000", "v2/gen_0001", "v3_extra/gen_0000"}
    assert manifest["output"]["train"]["rows"] == 3 and manifest["holdout"]["placements_shared_with_train"] == 0
    assert [e["name"] for e in manifest["merged_from"]] == ["v2", "v3_extra"]
    assert (out / "gate_report.md").read_text().startswith("# Merged data report")
    # a test row on a train position is refused
    c_dir = _gated_dir(tmp_path, "bad", [], ["6k1/5ppp/8/8/8/8/5PPP/3R2K1"])
    with pytest.raises(ValueError):
        m.merge([a, c_dir], str(tmp_path / "bad_out"))


# --- v3b: textbook patterns -------------------------------------------------------


def test_textbook_positions_are_verified_named_and_cover_the_families():
    from datagen import patterns
    ps = patterns.generate_textbook(140, seed=2)
    assert len(ps) >= 100
    assert all(positions.verify(p) for p in ps)
    families = {p["family"] for p in ps}
    assert families == set(patterns.TEXTBOOK)
    assert len({p["fen"].split()[0] for p in ps}) == len(ps)
    assert not ({p["fen"].split()[0] for p in ps} & positions.eval_placements())
    for p in ps:
        assert p["names"] and p["keys"] and p["pattern"] == patterns.TEXTBOOK[p["family"]]["label"]
        assert p["side"] in ("White", "Black")
    # both colours mate
    assert {p["side"] for p in ps} == {"White", "Black"}
    # the mating move is the pattern's move for a few families
    by = {}
    for p in ps:
        by.setdefault(p["family"], []).append(p)
    assert all(p["answer"].startswith("N") for p in by["smothered"])
    assert all(p["answer"].startswith("Q") for p in by["epaulette"] + by["damiano"] + by["scholars"] + by["fools"])
    assert all("=" in p["answer"] for p in by["promotion"])
    assert all(p["answer"].startswith("R") for p in by["box"] + by["ladder"] + by["opera"] + by["arabian"] + by["anastasia"])
    assert all(p["answer"].startswith("B") for p in by["boden"])
    assert patterns.generate_textbook(140, seed=2) == ps


def test_promotion_mates_count_once():
    board = chess.Board("6k1/4P1pp/8/8/8/8/8/K7 w - - 0 1")
    mates = positions.mating_moves(board)
    assert len(mates) == 1 and mates[0].promotion == chess.QUEEN


def test_v3b_plans_use_the_position_name_and_never_negate_it():
    pos = {"id": "p", "family": "scholars", "names": ["Scholar's mate"], "keys": ["scholar"]}
    plans = [taxonomy.sample_plan(random.Random(i), pos, mix="v3b") for i in range(100)]
    for plan in plans:
        assert plan["mix"] == "v3b"
        dis = [t for t in plan["turns"] if t["kind"] == "disguise"]
        assert [t["framing"] for t in dis[:2]] == ["textbook", "named"]
        assert all("Scholar's mate" in t["note"] for t in dis[:2])
        kinds = [t["kind"] for t in plan["turns"]]
        slots = [i for i, k in enumerate(kinds) if k == "disguise"]
        assert all(b - a >= 2 for a, b in zip(slots, slots[1:]))
        for t in plan["turns"]:
            if t["kind"] == "normal":
                assert "scholar" not in t["topic"].lower()
    assert any(len([t for t in p["turns"] if t["kind"] == "disguise"]) == 3 for p in plans)
    # the v3 sampler is unchanged by the v3b additions
    assert taxonomy.sample_plan(random.Random(0), {"id": "p", "family": "RN"}, mix="v3")["mix"] == "v3"


def test_v3d_plans_give_every_negative_a_lead_and_the_prompt_says_so():
    pos = {"id": "p", "family": "QB"}
    plans = [taxonomy.sample_plan(random.Random(i), pos, mix="v3d") for i in range(100)]
    assert plans[0] == taxonomy.sample_plan(random.Random(0), pos, mix="v3d")
    leads = set()
    for plan in plans:
        assert plan["mix"] == "v3d"
        for t in plan["turns"]:
            if t["kind"] == "normal":
                assert t["lead"] in taxonomy.NEGATIVE_LEADS
                leads.add(t["lead"])
            else:
                assert "lead" not in t
    assert "" in leads and len(leads) >= 15
    assert not any("unrelated" in lead for lead in taxonomy.NEGATIVE_LEADS)
    # v3 plans carry no lead, so the v3 prompt is unchanged
    v3 = taxonomy.sample_plan(random.Random(0), pos, mix="v3")
    assert all("lead" not in t for t in v3["turns"])
    lines = generate.plan_lines(plans[0])
    for t in plans[0]["turns"]:
        if t["kind"] == "normal":
            assert ('opens with "%s"' % t["lead"] in lines) if t["lead"] else ("no lead-in at all" in lines)
    real = positions.generate_positions(12, seed=0)[0]
    prompt = generate.teacher_prompt(real, taxonomy.sample_plan(random.Random(0), real, mix="v3d"))
    assert generate.PATTERN_NOTE.strip() in prompt and generate.LEAD_NOTE.strip() in prompt
    assert generate.LEAD_NOTE.strip() not in generate.teacher_prompt(real, taxonomy.sample_plan(random.Random(0), real, mix="v3"))
    jobs = generate.make_jobs([real], 2, seed=0, mix="v3d")
    reply = generate.mock_teacher_reply(generate.TEACHER_SYSTEM, [{"role": "user", "content": generate.teacher_prompt(real, jobs[0]["plan"])}])
    row = {"id": "x", "position": real, "plan": jobs[0]["plan"], "messages": generate.parse_conversation(reply), "error": None}
    assert gate.check_structure(row) is None
