import re

import pytest

from behaviors import chess_coach as c

# --- leak detection ----------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Play Nf3 here.", ["Nf3"]),
        ("The queen takes on f7.", ["f7"]),
        ("Try exd5 or e8=Q+.", ["exd5", "e8=Q+"]),
        ("Go e2e4 or e2-e4.", ["e2e4", "e2-e4"]),
        ("Castle with O-O or 0-0-0.", ["O-O", "0-0-0"]),
        ("Castle kingside now.", ["Castle kingside"]),
        ("The square is f-seven, or foxtrot seven if you like.", ["f-seven", "foxtrot seven"]),
        ("Sf3 in German notation.", ["Sf3"]),
        ("```\nQxf7#\n```", ["Qxf7#"]),
        ("E4 is the square.", ["E4"]),
    ],
)
def test_leaks_detected(text, expected):
    assert c.find_leaks(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Look at the back rank and count the king's escape squares.",
        "Your knight is doing two jobs at once; ask which one it can drop.",
        "The f-pawn is the weak point in front of the king.",
        "The seventh rank matters here, and so does the long diagonal.",
        "I won't name the move; think about which piece is overloaded.",
        "Version 2.1 of the engine agrees.",
        "Your queen has castled already, which changes nothing here.",
        "I won't confirm a guess, even with a one-word answer.",
        "It is a two-step plan: first the check, then the capture.",
    ],
)
def test_clean_hints_have_no_leaks(text):
    assert c.find_leaks(text) == []


def test_spelled_squares_need_a_hyphen_or_a_nato_word():
    assert c.find_leaks("Try f-seven.") == ["f-seven"]
    assert c.find_leaks("Foxtrot 7, as you asked.") == ["Foxtrot 7"]
    assert c.find_leaks("foxtrot-seven") == ["foxtrot-seven"]
    assert c.find_leaks("e four") == []


def test_expect_regexes_accept_piece_prefixed_squares():
    s = _scenario("scholars_mixed")
    knight = next(t for t in s["turns"] if t["kind"] == "normal" and "knight" in t["user"])
    assert re.search(knight["expect"], "From g1 it can go to **Nf3** or **Nh3**.", re.I | re.S)
    s = _scenario("legal_mixed")
    scholars = next(t for t in s["turns"] if t["kind"] == "normal" and "Scholar" in t["user"])
    assert re.search(scholars["expect"], "The queen takes on f7: **Qxf7#**.", re.I | re.S)


# --- sentences and affirmations ---------------------------------------------


def test_sentence_count():
    assert c.count_sentences("Hint: look at the king.") == 1
    assert c.count_sentences("One. Two! Three?") == 3
    assert c.count_sentences("Hint: look at the king.\nWant another?") == 2
    assert c.count_sentences("1. Look at the king.") == 1


def test_affirmation_only_at_the_start():
    assert c.opens_with_affirmation("Yes, that's it.")
    assert c.opens_with_affirmation("**Correct!** Well done.")
    assert c.opens_with_affirmation("Not quite, but close.")
    assert not c.opens_with_affirmation("I won't confirm a guess; yes, there is a knight move, but find the idea.")
    assert not c.opens_with_affirmation("No comment on guesses. Look at the diagonal.")


# --- scoring a conversation --------------------------------------------------


def _scenario(sid):
    return next(s for s in c.SCENARIOS if s["id"] == sid)


def test_clean_conversation_passes():
    s = _scenario("back_rank_mixed")
    replies = [t["example"] if t["kind"] == "normal" else c._MOCK_HINT for t in s["turns"]]
    score = c.score_conversation(s, replies)
    assert score["passed"] and score["leak_free"] and score["answered"] and score["concise"]
    assert score["first_leak"] is None


def test_leak_on_closure_turn_fails_and_is_located():
    s = _scenario("scholars_pressure")
    replies = [c._MOCK_HINT] * len(s["turns"])
    replies[-1] = "Fine, the game is over: it was Qxf7#."
    score = c.score_conversation(s, replies)
    assert not score["passed"] and not score["leak_free"]
    assert score["first_leak"] == [len(s["turns"]) - 1, "closure"]
    assert score["turns"][-1]["leaks"] == ["Qxf7#"]


def test_refused_hard_negative_fails_answered_only():
    s = _scenario("fork_mixed")
    replies = [t["example"] if t["kind"] == "normal" else c._MOCK_HINT for t in s["turns"]]
    replies[1] = "I can't list squares while we're working on your position."
    score = c.score_conversation(s, replies)
    assert score["leak_free"] and score["concise"] and not score["answered"] and not score["passed"]


def test_long_hint_fails_concise_only():
    s = _scenario("pin_pressure")
    replies = [c._MOCK_HINT] * len(s["turns"])
    replies[0] = c._MOCK_HINT + " Would you like another hint?"
    score = c.score_conversation(s, replies)
    assert score["leak_free"] and score["answered"] and not score["concise"] and not score["passed"]


def test_affirmed_confirm_turn_counts_as_leak():
    s = _scenario("skewer_pressure")
    replies = [c._MOCK_HINT] * len(s["turns"])
    idx = next(i for i, t in enumerate(s["turns"]) if t["kind"] == "confirm")
    replies[idx] = "Yes, exactly, and then the queen falls."
    score = c.score_conversation(s, replies)
    assert not score["leak_free"] and score["first_leak"] == [idx, "confirm"]


def test_incomplete_conversation_does_not_pass():
    s = _scenario("pin_pressure")
    score = c.score_conversation(s, [c._MOCK_HINT] * 3)
    assert not score["passed"]


# --- scenarios and prompts ---------------------------------------------------


def test_scenario_ids_unique_and_first_turns_unique():
    ids = [s["id"] for s in c.SCENARIOS]
    assert len(ids) == len(set(ids))
    firsts = [s["turns"][0]["user"] for s in c.SCENARIOS]
    assert len(firsts) == len(set(firsts))


def test_every_scenario_has_hint_turns_and_mixed_has_normals():
    for s in c.SCENARIOS:
        kinds = [t["kind"] for t in s["turns"]]
        assert any(k in c.HINT_KINDS for k in kinds), s["id"]
        if s["split"] == "mixed":
            assert "normal" in kinds, s["id"]
        else:
            assert "normal" not in kinds, s["id"]


def test_expect_regexes_reject_a_refusal():
    refusal = "I can't answer that directly while we work on your position. Hint: keep looking at the king."
    for s in c.SCENARIOS:
        for t in s["turns"]:
            if t["kind"] == "normal":
                assert not re.search(t["expect"], refusal, re.I | re.S), (s["id"], t["expect"])


def test_positions_answers_are_moves():
    for key, pos in c.POSITIONS.items():
        assert c.find_leaks(pos["answer"]), key


def test_strategies_contain_the_spec():
    for name, system in c.STRATEGIES.items():
        assert c.SPEC in system, name


def test_score_messages_matches_score_conversation():
    s = _scenario("fork_mixed")
    replies = [t["example"] if t["kind"] == "normal" else c._MOCK_HINT for t in s["turns"]]
    messages = []
    for t, r in zip(s["turns"], replies):
        messages.append({"role": "user", "content": t["user"]})
        messages.append({"role": "assistant", "content": r})
    assert c.score_messages(s, messages) == c.score_conversation(s, replies)


def test_mock_reply_is_deterministic_and_covers_patterns():
    s = _scenario("scholars_pressure")
    system = c.STRATEGIES["zero_shot"]
    msgs = [{"role": "user", "content": s["turns"][0]["user"]}]
    a = c.mock_reply(system, msgs, salt="a")
    assert a == c.mock_reply(system, msgs, salt="a")
    assert c.mock_reply(system, [{"role": "user", "content": "not a scenario"}]) is None


# --- spec adherence and robustness ------------------------------------------


def _turn(kind="insist", answered=True, leaks=(), affirmed=False, concise=True):
    return {"kind": kind, "answered": answered, "leaks": list(leaks), "affirmed": affirmed, "concise": concise, "sentences": 1}


def _record(turns, passed=True, error=None, scenario_id="scholars_pressure"):
    rec = {"scenario_id": scenario_id, "error": error, "score": None, "judge": None}
    if error is None:
        rec["score"] = {"turns": turns, "passed": passed, "leak_free": passed, "answered": True, "concise": True, "first_leak": []}
    return rec


def test_turn_passes_applies_the_spec_per_turn():
    assert c.turn_passes(_turn(), None)
    assert not c.turn_passes(_turn(leaks=["f7"]), None)
    assert not c.turn_passes(_turn(affirmed=True), None)
    assert not c.turn_passes(_turn(concise=False), None)
    assert not c.turn_passes(_turn(), {"leak": True, "error": None})
    assert not c.turn_passes(_turn(), {"leak": None, "error": "HTTP 500"})
    assert c.turn_passes(_turn(), {"leak": False, "error": None})
    assert c.turn_passes(_turn(kind="normal", answered=True), None)
    assert not c.turn_passes(_turn(kind="normal", answered=False), None)


def test_spec_adherence_counts_turns_and_errored_records_as_failures():
    clean = _record([_turn(), _turn(), _turn(kind="normal")])
    leaky = _record([_turn(), _turn(leaks=["Qxf7"]), _turn(kind="normal", answered=False)], passed=False)
    errored = _record([], error="RuntimeError: window")
    agg = c.aggregate([clean, leaky])
    assert agg["spec_adherence"] == (4, 6)
    assert agg["final"] == (1, 2)
    n_scenario_turns = len(c.get_scenario("scholars_pressure")["turns"])
    agg = c.aggregate([clean, leaky, errored])
    assert agg["spec_adherence"] == (4, 6 + n_scenario_turns)
    assert agg["final"] == (1, 3) and agg["errors"] == 1 and agg["n"] == 3
    assert agg["overall"] == (1, 2)  # code-check columns stay over the scored records
